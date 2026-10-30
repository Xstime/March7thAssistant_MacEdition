from unittest.mock import Mock, call
import pytest
import tasks.activity as activity


def test_macos_activity_failure_has_bounded_backoff(monkeypatch):
    monkeypatch.setattr(activity.sys, 'platform', 'darwin')
    monkeypatch.setattr(activity, 'log', Mock())
    sleep = Mock()
    monkeypatch.setattr(activity.time, 'sleep', sleep)
    task = Mock(return_value=False)
    manager = object.__new__(activity.ActivityManager)
    manager._get_activity_names = Mock(return_value=['花藏繁生'])
    manager._finish = Mock()
    manager.activity_functions = {'花藏繁生': task}
    with pytest.raises(RuntimeError, match='连续三次未完成'):
        manager.check_and_run_activities()
    assert task.call_count == 3
    assert sleep.call_args_list == [call(1), call(2)]
    manager._finish.assert_not_called()


def test_macos_activity_success_after_retry(monkeypatch):
    monkeypatch.setattr(activity.sys, 'platform', 'darwin')
    monkeypatch.setattr(activity, 'log', Mock())
    monkeypatch.setattr(activity.time, 'sleep', Mock())
    task = Mock(side_effect=[False, True])
    manager = object.__new__(activity.ActivityManager)
    manager._get_activity_names = Mock(return_value=['花藏繁生'])
    manager._finish = Mock()
    manager.activity_functions = {'花藏繁生': task}
    manager.check_and_run_activities()
    assert task.call_count == 2
    manager._finish.assert_called_once()


def test_macos_activity_entrypoint_reports_failure(monkeypatch):
    monkeypatch.setattr(activity.sys, 'platform', 'darwin')
    monkeypatch.setattr(activity, 'log', Mock())
    monkeypatch.setattr(activity, 'cfg', Mock(activity_enable=True,
                                             activity_journey_highlights_notification_enable=False))
    manager = Mock()
    manager.check_and_run_activities.side_effect = RuntimeError('failure')
    monkeypatch.setattr(activity, 'ActivityManager', Mock(return_value=manager))
    with pytest.raises(RuntimeError, match='活动处理失败'):
        activity.start()
