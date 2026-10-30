"""Challenge failures must not be reported or timestamped as completed runs."""
from importlib import import_module
from unittest.mock import Mock

import pytest


MODES = [('memoryofchaos', 'MemoryOfChaos'), ('purefiction', 'PureFiction'),
         ('apocalyptic', 'Apocalyptic')]


def challenge(module_name, class_name):
    module = import_module(f'tasks.challenge.{module_name}')
    instance = object.__new__(getattr(module, class_name))
    instance.name = 'test challenge'
    instance.max_level = 0
    instance.max_star = 3
    instance.level_range = [1, 2]
    instance.save_timestamp_into_config = Mock()
    return module, instance


@pytest.mark.parametrize('module_name,class_name', MODES)
def test_prepare_failure_is_reported_without_a_completion_timestamp(module_name, class_name):
    _, instance = challenge(module_name, class_name)
    instance.prepare = Mock(return_value=False)
    instance.start_challenges = Mock()
    assert instance.run() is False
    instance.start_challenges.assert_not_called()
    instance.save_timestamp_into_config.assert_not_called()


@pytest.mark.parametrize('module_name,class_name', MODES)
def test_confirmed_full_star_is_a_successful_skip(module_name, class_name):
    _, instance = challenge(module_name, class_name)
    instance.prepare = Mock(return_value=None)
    instance.start_challenges = Mock()
    assert instance.run() is True
    instance.start_challenges.assert_not_called()


@pytest.mark.parametrize('module_name,class_name', MODES)
@pytest.mark.parametrize('failure', ['missing_level', 'lost_battle'])
def test_challenge_failure_does_not_collect_or_timestamp(module_name, class_name, failure, monkeypatch):
    module, instance = challenge(module_name, class_name)
    instance.prepare = Mock(return_value=True)
    instance.find_level = Mock(return_value=False if failure == 'missing_level' else (10, 10))
    instance.judge_stars = Mock(return_value=0)
    instance.start_challenge = Mock(return_value=False)
    instance.collect_rewards = Mock()
    monkeypatch.setattr(module.time, 'sleep', lambda _: None)
    monkeypatch.setattr(module.auto, 'mouse_scroll', Mock())
    assert instance.run() is False
    instance.collect_rewards.assert_not_called()
    instance.save_timestamp_into_config.assert_not_called()


@pytest.mark.parametrize('module_name,class_name', MODES)
def test_selected_full_star_levels_record_completion(module_name, class_name, monkeypatch):
    module, instance = challenge(module_name, class_name)
    instance.prepare = Mock(return_value=True)
    instance.find_level = Mock(return_value=(10, 10))
    instance.judge_stars = Mock(return_value=3)
    instance.start_challenge = Mock()
    monkeypatch.setattr(module.time, 'sleep', lambda _: None)
    monkeypatch.setattr(module.auto, 'mouse_scroll', Mock())
    monkeypatch.setattr(module.auto, 'find_element', Mock(return_value=False))
    assert instance.run() is True
    instance.start_challenge.assert_not_called()
    instance.save_timestamp_into_config.assert_called_once()


@pytest.mark.parametrize('module_name,class_name', MODES)
@pytest.mark.parametrize('clicks,expected', [([True, True, True, False], True),
                                           ([False], False), ([True, False], False),
                                           ([True, True, False], False)])
def test_reward_confirmation_controls_completion_timestamp(module_name, class_name, clicks, expected, monkeypatch):
    module, instance = challenge(module_name, class_name)
    instance.max_level = 1
    monkeypatch.setattr(module.time, 'sleep', lambda _: None)
    monkeypatch.setattr(module.screen, 'wait_for_screen_change', Mock())
    monkeypatch.setattr(module.auto, 'click_element', Mock(side_effect=clicks))
    monkeypatch.setattr(module.auto, 'press_key', Mock())
    monkeypatch.setattr(module.Base, 'send_notification_with_screenshot', Mock())
    assert instance.collect_rewards() is expected
    assert instance.save_timestamp_into_config.call_count == (1 if expected else 0)


def test_challenge_dispatch_returns_failure(monkeypatch):
    from tasks import challenge as challenge_module
    manager = object.__new__(challenge_module.ChallengeManager)
    manager.game_modes = {'purefiction': Mock(run=Mock(return_value=False))}
    monkeypatch.setattr(challenge_module, 'ChallengeManager', Mock(return_value=manager))
    assert challenge_module.start('purefiction') is False


@pytest.mark.parametrize('setting,mode,label', [
    ('forgottenhall_enable', 'memoryofchaos', '忘却之庭'),
    ('purefiction_enable', 'purefiction', '虚构叙事'),
    ('apocalyptic_enable', 'apocalyptic', '末日幻影'),
])
def test_complete_run_propagates_challenge_failure(setting, mode, label, monkeypatch):
    module = import_module('tasks.daily.daily')
    from types import SimpleNamespace
    monkeypatch.setattr(module, 'sys', SimpleNamespace(platform='darwin'))
    config = Mock(asset_manager_enable=False, currencywars_enable=False,
                  weekly_divergent_enable=False, fight_enable=False,
                  universe_frequency='disabled', forgottenhall_enable=False,
                  purefiction_enable=False, apocalyptic_enable=False)
    setattr(config, setting, True)
    monkeypatch.setattr(module, 'cfg', config)
    monkeypatch.setattr(module.Daily, 'prepare_daily', Mock())
    monkeypatch.setattr(module, 'DivergentUniverse', Mock())
    monkeypatch.setattr(module.Date, 'is_next_mon_x_am', Mock(return_value=True))
    monkeypatch.setattr(module.challenge, 'start', Mock(return_value=False))
    monkeypatch.setattr(module, 'set_phase', Mock())
    with pytest.raises(RuntimeError, match=label):
        module.Daily.start()
    module.challenge.start.assert_called_once_with(mode)


@pytest.mark.parametrize('module_name,class_name', MODES)
def test_prepare_only_skips_after_recognizing_full_stars(module_name, class_name, monkeypatch):
    module, instance = challenge(module_name, class_name)
    instance.check_star_in_ocr_results = Mock(return_value=True)
    monkeypatch.setattr(module.time, 'sleep', lambda _: None)
    monkeypatch.setattr(module.screen, 'change_to', Mock())
    monkeypatch.setattr(module.auto, 'click_element', Mock(return_value=True))
    monkeypatch.setattr(module.auto, 'find_element', Mock(return_value=True))
    monkeypatch.setattr(module.auto, 'ocr_result', [], raising=False)
    assert instance.prepare() is None
    instance.save_timestamp_into_config.assert_called_once()


@pytest.mark.parametrize('module_name,class_name', MODES)
def test_reward_loop_has_a_limit_and_does_not_mark_complete(module_name, class_name, monkeypatch):
    module, instance = challenge(module_name, class_name)
    instance.max_level = 1
    monkeypatch.setattr(module.time, 'sleep', lambda _: None)
    monkeypatch.setattr(module.screen, 'wait_for_screen_change', Mock())
    monkeypatch.setattr(module.auto, 'click_element', Mock(return_value=True))
    assert instance.collect_rewards() is False
    instance.save_timestamp_into_config.assert_not_called()
