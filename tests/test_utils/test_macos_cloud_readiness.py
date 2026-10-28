"""Cloud controller must be operable without a Windows HWND on macOS."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_cloud_game_uses_cdp_readiness_not_hwnd_on_macos():
    cloud = (ROOT / "module" / "game" / "cloud.py").read_text(encoding="utf-8")
    assert 'def is_game_running(self) -> bool:' in cloud
    assert 'if sys.platform == "darwin":' in cloud
    assert "return self.is_in_game()" in cloud


def test_full_run_skips_windows_updater_on_macos():
    main = (ROOT / "main.py").read_text(encoding="utf-8")
    assert 'if sys.platform != "darwin":' in main
    assert "version.start()" in main
