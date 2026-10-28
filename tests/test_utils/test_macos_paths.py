"""Contract tests for the native macOS filesystem layout."""
import os
from pathlib import Path

from utils.macos_paths import (
    application_support_dir,
    browser_profile_dir,
    bundle_resource_dir,
    ensure_data_directories,
    logs_dir,
)


def test_user_directories_are_outside_app_bundle(tmp_path: Path):
    assert application_support_dir(tmp_path) == tmp_path / "Library" / "Application Support" / "March7thAssistant_MacEdition"
    assert logs_dir(tmp_path) == tmp_path / "Library" / "Logs" / "March7thAssistant_MacEdition"
    assert browser_profile_dir(tmp_path) == application_support_dir(tmp_path) / "BrowserProfile"


def test_creates_private_directories(tmp_path: Path):
    ensure_data_directories(tmp_path)
    for path in (application_support_dir(tmp_path), logs_dir(tmp_path), browser_profile_dir(tmp_path)):
        assert path.is_dir()
        if os.name == "posix":
            assert path.stat().st_mode & 0o777 == 0o700
    # Idempotence: repeated startups cannot fail on existing folders.
    ensure_data_directories(tmp_path)


def test_resource_root_exists_for_source_checkout():
    assert bundle_resource_dir().is_dir()
