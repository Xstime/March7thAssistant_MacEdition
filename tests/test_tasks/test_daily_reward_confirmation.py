"""Daily completion requires evidence and bounded reward handling."""
from unittest.mock import Mock
import pytest
from tasks.daily import daily
from tasks.reward import RewardManager
from tasks.reward import quest as quest_module


def test_specific_daily_checks_full_marker_even_without_badge():
    manager = object.__new__(RewardManager)
    instance = Mock(name='每日实训', start=Mock(return_value=True))
    manager.reward_instances = {'quest': instance}
    manager.reward_mapping = {'quest': ('unused', 0.9, None)}
    manager._find_reward = Mock(return_value=False)
    assert manager.check_and_collect_specific_reward('quest') is True
    instance.start.assert_called_once()
    manager._find_reward.assert_not_called()


@pytest.mark.parametrize('clicks,finds,expected', [
    ([False, False], [True, True], True),
    ([False, False], [True, False], False),
    ([False, False], [False], False),
    ([False, True, False], [], False),
])
def test_daily_reward_requires_full_marker_and_closable_dialog(monkeypatch, clicks, finds, expected):
    task = object.__new__(quest_module.Quest)
    monkeypatch.setattr(quest_module.time, 'sleep', lambda _: None)
    monkeypatch.setattr(quest_module, 'cfg', Mock(notify_template={'DailyPracticeNotCompleted': 'not complete'}))
    monkeypatch.setattr(quest_module, 'auto', Mock(click_element=Mock(side_effect=clicks),
                                                   find_element=Mock(side_effect=finds)))
    monkeypatch.setattr(quest_module.Base, 'send_notification_with_screenshot', Mock())
    assert task.run() is expected
    assert quest_module.cfg.set_value.call_count == (1 if expected else 0)


def test_daily_reward_loop_stops_after_limit(monkeypatch):
    task = object.__new__(quest_module.Quest)
    monkeypatch.setattr(quest_module.time, 'sleep', lambda _: None)
    monkeypatch.setattr(quest_module, 'auto', Mock(click_element=Mock(return_value=True)))
    assert task.run() is False
    assert quest_module.auto.click_element.call_count == 20


@pytest.mark.parametrize('reward_enabled,quest_enabled,verified,expect_timestamp', [
    (True, True, False, False),
    (True, True, True, True),
    (False, True, False, True),
    (True, False, False, True),
])
def test_daily_only_records_confirmed_or_intentionally_disabled_reward(monkeypatch, reward_enabled, quest_enabled,
                                                                         verified, expect_timestamp):
    cfg = Mock(reward_enable=reward_enabled, reward_quest_enable=quest_enabled)
    cfg.daily_tasks = []
    cfg.set_value.side_effect = lambda key, value: setattr(cfg, key, value)
    monkeypatch.setattr(daily, 'cfg', cfg)
    monkeypatch.setattr(daily, 'log', Mock())
    monkeypatch.setattr(daily.Daily, 'lookup', lambda: setattr(cfg, 'daily_tasks', {}))
    monkeypatch.setattr(daily.reward, 'start_specific', Mock(return_value=verified))
    monkeypatch.setattr(daily.sys, 'platform', 'darwin')
    result = daily.Daily.run()
    assert cfg.save_timestamp.call_count == (1 if expect_timestamp else 0)
    if not expect_timestamp:
        assert result is False
