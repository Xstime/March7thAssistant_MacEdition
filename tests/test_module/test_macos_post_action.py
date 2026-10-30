"""Do not execute upstream Windows post-task commands on macOS."""
from unittest.mock import Mock
from module.game.base import GameControllerBase


def test_macos_skips_windows_post_actions(monkeypatch):
    import module.game.base as base
    monkeypatch.setattr(base.sys, 'platform', 'darwin')
    controller = object.__new__(GameControllerBase)
    controller.stop_game = Mock()
    controller.log_warning = Mock()
    monkeypatch.setattr(base.time, 'sleep', Mock(side_effect=AssertionError('must not wait')))
    monkeypatch.setattr(base.os, 'system', Mock(side_effect=AssertionError('must not execute')))
    assert controller.shutdown('Sleep') is False
    controller.stop_game.assert_called_once_with()
    assert '不支持 macOS' in controller.log_warning.call_args.args[0]
