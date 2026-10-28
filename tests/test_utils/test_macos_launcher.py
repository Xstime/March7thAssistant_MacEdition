"""Static contracts for native macOS GUI/CLI sharing one .app."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_source_entrypoints_bootstrap_before_importing_project_config():
    for name in ("app.py", "main.py"):
        text = (ROOT / name).read_text(encoding="utf-8")
        assert text.index("bootstrap_runtime()") < text.index("from utils.tasks import AVAILABLE_TASKS")


def test_native_cli_dispatch_happens_before_qt_imports():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    assert 'sys.argv[1] == "--cli"' in app
    assert app.index('runpy.run_module("main"') < app.index("from PySide6.QtCore import")


def test_mac_gui_launches_cli_not_windows_executable():
    log = (ROOT / "app" / "log_interface.py").read_text(encoding="utf-8")
    assert 'arguments = ["--cli", command]' in log
    assert "bundle_resource_dir() / \"main.py\"" in log


def test_native_chrome_cache_is_writable_and_no_forced_unsandboxed_mode():
    cloud = (ROOT / "module" / "game" / "cloud.py").read_text(encoding="utf-8")
    assert '"--browser-version", "stable"' in cloud
    assert "sys.platform == \"win32\"" in cloud
    assert "browser_install_dir" in cloud
