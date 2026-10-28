"""Tests for macOS workspace paths: do not create files in the real home."""
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from utils.macos_paths import (
    _ensure_directory_link,
    application_support_dir,
    browser_install_dir,
    browser_profile_dir,
    bundle_resource_dir,
    ensure_data_directories,
    logs_dir,
)


def test_private_user_directories(tmp_path: Path):
    assert application_support_dir(tmp_path) == tmp_path / "Library" / "Application Support" / "March7thAssistant_MacEdition"
    assert logs_dir(tmp_path) == tmp_path / "Library" / "Logs" / "March7thAssistant_MacEdition"
    assert browser_profile_dir(tmp_path) == application_support_dir(tmp_path) / "BrowserProfile"
    assert browser_install_dir(tmp_path) == application_support_dir(tmp_path) / "WebBrowser"
    ensure_data_directories(tmp_path)
    for p in (application_support_dir(tmp_path), logs_dir(tmp_path), browser_profile_dir(tmp_path), browser_install_dir(tmp_path)):
        assert p.is_dir()
        if os.name == "posix":
            assert p.stat().st_mode & 0o777 == 0o700
    ensure_data_directories(tmp_path)


def test_resource_symlink_relocation_and_data_protection(tmp_path: Path):
    first, second = tmp_path / "first", tmp_path / "second"
    first.mkdir()
    second.mkdir()
    link = tmp_path / "assets"
    _ensure_directory_link(link, first)
    _ensure_directory_link(link, first)
    assert link.resolve() == first
    _ensure_directory_link(link, second)
    assert link.resolve() == second


def test_never_replace_user_directory(tmp_path: Path):
    target = tmp_path / "target"
    target.mkdir()
    occupied = tmp_path / "assets"
    occupied.mkdir()
    with pytest.raises(RuntimeError):
        _ensure_directory_link(occupied, target)
    assert occupied.is_dir() and not occupied.is_symlink()


def test_bootstrap_workspace(tmp_path: Path, monkeypatch):
    import utils.macos_paths as m
    root = tmp_path / "resources"
    (root / "assets").mkdir(parents=True)
    (root / "3rdparty").mkdir()
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(m, "is_native_macos", lambda: True)
    monkeypatch.setattr(m, "bundle_resource_dir", lambda: root)
    # Do not change cwd outside context, as this breaks unrelated tests.
    previous_cwd = Path.cwd()
    try:
        with patch.object(Path, "home", return_value=home):
            assert m.bootstrap_runtime() == application_support_dir(home)
            assert (application_support_dir(home) / "assets").resolve() == (root / "assets")
            assert (application_support_dir(home) / "logs").resolve() == logs_dir(home)
            assert Path.cwd() == application_support_dir(home)
    finally:
        os.chdir(previous_cwd)


def test_resource_root_exists():
    assert bundle_resource_dir().is_dir()
