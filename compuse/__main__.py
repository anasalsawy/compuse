"""Entry points for running compuse as an application.

``pip install .`` registers ``compuse`` (CLI) and ``compuse-gui`` (desktop)
console scripts. PyInstaller ``--name`` targets these modules directly.
"""
from __future__ import annotations

from compuse.app.cli import main

if __name__ == "__main__":
    raise SystemExit(main())