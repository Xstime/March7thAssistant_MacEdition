"""Native macOS paths and early process bootstrap.

The upstream app addresses resources and mutable files relative to cwd. A
native .app is installed in a read-only bundle; start inside a private
Application Support workspace, and link only bundled read-only resources.
No Qt or configuration imports are permitted in this early boot module.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


APP_DIRECTORY_NAME = "March7thAssistant_MacEdition"


def is_native_macos() -> bool:
    return sys.platform == "darwin"


def application_support_dir(home: Path | None = None) -> Path:
    home = Path.home() if home is None else Path(home)
    return home / "Library" / "Application Support" / APP_DIRECTORY_NAME


def logs_dir(home: Path | None = None) -> Path:
    home = Path.home() if home is None else Path(home)
    return home / "Library" / "Logs" / APP_DIRECTORY_NAME


def browser_profile_dir(home: Path | None = None) -> Path:
    return application_support_dir(home) / "BrowserProfile"


def browser_install_dir(home: Path | None = None) -> Path:
    return application_support_dir(home) / "WebBrowser"


def bundle_resource_dir() -> Path:
    """Read-only resource root (PyInstaller extraction or source checkout)."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)).resolve()
    return Path(__file__).resolve().parent.parent


def ensure_data_directories(home: Path | None = None) -> None:
    """Restrict credentials and browser profile to the current OS user."""
    for path in (
        application_support_dir(home),
        logs_dir(home),
        browser_profile_dir(home),
        browser_install_dir(home),
    ):
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
        if os.name == "posix":
            path.chmod(0o700)


def _ensure_directory_link(link: Path, target: Path) -> None:
    """Never overwrite real user files; repair old links after app relocation."""
    target = target.resolve()
    if not target.is_dir():
        raise FileNotFoundError(f"Application resource directory not found: {target}")
    if link.is_symlink():
        if link.resolve() == target:
            return
        link.unlink()
    elif link.exists():
        raise RuntimeError(f"Cannot replace existing user data path: {link}")
    link.symlink_to(target, target_is_directory=True)


def bootstrap_runtime() -> Path:
    """Prepare a writable cwd for the existing Python code, once per process.

    This avoids the most dangerous 'freeze' bug: writing config.yaml and logs
    into Contents/MacOS or the read-only PyInstaller resource directory.
    """
    if not is_native_macos():
        raise RuntimeError("Native macOS bootstrap must only run on Darwin")
    ensure_data_directories()
    workspace = application_support_dir()
    resources = bundle_resource_dir()
    for folder in ("assets", "3rdparty"):
        if (resources / folder).is_dir():
            _ensure_directory_link(workspace / folder, resources / folder)
        elif folder == "assets":
            raise FileNotFoundError(f"Bundled assets missing: {resources / folder}")
    _ensure_directory_link(workspace / "logs", logs_dir())
    os.chdir(workspace)
    return workspace
