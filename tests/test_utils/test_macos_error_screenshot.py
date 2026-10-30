from unittest.mock import Mock
from utils import screenshot_util


def test_macos_errors_do_not_capture_or_expose_login_screen(monkeypatch, tmp_path):
    monkeypatch.setattr(screenshot_util.sys, 'platform', 'darwin')
    monkeypatch.setattr(screenshot_util, 'log_dir', lambda: str(tmp_path))
    logger = Mock()
    assert screenshot_util.save_error_screenshot(logger) is None
    assert list(tmp_path.iterdir()) == []
    assert '避免记录登录信息' in logger.debug.call_args.args[0]
