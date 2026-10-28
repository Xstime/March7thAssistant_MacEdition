# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build for the unofficial Apple Silicon native edition.

Build on an Apple Silicon macOS runner with:
    uv run pyinstaller --noconfirm "March7th MacEdition.spec"
"""
import os
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

if os.uname().sysname != "Darwin" or os.uname().machine != "arm64":
    raise RuntimeError("Build the native edition on an Apple Silicon (arm64) Mac.")

datas = [("assets", "assets")]
if os.path.isdir("3rdparty"):
    datas.append(("3rdparty", "3rdparty"))
datas += collect_data_files("rapidocr")

# OCR uses a CPU fallback; collect native libs where the installed package
# ships them (PyInstaller's built-in hooks collect remaining dependencies).
binaries = collect_dynamic_libs("openvino")

a = Analysis(
    ["app.py"],
    pathex=[os.getcwd()],
    binaries=binaries,
    datas=datas,
    hiddenimports=[
        "main",  # --cli dispatch shares the packaged GUI executable.
        "selenium.webdriver.chrome.webdriver",
        "selenium.webdriver.chrome.service",
        "selenium.webdriver.chrome.options",
        "selenium.webdriver.chromium.webdriver",
        "selenium.webdriver.chromium.service",
        "selenium.webdriver.chromium.options",
        "selenium.webdriver.remote.webdriver",
        "selenium.webdriver.common.selenium_manager",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["winotify", "win32gui", "win32api", "win32con"],
    noarchive=False,
)

pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="March7thAssistant_MacEdition",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    argv_emulation=False,
    target_arch="arm64",
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="March7thAssistant_MacEdition",
)
app = BUNDLE(
    coll,
    name="March7thAssistant_MacEdition.app",
    icon=None,
    bundle_identifier="io.github.xstime.march7thassistant.macedition",
    info_plist={
        "NSHighResolutionCapable": True,
        "NSRequiresAquaSystemAppearance": False,
    },
)
