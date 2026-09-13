import json
import pytest
from compuse.app.workflow import authorize, build_action, run_demo
from compuse.app.cli import main


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