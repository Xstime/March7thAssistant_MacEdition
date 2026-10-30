"""Exercise main's task dispatch without running its command-line bootstrap."""
import ast
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


def load_dispatch():
    source = (Path(__file__).resolve().parents[2] / 'main.py').read_text(encoding='utf-8')
    node = next(item for item in ast.parse(source).body
                if isinstance(item, ast.FunctionDef) and item.name == 'run_sub_task')
    module = ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[]))
    war = Mock()
    war.start.return_value = False
    daily = Mock()
    daily.run.return_value = False
    reward = Mock()
    game = Mock()
    telemetry = Mock()
    env = {'sys': SimpleNamespace(platform='darwin'), 'cfg': Mock(cloud_game_enable=True),
           'game': game, 'Daily': daily, 'reward': reward, 'CurrencyWars': Mock(return_value=war),
           'DivergentUniverse': Mock(), 'Power': Mock(), 'Fight': Mock(), 'screen_test': Mock(),
           'Universe': Mock(), 'challenge': Mock(), 'Redemption': Mock(), 'cloud_game': Mock(),
           'telemetry': telemetry, 'time': __import__('time'), 'TASK_NAMES': {}}
    exec(compile(module, 'main.py', 'exec'), env)
    return env['run_sub_task'], daily, reward, war, game, telemetry


def test_failed_daily_does_not_continue_to_rewards():
    dispatch, daily, reward, _, game, telemetry = load_dispatch()
    with pytest.raises(RuntimeError, match='任务 daily 未能完成'):
        dispatch('daily')
    daily.run.assert_called_once()
    reward.start.assert_not_called()
    game.stop.assert_not_called()
    assert telemetry.track_task_complete.call_args.args[1] is False


def test_failed_loop_stops_instead_of_retrying_forever():
    dispatch, _, _, war, _, telemetry = load_dispatch()
    with pytest.raises(RuntimeError, match='循环任务 currencywarsloop 未完成'):
        dispatch('currencywarsloop')
    war.start.assert_called_once()
    telemetry.track_task_complete.assert_called_once()
    assert telemetry.track_task_complete.call_args.args[1] is False


def test_takeover_attaches_existing_cloud_game_before_running():
    dispatch, _, _, war, game, telemetry = load_dispatch()
    war.loop.return_value = True
    dispatch('currencywarstemp')
    dispatch.__globals__['cloud_game'].attach_existing_game.assert_called_once()
    game.start.assert_not_called()
    game.switch_to_game.assert_not_called()
    war.loop.assert_called_once()
    assert telemetry.track_task_complete.call_args.args[1] is True


def test_takeover_stops_when_no_existing_game_can_be_attached():
    dispatch, _, _, war, game, telemetry = load_dispatch()
    dispatch.__globals__['cloud_game'].attach_existing_game.side_effect = RuntimeError('没有可接管的云游戏')
    with pytest.raises(RuntimeError, match='没有可接管'):
        dispatch('currencywarstemp')
    war.loop.assert_not_called()
    game.start.assert_not_called()
    telemetry.track_task_complete.assert_not_called()
