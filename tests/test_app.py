import json
import io
import sys
import types
import zipfile
import pytest
from compuse.app.workflow import authorize, build_action, perform, run_demo
from compuse.app.cli import main
from compuse.app.executor import execute, ExecutorError
from compuse.app.sequence import load_steps, run_steps


def test_tasker_prompt_session_uses_prompt_toolkit_meta_dict(monkeypatch):
    from compuse.app.tasker_cli import TaskerShell

    captured = {}

    class FakeWordCompleter:
        def __init__(self, words, **kwargs):
            captured["words"] = words
            captured.update(kwargs)

    class FakePromptSession:
        def __init__(self, *, completer):
            self.completer = completer

    fake_prompt_toolkit = types.ModuleType("prompt_toolkit")
    fake_prompt_toolkit.PromptSession = FakePromptSession
    fake_completion = types.ModuleType("prompt_toolkit.completion")
    fake_completion.WordCompleter = FakeWordCompleter
    monkeypatch.setitem(sys.modules, "prompt_toolkit", fake_prompt_toolkit)
    monkeypatch.setitem(sys.modules, "prompt_toolkit.completion", fake_completion)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)

    shell = TaskerShell.__new__(TaskerShell)
    shell.input_fn = input
    session = shell._prompt_session()

    assert isinstance(session, FakePromptSession)
    assert "/help" in captured["words"]
    assert captured["meta_dict"]["/help"] == "show commands"
    assert "meta" not in captured


def test_tasker_archive_update_overlays_source_and_keeps_runtime_files(tmp_path):
    from compuse.app import updater

    archive_bytes = io.BytesIO()
    with zipfile.ZipFile(archive_bytes, "w") as archive:
        archive.writestr("compuse-main/compuse/app/tasker_cli.py", "new code")
        archive.writestr("compuse-main/pyproject.toml", "new metadata")

    runtime_db = tmp_path / "desktop-web.db"
    runtime_db.write_text("keep this", encoding="utf-8")
    staging = tmp_path / "staging"
    staging.mkdir()
    files = updater._stage_archive(archive_bytes.getvalue(), staging)
    updater._install_staged(tmp_path, files, "a" * 40, staging)

    assert (tmp_path / "compuse/app/tasker_cli.py").read_text(encoding="utf-8") == "new code"
    assert (tmp_path / "pyproject.toml").read_text(encoding="utf-8") == "new metadata"
    assert runtime_db.read_text(encoding="utf-8") == "keep this"
    assert (tmp_path / updater.REVISION_MARKER).read_text(encoding="ascii").strip() == "a" * 40


def test_tasker_update_check_skips_when_revision_marker_is_current(monkeypatch, tmp_path):
    from compuse.app import updater

    revision = "b" * 40
    (tmp_path / updater.REVISION_MARKER).write_text(revision, encoding="ascii")
    monkeypatch.setattr(updater, "remote_revision", lambda **_: revision)

    result = updater.maybe_auto_update(root=tmp_path, restart=False)

    assert result.state == "current"
    assert result.revision == revision


def test_tasker_main_returns_after_successful_auto_restart(monkeypatch):
    from compuse.app import tasker_cli, updater

    monkeypatch.setattr(
        tasker_cli,
        "maybe_auto_update",
        lambda **_: updater.UpdateResult("restarted", exit_code=0),
    )

    assert tasker_cli.main(["--no-banner"]) == 0


def test_demo_covers_full_lifecycle():
    lines = run_demo()
    joined = "\n".join(lines)
    assert "permit        issued" in joined
    assert "approved" in joined
    assert "chain verifies=True" in joined
    assert "mutation boundary released" in joined


def test_build_action_rejects_unknown_kind():
    with pytest.raises(Exception):
        build_action({"kind": "teleport", "x": 1})


def test_authorize_end_to_end():
    result = authorize({"kind": "click", "x": 10, "y": 20})
    assert result["approved"]["kind"] == "click"
    assert result["approved"]["x"] == 10
    assert result["journal_events"] >= 2
    assert result["journal_verifies"] is True


