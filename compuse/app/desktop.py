"""Optional live desktop adapter for the Compuse agent runtime.

This is deliberately separate from the portable coordination core.  Installing
the package does not grant it mouse/keyboard control; callers must explicitly
construct the adapter with ``live=True``.
"""
from __future__ import annotations

import base64
import ctypes
import hashlib
import io
import os
import subprocess
import time
import webbrowser
from datetime import datetime, timezone
from typing import Any, Iterable

from compuse.protocol import (
    Action,
    ApplicationLaunch,
    Browse,
    Click,
    DoubleClick,
    Drag,
    FocusWindow,
    KeyCombo,
    Keypress,
    MouseMove,
    OpenFile,
    Screenshot,
    Scroll,
    TypeText,
    Wait,
)

from compuse.agent.contracts import RuntimeObservation


class DesktopSafetyError(RuntimeError):
    """Raised when live input was not explicitly enabled."""


class DesktopAdapter:
    """Capture the active Windows desktop and execute typed input actions."""

    def __init__(
        self,
        *,
        live: bool = False,
        launch_allowlist: Iterable[str] = (),
        screenshot_format: str = "PNG",
    ) -> None:
        self.live = live
        self.launch_allowlist = frozenset(os.path.abspath(str(p)) for p in launch_allowlist)
        self.screenshot_format = screenshot_format
        self._revision = 0
        self._pyautogui = None

    def _gui(self):
        if self._pyautogui is None:
            try:
                import pyautogui
            except ImportError as exc:  # pragma: no cover - optional Windows dependency
                raise DesktopSafetyError(
                    "pyautogui is not installed; install compuse[desktop]"
                ) from exc
            pyautogui.PAUSE = 0.02
            self._pyautogui = pyautogui
        return self._pyautogui

    @staticmethod
    def _windows_identity() -> tuple[str | None, str | None, int | None, int | None, str | None]:
        if os.name != "nt":
            return None, None, None, None, None
        try:
            user32 = ctypes.WinDLL("user32", use_last_error=True)
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            hwnd = user32.GetForegroundWindow()
            if not hwnd:
                return None, None, None, None, None
            title_buffer = ctypes.create_unicode_buffer(512)
            user32.GetWindowTextW(hwnd, title_buffer, len(title_buffer))
            pid = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            session_id = ctypes.c_ulong()
            if not kernel32.ProcessIdToSessionId(pid.value, ctypes.byref(session_id)):
                session_id_value = None
            else:
                session_id_value = int(session_id.value)
            return str(hwnd), title_buffer.value or None, int(pid.value), session_id_value, "WinSta0\\Default"
        except (AttributeError, OSError):  # pragma: no cover - Windows API dependent
            return None, None, None, None, None

    def observe(self) -> RuntimeObservation:
        gui = self._gui()
        image = gui.screenshot()
        buffer = io.BytesIO()
        image.save(buffer, format=self.screenshot_format)
        raw = buffer.getvalue()
        encoded = base64.b64encode(raw).decode("ascii")
        width, height = image.size
        window_id, foreground, process_id, session_id, input_desktop = self._windows_identity()
        markers = self._ui_markers(window_id)
        if foreground and foreground not in markers:
            markers = (foreground, *markers)
        self._revision += 1
        return RuntimeObservation(
            run_id="desktop",
            revision=self._revision,
            captured_at=datetime.now(timezone.utc),
            coordinate_space_id=f"screen:{width}x{height}",
            foreground_window=foreground,
            visible_markers=markers,
            screen_sha256=hashlib.sha256(raw).hexdigest(),
            window_id=window_id,
            process_id=process_id,
            session_id=session_id,
            input_desktop=input_desktop,
            screenshot_data_url=f"data:image/{self.screenshot_format.lower()};base64,{encoded}",
        )

    @staticmethod
    def _ui_markers(window_id: str | None) -> tuple[str, ...]:
        """Read short visible UIA labels when pywinauto is available.

        UIA is an observation source only.  It does not authorize or dispatch
        an action, and failure to read it simply leaves the marker set empty.
        """
        if os.name != "nt" or not window_id:
            return ()
        try:
            from pywinauto import Desktop

            window = Desktop(backend="uia").window(handle=int(window_id))
            values: list[str] = []
            for control in window.descendants():
                try:
                    text = control.window_text().strip()
                except Exception:  # noqa: BLE001 - individual controls may disappear
                    continue
                if text and len(text) <= 256 and text not in values:
                    values.append(text)
                if len(values) >= 63:
                    break
            return tuple(values)
        except (ImportError, OSError, ValueError):  # pragma: no cover - optional Windows dependency
            return ()

    def _require_live(self, action: Action) -> None:
        if not self.live and not isinstance(action, (Screenshot, Wait)):
            raise DesktopSafetyError(
                "live desktop input is disabled; pass --live after reviewing the task"
            )

    def execute_action(self, action: Action) -> dict[str, Any]:
        self._require_live(action)
        gui = self._gui()
        started = time.perf_counter()
        if isinstance(action, Wait):
            time.sleep(action.seconds)
            detail = f"waited {action.seconds}s"
        elif isinstance(action, Screenshot):
            self.observe()
            detail = "captured screenshot"
        elif isinstance(action, MouseMove):
            gui.moveTo(action.x, action.y)
            detail = f"moved pointer to ({action.x}, {action.y})"
        elif isinstance(action, TypeText):
            try:
                import pyperclip

                pyperclip.copy(action.text)
                gui.hotkey("ctrl", "v")
            except Exception:  # noqa: BLE001 - ASCII fallback when clipboard integration is unavailable
                gui.write(action.text, interval=0)
            detail = f"typed {len(action.text)} character(s)"
        elif isinstance(action, Click):
            gui.click(action.x, action.y)
            detail = f"clicked ({action.x}, {action.y})"
        elif isinstance(action, DoubleClick):
            gui.doubleClick(action.x, action.y)
            detail = f"double-clicked ({action.x}, {action.y})"
        elif isinstance(action, Drag):
            gui.moveTo(action.start_x, action.start_y)
            gui.dragTo(action.end_x, action.end_y, duration=0.15, button="left")
            detail = f"dragged ({action.start_x}, {action.start_y}) to ({action.end_x}, {action.end_y})"
        elif isinstance(action, Scroll):
            gui.scroll(action.delta)
            detail = f"scrolled {action.delta}"
        elif isinstance(action, Keypress):
            gui.press(action.key)
            detail = f"pressed {action.key}"
        elif isinstance(action, KeyCombo):
            gui.hotkey(*action.keys)
            detail = f"pressed {'+'.join(action.keys)}"
        elif isinstance(action, FocusWindow):
            self._focus_window(action.window_id)
            detail = f"focused window {action.window_id}"
        elif isinstance(action, ApplicationLaunch):
            target = os.path.abspath(action.target_id)
            if target not in self.launch_allowlist:
                raise DesktopSafetyError(f"launch target is not allowlisted: {action.target_id}")
            subprocess.Popen([target], shell=False)
            detail = f"launched {target}"
        elif isinstance(action, OpenFile):
            target = os.path.abspath(os.path.expanduser(action.path))
            if not os.path.isfile(target):
                raise DesktopSafetyError(f"file does not exist: {target}")
            if os.name == "nt":
                os.startfile(target)
            else:  # pragma: no cover - live adapter is intended for Windows
                subprocess.Popen(["xdg-open", target], shell=False)
            detail = f"opened {target}"
        elif isinstance(action, Browse):
            if not webbrowser.open(action.url, new=2):
                raise DesktopSafetyError(f"could not open browser for {action.url}")
            detail = f"opened {action.url}"
        else:  # pragma: no cover - the protocol union is exhaustive
            raise DesktopSafetyError(f"unsupported desktop action: {action.kind}")
        return {
            "performed": True,
            "uncertain": False,
            "detail": detail,
            "elapsed_ms": (time.perf_counter() - started) * 1000.0,
        }

    @staticmethod
    def _focus_window(window_id: str) -> None:
        if os.name != "nt":
            raise DesktopSafetyError("window focusing is only implemented on Windows")
        try:
            user32 = ctypes.WinDLL("user32", use_last_error=True)
            hwnd = int(window_id)
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            if not user32.SetForegroundWindow(hwnd):
                raise DesktopSafetyError(f"Windows refused to focus window {window_id}")
        except ValueError as exc:
            raise DesktopSafetyError(f"invalid window id: {window_id}") from exc


__all__ = ["DesktopAdapter", "DesktopSafetyError"]
