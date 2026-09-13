import json
import sys
import pytest
from compuse.app.workflow import authorize, build_action, perform, run_demo
from compuse.app.cli import main
from compuse.app.executor import execute, ExecutorError


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