def test_cli_version_and_authorize(capsys):
    assert main(["version"]) == 0
    captured = capsys.readouterr()
    assert "compuse" in captured.out
    assert main(["authorize", json.dumps({"kind": "type", "text": "hi"})]) == 0
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert parsed["approved"]["text"] == "hi"


def test_cli_authorize_bad_json(capsys):
    assert main(["authorize", "{nope"]) != 0


def test_cli_authorize_from_file(tmp_path, capsys):
    payload = tmp_path / "action.json"
    payload.write_text(json.dumps({"kind": "type", "text": "from file"}), encoding="utf-8")
    assert main(["authorize", f"@{payload}"]) == 0
    captured = capsys.readouterr()
    assert json.loads(captured.out)["approved"]["text"] == "from file"


def test_cli_authorize_from_missing_file(capsys):
    assert main(["authorize", "@/nonexistent/action.json"]) != 0


def test_cli_authorize_persists_journal(tmp_path, capsys):
    db_path = str(tmp_path / "j.db")
    journal = tmp_path / "j.db"
    assert main(["authorize", json.dumps({"kind": "type", "text": "hi"}),
                 "--journal", db_path]) == 0
    assert main(["journal", db_path, "--verify", "--run-id", "cli-run"]) == 0
    out = capsys.readouterr().out
    assert "verifies=True" in out
    assert main(["journal", db_path, "--run-id", "cli-run"]) == 0


def _fake_run_popen_factory(popen_calls):
    def fake_popen(*args, **kwargs):
        popen_calls["args"] = args[0]
        return None
    return fake_popen


def test_execute_open_file_performs(monkeypatch, tmp_path):
    from compuse.app import executor
    target = tmp_path / "hi.txt"
    target.write_text("hello", encoding="utf-8")
    calls: dict = {}
    if sys.platform == "win32":
        monkeypatch.setattr(executor.os, "startfile", lambda p, *a, **k: calls.setdefault("called", p))
    else:
        monkeypatch.setattr(executor.subprocess, "Popen", _fake_run_popen_factory(calls))
    action = build_action({"kind": "file.open", "path": str(target)})
    result = execute(action)
    assert result["performed"] is True
    assert "opened" in result["detail"]


def test_execute_open_missing_file_rejected(tmp_path):
    action = build_action({"kind": "file.open", "path": str(tmp_path / "nope.txt")})
    with pytest.raises(ExecutorError):
        execute(action)


def test_execute_browse_performs(monkeypatch):
    from compuse.app import executor
    calls: dict = {}
    monkeypatch.setattr(executor.webbrowser, "open", lambda url, new=0: calls.setdefault("url", url))
    action = build_action({"kind": "browse", "url": "https://example.com/"})
    result = execute(action)
    assert result["performed"] is True
    assert calls["url"] == "https://example.com/"


def test_execute_unsupported_kind_is_supervised(monkeypatch):
    action = build_action({"kind": "type", "text": "hello"})
    result = execute(action)
    assert result["performed"] is False


def test_perform_executes_and_journals(monkeypatch, tmp_path):
    from compuse.app import executor
    db = str(tmp_path / "perf.db")
    calls: dict = {}
    monkeypatch.setattr(executor.webbrowser, "open", lambda url, new=0: calls.setdefault("url", url))
    result = perform({"kind": "browse", "url": "https://example.com/"}, run_id="perf-run",
                     journal_path=db)
    assert result["execution"]["performed"] is True
    assert result["journal_events"] >= 2
    assert result["journal_verifies"] is True
    assert calls["url"] == "https://example.com/"


def test_cli_open_and_browse(monkeypatch, tmp_path, capsys):
    from compuse.app import executor
    calls: dict = {}
    monkeypatch.setattr(executor.webbrowser, "open", lambda url, new=0: calls.setdefault("url", url))
    assert main(["browse", "https://example.com/"]) == 0
    captured = capsys.readouterr()
    assert json.loads(captured.out)["execution"]["performed"] is True


