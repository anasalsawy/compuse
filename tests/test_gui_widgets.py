# SYNC-V2-MARKER
"""Q&A-less widget smoke tests for the GUI (needs a display; shared Tk root).

On Windows, creating multiple ``Tk()`` interpreters inside one process is
flaky (tcl/ttk re-initialization), so the widget subtree is built once on a
module-level root and reused.
"""
import pytest

tkinter = pytest.importorskip("tkinter")


@pytest.fixture(scope="module")
def root():
    r = tkinter.Tk()
    r.withdraw()
    yield r
    try:
        r.destroy()
    except tkinter.TclError:
        pass


def _build(root, controller=None):
    from compuse.app.gui import AppController, CompuseApp

    if controller is None:
        controller = AppController()
    widget = CompuseApp(root, controller)
    root.update_idletasks()
    return widget


def test_widgets_render_and_demo_runs(root):
    widget = _build(root)
    widget._on_demo()
    text = widget._log.get("1.0", "end")
    assert "permit" in text and "chain verifies=True" in text


def test_widget_authorize_buttons(root):
    widget = _build(root)
    widget._on_authorize()
    assert "approved" in widget._log.get("1.0", "end")
    widget._on_clear()
    assert widget._log.get("1.0", "end").strip() == ""


def test_widget_authorize_failure_is_caught(root):
    widget = _build(root)

    class Broken:
        def authorize(self, payload):
            raise RuntimeError("boom")

    widget.controller = Broken()
    widget._on_authorize()
    assert "error: boom" in widget._log.get("1.0", "end")