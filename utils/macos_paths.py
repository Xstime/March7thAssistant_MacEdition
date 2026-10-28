"""Paths for the native macOS edition.

Keep mutable user data outside the signed/read-only .app bundle.  This module
has no Qt or application imports so it can be tested before the GUI boots.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


APP_DIRECTORY_NAME = "March7thAssistant_MacEdition"


def is_native_macos() -> bool:
    return sys.platform == "darwin"


def application_support_dir(home: Path | None = None) -> Path:
    """Return the per-user, writable data directory (no directory creation)."""
    home = Path.home() if home is None else Path(home)
    return home / "Library" / "Application Support" / APP_DIRECTORY_NAME


def logs_dir(home: Path | None = None) -> Path:
    """Return the per-user log directory (no directory creation)."""
    home = Path.home() if home is None else Path(home)
    return home / "Library" / "Logs" / APP_DIRECTORY_NAME


def browser_profile_dir(home: Path | None = None) -> Path:
    """Use an isolated Chrome profile; never overwrite the user's Chrome data."""
    return application_support_dir(home) / "BrowserProfile"


def bundle_resource_dir() -> Path:
    """Resource root for scripts or PyInstaller frozen macOS app bundles.

    The caller should supply packaged assets through the build specification.
    Avoid writing into this directory.
    """
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)).resolve()
    return Path(__file__).resolve().parent.parent


def ensure_data_directories(home: Path | None = None) -> None:
    """Create only the writable per-user directories with restrictive permissions."""
    for path in (application_support_dir(home), logs_dir(home), browser_profile_dir(home)):
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
        if os.name == "posix":
            path.chmod(0o700)