class _FakeEngine:
    def __init__(self, trace: list[str]) -> None:
        self.trace = trace
        self.started = False

    def start(self) -> None:
        self.started = True

    def run_webop(self, action) -> dict:
        kind = action.op
        self.trace.append(kind)
        if kind == "goto":
            return {"performed": True, "detail": f"navigated to {action.url}"}
        if kind == "click":
            return {"performed": True, "detail": f"clicked {action.selector}"}
        if kind == "wait":
            return {"performed": True, "detail": "waited"}
        if kind == "type":
            return {"performed": True, "detail": "typed"}
        return {"performed": False, "detail": "unknown"}

    def close(self) -> None:
        self.started = False


def test_run_steps_each_step_is_permitted_and_journaled(tmp_path):
    from compuse.protocol import WebOp
    steps = [
        WebOp(op="goto", url="https://books.toscrape.com/"),
        WebOp(op="click", selector="article.product_pod h3 a"),
        WebOp(op="wait", seconds=0.25),
    ]
    trace: list[str] = []
    result = run_steps(steps, run_id="seq-run", journal_path=str(tmp_path / "seq.db"),
                       browser=_FakeEngine(trace))
    assert result["failures"] == 0
    assert result["steps"] == 3
    assert trace == ["goto", "click", "wait"]
    assert result["journal_events"] == 6
    assert result["journal_verifies"] is True
    for i, line in enumerate(result["transcript"]):
        assert str(i + 1) in line


def test_run_steps_continues_on_step_failure(tmp_path):
    from compuse.protocol import WebOp

    class Boom(_FakeEngine):
        def run_webop(self, action):
            self.trace.append(action.op)
            if action.op == "click":
                raise RuntimeError("selector not found")
            return {"performed": True, "detail": "ok"}

    steps = [WebOp(op="goto", url="https://x/"), WebOp(op="click", selector="#nope"), WebOp(op="wait", seconds=0.1)]
    result = run_steps(steps, run_id="seq-boom", browser=Boom([]))
    assert result["failures"] == 1
    assert "ERROR" in result["transcript"][1]
    assert result["journal_verifies"] is True


def test_load_steps_validates(tmp_path):
    path = tmp_path / "steps.json"
    path.write_text(json.dumps([{"op": "goto", "url": "https://example.com/"}, {"op": "bad"}]), encoding="utf-8")
    with pytest.raises(Exception):
        load_steps(str(path))


def test_load_steps_tolerates_utf8_bom(tmp_path):
    raw = json.dumps([{"op": "goto", "url": "https://example.com/"}]).encode("utf-8")
    path = tmp_path / "steps.json"
    path.write_bytes(b"\xef\xbb\xbf" + raw)
    steps = load_steps(str(path))
    assert len(steps) == 1 and steps[0].op == "goto"


def test_cli_run_with_steps_file(monkeypatch, tmp_path, capsys):
    from compuse.app import cli
    path = tmp_path / "steps.json"
    path.write_text(json.dumps([{"op": "goto", "url": "https://books.toscrape.com/"},
                                {"op": "click", "selector": "a"}, {"op": "wait", "seconds": 0.1}]),
                    encoding="utf-8")
    trace: list[str] = []
    monkeypatch.setattr(cli, "run_steps", lambda steps, **k: run_steps(
        steps, run_id="cli-run", browser=_FakeEngine(trace)))
    assert main(["run", str(path)]) == 0
    captured = capsys.readouterr()
    assert "3 step(s)" in captured.out
    assert "journal verifies=True" in captured.out


def test_cli_journal_roundtrip(tmp_path):
    path = str(tmp_path / "journal.db")
    assert main(["journal", path, "--verify", "--run-id", "r"]) == 0
    assert main(["journal", path, "--run-id", "r"]) == 0


def test_gui_controller_transcript():
    from compuse.app.gui import AppController

    ctrl = AppController()
    ctrl.run_demo()
    assert any("permit" in line for line in ctrl.transcript)
    result = ctrl.authorize({"kind": "type", "text": "gui"})
    assert result["approved"]["text"] == "gui"
    assert any("authorized" in line for line in ctrl.transcript)
