"""Rate-limited, private snapshots for macOS UI preview.

Published from screenshots already collected by automation: no additional
Chrome requests or frame capture are needed for the preview panel.
"""
from __future__ import annotations

import os
import tempfile
import threading
import time
from pathlib import Path

from utils.macos_paths import logs_dir


PREVIEW_NAME = "game_preview.bin"
MIN_INTERVAL_SECONDS = 15.0
_last_publish = 0.0
_lock = threading.Lock()


def preview_path(directory: Path | None = None) -> Path:
    return (logs_dir() if directory is None else Path(directory)) / PREVIEW_NAME


def publish_preview(data: bytes, directory: Path | None = None, now: float | None = None) -> bool:
    """Atomically replace one snapshot, at most every 15 s; never raise."""
    global _last_publish
    if not data or len(data) > 10 * 1024 * 1024:
        return False
    now = time.monotonic() if now is None else now
    with _lock:
        if now - _last_publish < MIN_INTERVAL_SECONDS:
            return False
        path = preview_path(directory)
        tmp_name = None
        try:
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            fd, tmp_name = tempfile.mkstemp(prefix=".preview-", dir=path.parent)
            if os.name == "posix":
                os.fchmod(fd, 0o600)
            with os.fdopen(fd, "wb") as out:
                out.write(data)
            os.replace(tmp_name, path)
            _last_publish = now
            return True
        except OSError:
            if tmp_name:
                try:
                    os.unlink(tmp_name)
                except OSError:
                    pass
            return False
