"""Permitted-action executor: performs a consumed action on the local host.

Only side-effect-free-with-user-invocation primitives are performed for real
(open a file with the OS default app, open a URL in the default browser).
No shell interception and no synthetic input injection: other action kinds
are acknowledged but deliberately left unperformed.
"""
from __future__ import annotations

import os
import platform
import subprocess
import webbrowser
from pathlib import Path
from typing import Any

from compuse.protocol import Action, Browse, OpenFile


class ExecutorError(RuntimeError):
    pass


def execute(action: Action) -> dict[str, Any]:
    """Perform ``action`` and return an execution record.

    Raises ExecutorError if the action cannot be carried out.
    """
    if isinstance(action, OpenFile):
        path = Path(action.path).expanduser()
        if not path.is_absolute():
            path = Path.cwd() / path
        if not path.exists() or not path.is_file():
            raise ExecutorError(f"file does not exist: {path}")
        _open_path(path)
        return {"performed": True, "detail": f"opened {path} with the default app", "target": str(path)}
    if isinstance(action, Browse):
        url = action.url
        if not webbrowser.open(url, new=2):
            raise ExecutorError(f"could not open browser for {url}")
        return {"performed": True, "detail": f"browsing {url} in the default browser", "target": url}
    return {"performed": False, "detail": "supervised demo: no host side effect for this action kind", "target": None}


def _open_path(path: Path) -> None:
    system = platform.system()
    if system == "Windows":
        os.startfile(str(path))
    elif system == "Darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


__all__ = ["execute", "ExecutorError"]