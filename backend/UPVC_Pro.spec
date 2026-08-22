# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for UPVC Pro desktop app (one-folder build, BROMS-style).

Entry: ../desktop/upvc_desktop.py - starts FastAPI in a thread, then opens a
pywebview window. Bundles the built React app so the frozen exe is
self-contained; the `app` package rides along via collect_submodules.

Run from the backend folder, the same way BROMS builds:
    python -m PyInstaller UPVC_Pro.spec --noconfirm --distpath dist --workpath build
Output: backend/dist/UPVC Pro/UPVC Pro.exe

Verify the result before shipping:
    "dist/UPVC Pro/UPVC Pro.exe" --self-test
"""
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# uvicorn/webview/pyinstaller load protocol + platform backends dynamically
hiddenimports = (
    collect_submodules("uvicorn")
    + collect_submodules("webview")
    + collect_submodules("app")
    + [
        "anyio",
        "bcrypt",
        "passlib",
        "passlib.handlers",
        "passlib.handlers.bcrypt",
        "passlib.context",
        "cryptography",
        "cryptography.hazmat",
        "cryptography.hazmat.primitives",
        "cryptography.hazmat.backends",
        "openpyxl",
        "dateutil",
        "orjson",
        "jose",
        "jose.backends",
        "jose.backends.cryptography_backend",
    ]
)

datas = [
    ("../frontend/dist", "frontend/dist"),  # served by FastAPI (matches _MEIPASS structure)
]
datas += collect_data_files("webview")  # pywebview's bundled JS/HTML

a = Analysis(
    ["../desktop/upvc_desktop.py"],
    pathex=["."],  # so `app` resolves while the spec runs from backend/
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="UPVC Pro",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # windowed desktop app
    disable_windowed_traceback=False,
    icon=None,  # Optional: add icon here
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="UPVC Pro",  # output folder name
)
