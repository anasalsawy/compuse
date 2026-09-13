@echo off
REM Builds compuse.exe and CompuseConsole.exe into .\dist
cd /d "%~dp0.."
if not exist .venv (
  echo Create venv first: python -m venv .venv
  exit /b 1
)
.venv\Scripts\python.exe -m pip install --quiet pyinstaller build
.venv\Scripts\python.exe -m PyInstaller --clean -y --noconfirm packaging\spec.spec
echo.
echo Built:
dir /b dist\compuse.exe dist\CompuseConsole.exe 2>nul