"""Desktop GUI application wrapping the coordination core.

Built on tkinter (stdlib) so it packages cleanly into a standalone .exe.
The controller logic is kept separate from widgets so it stays testable.
"""
from __future__ import annotations

from tkinter import BOTH, END, LEFT, X, ttk

from compuse.app.workflow import authorize, demo


class AppController:
    """Model behind the GUI: runs workflows and records a transcript."""

    def __init__(self) -> None:
        self.transcript: list[str] = []

    def log(self, line: str) -> None:
        self.transcript.append(line)

    def run_demo(self) -> None:
        demo(self.transcript)

    def authorize(self, payload: dict) -> dict:
        result = authorize(payload)
        self.log(f"authorized {result['approved']['kind']!r} permit {result['permit_id'][:8]}")
        return result


class CompuseApp(ttk.Frame):
    def __init__(self, master: object = None, controller: AppController | None = None) -> None:
        super().__init__(master)
        self.controller = controller or AppController()
        self.pack(fill=BOTH, expand=True)
        self._build_gui()

    def _build_gui(self) -> None:
        self._log = self._make_log()
        self._make_controls()

    def _make_log(self) -> None:
        from tkinter import scrolledtext

        frame = ttk.Frame(self)
        frame.pack(fill=BOTH, expand=True, padx=8, pady=(8, 4))
        box = scrolledtext.ScrolledText(frame, height=18, state="disabled", wrap="word")
        box.pack(fill=BOTH, expand=True)
        return box

    def _make_controls(self) -> None:
        bar = ttk.Frame(self)
        bar.pack(fill=X, padx=8, pady=4)
        ttk.Button(bar, text="Run Demo", command=self._on_demo).pack(side=LEFT, padx=2)
        ttk.Button(bar, text="Authorize: Type 'hello'", command=self._on_authorize).pack(side=LEFT, padx=2)
        ttk.Button(bar, text="Authorize: Click", command=self._on_click).pack(side=LEFT, padx=2)
        ttk.Button(bar, text="Clear", command=self._on_clear).pack(side=LEFT, padx=2)

    def _append(self, line: str) -> None:
        self._log.configure(state="normal")
        self._log.insert(END, line + "\n")
        self._log.configure(state="disabled")
        self._log.see(END)

    def _flush(self) -> None:
        for line in self.controller.transcript:
            self._append(line)

    def _on_demo(self) -> None:
        self.controller.run_demo()
        self._flush()

    def _on_authorize(self) -> None:
        self._run_authorize({"kind": "type", "text": "hello from compuse GUI"})

    def _on_click(self) -> None:
        self._run_authorize({"kind": "click", "x": 100, "y": 200})

    def _run_authorize(self, payload: dict) -> None:
        try:
            result = self.controller.authorize(payload)
            self._append(f"-> approved {result['approved']}")
        except Exception as exc:
            self._append(f"-> error: {exc}")

    def _on_clear(self) -> None:
        self._log.configure(state="normal")
        self._log.delete("1.0", END)
        self._log.configure(state="disabled")


def main() -> int:
    from tkinter import Tk

    root = Tk()
    root.title("Compuse Console")
    root.geometry("760x560")
    CompuseApp(root, AppController())
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())