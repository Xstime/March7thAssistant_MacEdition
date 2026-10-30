"""macOS full-run capability and failure reporting."""
from unittest.mock import Mock

import pytest

from tasks.daily import daily


def test_windows_only_task_is_skipped_with_a_reason(monkeypatch):
    monkeypatch.setattr(daily.sys, 'platform', 'darwin')
    log = Mock()
    monkeypatch.setattr(daily, 'log', log)
    action = Mock()
    daily._run_platform_task('fight', action)
    action.assert_not_called()
    assert 'Windows' in log.warning.call_args.args[0]


def test_supported_task_still_runs(monkeypatch):
    monkeypatch.setattr(daily.sys, 'platform', 'darwin')
    action = Mock(return_value='done')
    assert daily._run_platform_task('power', action) == 'done'
    action.assert_called_once_with()


def test_failed_power_stops_daily_run_on_macos(monkeypatch):
    monkeypatch.setattr(daily.sys, 'platform', 'darwin')
    monkeypatch.setattr(daily, 'cfg', Mock(reward_enable=False, power_enable=True,
                                         build_target_enable=False, daily_enable=False,
                                         echo_of_war_enable=False))
    monkeypatch.setattr(daily.Power, 'run_weekly_relic_cleanup', Mock())
    monkeypatch.setattr(daily.Power, 'run', Mock(return_value=False))
    monkeypatch.setattr(daily.activity, 'start', Mock())
    with pytest.raises(RuntimeError, match='清体力未完成'):
        daily.Daily.prepare_daily()


def test_failed_echo_stops_before_spending_power(monkeypatch):
    monkeypatch.setattr(daily.sys, 'platform', 'darwin')
    cfg = Mock(reward_enable=False, power_enable=True, build_target_enable=False,
               daily_enable=False, echo_of_war_enable=True,
               echo_of_war_start_day_of_week=1, echo_of_war_timestamp=0, refresh_hour=4)
    monkeypatch.setattr(daily, 'cfg', cfg)
    monkeypatch.setattr(daily.Date, 'is_next_mon_x_am', Mock(return_value=True))
    monkeypatch.setattr(daily.Power, 'run_weekly_relic_cleanup', Mock())
    monkeypatch.setattr(daily.Power, 'run', Mock())
    monkeypatch.setattr(daily.activity, 'start', Mock())
    monkeypatch.setattr(daily.Echoofwar, 'start', Mock(return_value=False))
    with pytest.raises(RuntimeError, match='历战余响未完成'):
        daily.Daily.prepare_daily()
    daily.Power.run.assert_not_called()


def test_daily_under_target_does_not_record_completion(monkeypatch):
    monkeypatch.setattr(daily.sys, 'platform', 'darwin')
    cfg = Mock()
    cfg.daily_tasks = []
    def set_value(key, value):
        setattr(cfg, key, value)
    cfg.set_value.side_effect = set_value
    monkeypatch.setattr(daily, 'cfg', cfg)
    monkeypatch.setattr(daily, 'log', Mock())
    def lookup():
        cfg.daily_tasks = {'累计消耗120点开拓力': True}
    monkeypatch.setattr(daily.Daily, 'lookup', lookup)
    monkeypatch.setattr(daily.reward, 'start_specific', Mock(return_value=True))
    assert daily.Daily.run() is False
    cfg.save_timestamp.assert_not_called()
    daily.reward.start_specific.assert_not_called()


def test_completed_daily_records_timestamp(monkeypatch):
    monkeypatch.setattr(daily.sys, 'platform', 'darwin')
    cfg = Mock()
    cfg.daily_tasks = []
    cfg.set_value.side_effect = lambda key, value: setattr(cfg, key, value)
    monkeypatch.setattr(daily, 'cfg', cfg)
    monkeypatch.setattr(daily, 'log', Mock())
    def lookup():
        cfg.daily_tasks = {'完成1次「差分宇宙」或「模拟宇宙」': True}
    monkeypatch.setattr(daily.Daily, 'lookup', lookup)
    monkeypatch.setattr(daily.Universe, 'run_daily', Mock(return_value=True))
    monkeypatch.setattr(daily.reward, 'start_specific', Mock(return_value=True))
    daily.Daily.run()
    cfg.save_timestamp.assert_called_once_with('last_run_timestamp')
    daily.reward.start_specific.assert_called_once_with('quest')


def test_missing_daily_ocr_does_not_count_as_completed(monkeypatch):
    monkeypatch.setattr(daily.sys, 'platform', 'darwin')
    monkeypatch.setattr(daily, 'cfg', Mock())
    monkeypatch.setattr(daily, 'log', Mock())
    monkeypatch.setattr(daily, 'screen', Mock())
    tasks = Mock(daily_tasks={}, activity_full=False)
    monkeypatch.setattr(daily, 'Tasks', Mock(return_value=tasks))
    with pytest.raises(RuntimeError, match='无法确认完成状态'):
        daily.Daily.lookup()
    daily.cfg.set_value.assert_not_called()


def test_explicit_full_activity_is_valid_completion_signal(monkeypatch):
    monkeypatch.setattr(daily.sys, 'platform', 'darwin')
    monkeypatch.setattr(daily, 'cfg', Mock())
    monkeypatch.setattr(daily, 'log', Mock())
    monkeypatch.setattr(daily, 'screen', Mock())
    tasks = Mock(daily_tasks={}, activity_full=True)
    monkeypatch.setattr(daily, 'Tasks', Mock(return_value=tasks))
    daily.Daily.lookup()
    daily.cfg.set_value.assert_called_once_with('daily_tasks', {})


def test_full_activity_marker_is_recorded_from_ocr(monkeypatch):
    import tasks.daily.tasks as task_module
    task = object.__new__(task_module.Tasks)
    task.crop = (0, 0, 1, 1)
    task.daily_tasks = {}
    task.activity_full = False
    monkeypatch.setattr(task_module, 'auto', Mock(take_screenshot=Mock(return_value=('frame', None, 1))))
    monkeypatch.setattr(task_module, 'ocr', Mock(recognize_multi_lines=Mock(
        return_value=[([], ('本日活跃度已满', 0.99))])))
    monkeypatch.setattr(task_module, 'log', Mock())
    assert task.detect() is False
    assert task.activity_full is True
