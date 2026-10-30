"""An unrecognized game screen must not let the task proceed."""
from unittest.mock import Mock

import pytest

import tasks.game as game


def test_exhausted_screen_retries_fail(monkeypatch):
    cloud = Mock()
    cloud.start_game_process.return_value = True
    cloud.is_in_game.return_value = True
    monkeypatch.setattr(game, 'cloud_game', cloud)
    monkeypatch.setattr(game, 'cfg', Mock(cloud_game_enable=True))
    monkeypatch.setattr(game, 'wait_until', Mock(return_value=False))
    monkeypatch.setattr(game, 'log', Mock())
    with pytest.raises(TimeoutError, match='无法识别游戏画面'):
        game.start_game()
    assert cloud.stop_game.call_count == 3
