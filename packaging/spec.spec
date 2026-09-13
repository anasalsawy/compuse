# PyInstaller spec: compuse CLI (compuse.exe) and GUI (CompuseConsole.exe)
from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files("compuse")

for (name, path, console) in (
    ("compuse", "compuse/app/cli.py", True),
    ("CompuseConsole", "compuse/app/gui.py", False),
):
    a = Analysis(
        [path],
        pathex=[],
        binaries=[],
        datas=datas,
        hiddenimports=["pydantic"],
        hookspath=[],
        runtime_hooks=[],
        excludes=[],
        noarchive=False,
    )
    pyz = PYZ(a.pure)
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name=name,
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=console,
        disable_windowed_traceback=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )