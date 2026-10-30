from PySide6.QtCore import QDateTime
from types import SimpleNamespace, MethodType
from unittest.mock import Mock
import pytest

from app.common.schedule import missed_schedule_slot


def date(text):
    return QDateTime.fromString(text, 'yyyy-MM-ddTHH:mm:ss')


def test_wake_finds_latest_missed_daily_slot_without_current_minute():
    task = {'time': '04:00'}
    before = date('2026-10-20T03:00:00').toSecsSinceEpoch() // 60
    now = date('2026-10-21T04:00:30')
    assert missed_schedule_slot(task, before, now) == date('2026-10-20T04:00:00').toSecsSinceEpoch()


def test_missed_slot_respects_weekdays_and_start_boundary():
    task = {'time': '04:00', 'weekdays': [1]}
    before = date('2026-10-18T12:00:00').toSecsSinceEpoch() // 60
    now = date('2026-10-21T10:00:00')
    monday = date('2026-10-19T04:00:00').toSecsSinceEpoch()
    assert missed_schedule_slot(task, before, now) == monday
    assert missed_schedule_slot(task, monday // 60, now) is None


def test_invalid_schedule_is_not_replayed():
    assert missed_schedule_slot({'time': 'broken'}, 0, date('2026-10-21T10:00:00')) is None


def test_wake_logs_missed_task_and_runs_it_only_when_enabled(monkeypatch):
    from app import log_interface
    task = {'id': 'daily', 'name': '每日任务', 'time': '04:00', 'program': 'self', 'args': 'daily'}
    settings = {'scheduled_tasks': [task], 'macos_schedule_catch_up': False}
    monkeypatch.setattr(log_interface.cfg, 'get_value', lambda key, default=None: settings.get(key, default))
    interface = SimpleNamespace(_last_triggered_ts={}, appendLog=Mock(),
                                isTaskRunning=Mock(return_value=False), _pause_state='running',
                                runScheduledTask=Mock())
    interface._isScheduleCatchUpBusy = MethodType(log_interface.LogInterface._isScheduleCatchUpBusy, interface)
    interface._runPendingMissedSchedule = MethodType(log_interface.LogInterface._runPendingMissedSchedule, interface)
    previous = date('2026-10-20T03:00:00').toSecsSinceEpoch() // 60
    now = date('2026-10-20T07:00:00')
    log_interface.LogInterface._handleMissedSchedules(interface, previous, now)
    assert '延误' in interface.appendLog.call_args_list[0].args[0]
    interface.runScheduledTask.assert_not_called()
    settings['macos_schedule_catch_up'] = True
    log_interface.LogInterface._handleMissedSchedules(interface, previous, now)
    interface.runScheduledTask.assert_called_once_with(task, tasks=[task], manual=False)
    log_interface.LogInterface._handleMissedSchedules(interface, previous, now)
    assert interface.runScheduledTask.call_count == 1


def test_wake_does_not_interrupt_running_task(monkeypatch):
    from app import log_interface
    task = {'id': 'daily', 'time': '04:00'}
    monkeypatch.setattr(log_interface.cfg, 'get_value', lambda key, default=None:
                        {'scheduled_tasks': [task], 'macos_schedule_catch_up': True}.get(key, default))
    interface = SimpleNamespace(_last_triggered_ts={}, appendLog=Mock(),
                                isTaskRunning=Mock(return_value=True), _pause_state='running',
                                runScheduledTask=Mock())
    interface._isScheduleCatchUpBusy = MethodType(log_interface.LogInterface._isScheduleCatchUpBusy, interface)
    interface._runPendingMissedSchedule = MethodType(log_interface.LogInterface._runPendingMissedSchedule, interface)
    previous = date('2026-10-20T03:00:00').toSecsSinceEpoch() // 60
    log_interface.LogInterface._handleMissedSchedules(interface, previous, date('2026-10-20T07:00:00'))
    interface.runScheduledTask.assert_not_called()


def test_busy_catchup_runs_once_when_idle(monkeypatch):
    from app import log_interface
    task = {'id': 'daily', 'name': '每日任务', 'time': '04:00'}
    settings = {'scheduled_tasks': [task], 'macos_schedule_catch_up': True}
    monkeypatch.setattr(log_interface.cfg, 'get_value', lambda key, default=None: settings.get(key, default))
    interface = SimpleNamespace(_last_triggered_ts={}, appendLog=Mock(),
                                isTaskRunning=Mock(return_value=True), _pause_state='running',
                                runScheduledTask=Mock(return_value=True), _pending_missed_schedule=None)
    interface._isScheduleCatchUpBusy = MethodType(log_interface.LogInterface._isScheduleCatchUpBusy, interface)
    interface._runPendingMissedSchedule = MethodType(log_interface.LogInterface._runPendingMissedSchedule, interface)
    previous = date('2026-10-20T03:00:00').toSecsSinceEpoch() // 60
    log_interface.LogInterface._handleMissedSchedules(interface, previous, date('2026-10-20T07:00:00'))
    assert interface._pending_missed_schedule['task'] == task
    interface.runScheduledTask.assert_not_called()
    interface.isTaskRunning.return_value = False
    interface._runPendingMissedSchedule()
    interface._runPendingMissedSchedule()
    interface.runScheduledTask.assert_called_once_with(task, tasks=[task], manual=False)
    assert interface._pending_missed_schedule is None


def test_deferred_catchup_does_not_run_edited_or_disabled_task(monkeypatch):
    from app import log_interface
    task = {'id': 'daily', 'name': '每日任务', 'time': '04:00'}
    settings = {'scheduled_tasks': [task], 'macos_schedule_catch_up': True}
    monkeypatch.setattr(log_interface.cfg, 'get_value', lambda key, default=None: settings.get(key, default))
    interface = SimpleNamespace(_last_triggered_ts={}, appendLog=Mock(),
                                isTaskRunning=Mock(return_value=True), _pause_state='running',
                                runScheduledTask=Mock(return_value=True), _pending_missed_schedule=None)
    interface._isScheduleCatchUpBusy = MethodType(log_interface.LogInterface._isScheduleCatchUpBusy, interface)
    interface._runPendingMissedSchedule = MethodType(log_interface.LogInterface._runPendingMissedSchedule, interface)
    previous = date('2026-10-20T03:00:00').toSecsSinceEpoch() // 60
    log_interface.LogInterface._handleMissedSchedules(interface, previous, date('2026-10-20T07:00:00'))
    task['enabled'] = False
    interface.isTaskRunning.return_value = False
    interface._runPendingMissedSchedule()
    interface.runScheduledTask.assert_not_called()
    assert interface._pending_missed_schedule is None
    assert '停用' in interface.appendLog.call_args.args[0]


def test_clock_rollback_does_not_retrigger_past_slots(monkeypatch):
    from app import log_interface
    minute = [2000]
    class Clock:
        @staticmethod
        def currentDateTime():
            return SimpleNamespace(toSecsSinceEpoch=lambda: minute[0] * 60)
    monkeypatch.setattr(log_interface, 'QDateTime', Clock)
    monkeypatch.setattr(log_interface, 'milliseconds_to_next_minute', lambda now: 1000)
    monkeypatch.setattr(log_interface, '_schedule_event', Mock())
    monkeypatch.setattr(log_interface, 'write_checkpoint', Mock())
    interface = SimpleNamespace(_schedule_running=True, _last_schedule_minute=2000,
                                _schedule_ignore_until_minute=None, _schedule_timer=Mock(),
                                _checkScheduledTime=Mock(), _handleMissedSchedules=Mock(),
                                _runPendingMissedSchedule=Mock(), _pending_missed_schedule=None,
                                appendLog=Mock())
    minute[0] = 1999
    log_interface.LogInterface._onScheduleTimerTimeout(interface)
    assert interface._schedule_ignore_until_minute == 2000
    minute[0] = 2000
    log_interface.LogInterface._onScheduleTimerTimeout(interface)
    interface._checkScheduledTime.assert_not_called()
    minute[0] = 2001
    log_interface.LogInterface._onScheduleTimerTimeout(interface)
    interface._checkScheduledTime.assert_called_once()
    assert interface._schedule_ignore_until_minute is None


def test_startup_recovers_previous_checkpoint_after_initialization(monkeypatch):
    from app import log_interface
    now = date('2026-10-21T10:00:00')
    class Clock:
        @staticmethod
        def currentDateTime():
            return now
    callbacks = []
    monkeypatch.setattr(log_interface, 'QDateTime', Clock)
    monkeypatch.setattr(log_interface, 'milliseconds_to_next_minute', lambda value: 1000)
    monkeypatch.setattr(log_interface, 'read_checkpoint', lambda: now.toSecsSinceEpoch() // 60 - 180)
    monkeypatch.setattr(log_interface, 'write_checkpoint', Mock())
    monkeypatch.setattr(log_interface.QTimer, 'singleShot', lambda delay, callback: callbacks.append(callback))
    interface = SimpleNamespace(_schedule_timer=Mock(), _schedule_running=False,
                                _recoverSchedulesAtStartup=Mock(), appendLog=Mock())
    log_interface.LogInterface._startScheduleTimer(interface)
    assert len(callbacks) == 1
    interface._recoverSchedulesAtStartup.assert_not_called()
    callbacks[0]()
    interface._recoverSchedulesAtStartup.assert_called_once_with(now.toSecsSinceEpoch() // 60 - 180)
    log_interface.write_checkpoint.assert_not_called()


def test_startup_retains_checkpoint_while_catchup_is_queued(monkeypatch):
    from app import log_interface
    now = date('2026-10-21T10:00:00')
    class Clock:
        @staticmethod
        def currentDateTime():
            return now
    monkeypatch.setattr(log_interface, 'QDateTime', Clock)
    checkpoint = Mock()
    monkeypatch.setattr(log_interface, 'write_checkpoint', checkpoint)
    interface = SimpleNamespace(_schedule_running=True, _checkScheduledTime=Mock(),
                                _handleMissedSchedules=Mock(), _runPendingMissedSchedule=Mock(),
                                _pending_missed_schedule={'slot': 123}, appendLog=Mock())
    previous = now.toSecsSinceEpoch() // 60 - 180
    log_interface.LogInterface._recoverSchedulesAtStartup(interface, previous)
    interface._handleMissedSchedules.assert_called_once_with(previous, now)
    checkpoint.assert_not_called()
    interface._pending_missed_schedule = None
    log_interface.LogInterface._recoverSchedulesAtStartup(interface, previous)
    checkpoint.assert_called_once_with(now.toSecsSinceEpoch() // 60)


def test_more_recent_execution_prevents_older_catchup(monkeypatch):
    from app import log_interface
    task = {'id': 'daily', 'time': '04:00'}
    monkeypatch.setattr(log_interface.cfg, 'get_value', lambda key, default=None:
                        {'scheduled_tasks': [task], 'macos_schedule_catch_up': True}.get(key, default))
    current_slot = date('2026-10-21T04:00:00').toSecsSinceEpoch()
    interface = SimpleNamespace(_last_triggered_ts={'daily': current_slot}, appendLog=Mock(),
                                isTaskRunning=Mock(return_value=False), _pause_state='running',
                                runScheduledTask=Mock(return_value=True), _pending_missed_schedule=None)
    interface._isScheduleCatchUpBusy = MethodType(log_interface.LogInterface._isScheduleCatchUpBusy, interface)
    interface._runPendingMissedSchedule = MethodType(log_interface.LogInterface._runPendingMissedSchedule, interface)
    previous = date('2026-10-20T03:00:00').toSecsSinceEpoch() // 60
    log_interface.LogInterface._handleMissedSchedules(interface, previous, date('2026-10-21T04:00:30'))
    interface.runScheduledTask.assert_not_called()
    assert interface._pending_missed_schedule is None


def test_reopen_recovers_missed_schedule_and_commits_checkpoint(monkeypatch):
    from app import log_interface
    now = date('2026-10-20T07:00:00')
    class Clock:
        @staticmethod
        def currentDateTime():
            return now
        @staticmethod
        def fromSecsSinceEpoch(value):
            return QDateTime.fromSecsSinceEpoch(value)
    task = {'id': 'daily', 'name': '每日任务', 'time': '04:00'}
    settings = {'scheduled_tasks': [task], 'macos_schedule_catch_up': True}
    monkeypatch.setattr(log_interface.cfg, 'get_value', lambda key, default=None: settings.get(key, default))
    monkeypatch.setattr(log_interface, 'QDateTime', Clock)
    checkpoint = Mock()
    monkeypatch.setattr(log_interface, 'write_checkpoint', checkpoint)
    interface = SimpleNamespace(_schedule_running=True, _last_triggered_ts={}, appendLog=Mock(),
                                isTaskRunning=Mock(return_value=False), _pause_state='running',
                                runScheduledTask=Mock(return_value=True), _pending_missed_schedule=None,
                                _checkScheduledTime=Mock())
    interface._isScheduleCatchUpBusy = MethodType(log_interface.LogInterface._isScheduleCatchUpBusy, interface)
    interface._runPendingMissedSchedule = MethodType(log_interface.LogInterface._runPendingMissedSchedule, interface)
    interface._handleMissedSchedules = MethodType(log_interface.LogInterface._handleMissedSchedules, interface)
    previous = date('2026-10-20T03:00:00').toSecsSinceEpoch() // 60
    log_interface.LogInterface._recoverSchedulesAtStartup(interface, previous)
    interface.runScheduledTask.assert_called_once_with(task, tasks=[task], manual=False)
    checkpoint.assert_called_once_with(now.toSecsSinceEpoch() // 60)


def test_catchup_start_failure_is_recorded_and_not_repeated(monkeypatch):
    from app import log_interface
    task = {'id': 'daily', 'time': '04:00'}
    monkeypatch.setattr(log_interface.cfg, 'get_value', lambda key, default=None:
                        {'scheduled_tasks': [task], 'macos_schedule_catch_up': True}.get(key, default))
    interface = SimpleNamespace(_last_triggered_ts={}, appendLog=Mock(),
                                isTaskRunning=Mock(return_value=False), _pause_state='running',
                                runScheduledTask=Mock(return_value=False), _pending_missed_schedule=None)
    interface._isScheduleCatchUpBusy = MethodType(log_interface.LogInterface._isScheduleCatchUpBusy, interface)
    interface._runPendingMissedSchedule = MethodType(log_interface.LogInterface._runPendingMissedSchedule, interface)
    previous = date('2026-10-20T03:00:00').toSecsSinceEpoch() // 60
    now = date('2026-10-20T07:00:00')
    log_interface.LogInterface._handleMissedSchedules(interface, previous, now)
    log_interface.LogInterface._handleMissedSchedules(interface, previous, now)
    interface.runScheduledTask.assert_called_once()
    assert any('未能启动' in c.args[0] for c in interface.appendLog.call_args_list)


def test_reopen_with_catchup_disabled_logs_but_does_not_run(monkeypatch):
    from app import log_interface
    now = date('2026-10-20T07:00:00')
    class Clock:
        @staticmethod
        def currentDateTime():
            return now
        @staticmethod
        def fromSecsSinceEpoch(value):
            return QDateTime.fromSecsSinceEpoch(value)
    task = {'id': 'daily', 'name': '每日任务', 'time': '04:00'}
    monkeypatch.setattr(log_interface.cfg, 'get_value', lambda key, default=None:
                        {'scheduled_tasks': [task], 'macos_schedule_catch_up': False}.get(key, default))
    monkeypatch.setattr(log_interface, 'QDateTime', Clock)
    checkpoint = Mock()
    monkeypatch.setattr(log_interface, 'write_checkpoint', checkpoint)
    interface = SimpleNamespace(_schedule_running=True, _last_triggered_ts={}, appendLog=Mock(),
                                isTaskRunning=Mock(return_value=False), _pause_state='running',
                                runScheduledTask=Mock(), _pending_missed_schedule=None,
                                _checkScheduledTime=Mock())
    interface._isScheduleCatchUpBusy = MethodType(log_interface.LogInterface._isScheduleCatchUpBusy, interface)
    interface._runPendingMissedSchedule = MethodType(log_interface.LogInterface._runPendingMissedSchedule, interface)
    interface._handleMissedSchedules = MethodType(log_interface.LogInterface._handleMissedSchedules, interface)
    previous = date('2026-10-20T03:00:00').toSecsSinceEpoch() // 60
    log_interface.LogInterface._recoverSchedulesAtStartup(interface, previous)
    interface.runScheduledTask.assert_not_called()
    assert any('已按设置跳过' in c.args[0] for c in interface.appendLog.call_args_list)
    checkpoint.assert_called_once_with(now.toSecsSinceEpoch() // 60)


def test_scheduled_task_does_not_interrupt_process_that_is_starting(monkeypatch):
    from app import log_interface
    task = {'id': 'daily', 'name': '每日任务', 'time': '04:00', 'enabled': True}
    monkeypatch.setattr(log_interface.cfg, 'get_value', lambda key, default=None:
                        {'scheduled_tasks': [task], 'scheduled_on_conflict': 'skip'}.get(key, default))
    interface = SimpleNamespace(_pause_state='running', _last_triggered_ts={}, appendLog=Mock(),
                                _updateScheduleStatusLabel=Mock(), isTaskRunning=Mock(return_value=False),
                                _hasActiveStartedProcess=Mock(return_value=True), runScheduledTask=Mock())
    log_interface.LogInterface._checkScheduledTime(interface, date('2026-10-20T04:00:00'))
    interface.runScheduledTask.assert_not_called()
    assert any('跳过计划任务' in c.args[0] for c in interface.appendLog.call_args_list)


def test_paused_at_scheduled_minute_defers_until_idle_when_catchup_enabled(monkeypatch):
    from app import log_interface
    task = {'id': 'daily', 'name': '每日任务', 'time': '04:00', 'enabled': True}
    monkeypatch.setattr(log_interface.cfg, 'get_value', lambda key, default=None:
                        {'scheduled_tasks': [task], 'macos_schedule_catch_up': True}.get(key, default))
    interface = SimpleNamespace(_pause_state=log_interface.STATE_PAUSED, _last_triggered_ts={},
                                _pending_missed_schedule=None, appendLog=Mock(),
                                _updateScheduleStatusLabel=Mock(), isTaskRunning=Mock(return_value=True),
                                runScheduledTask=Mock(return_value=True))
    interface._isScheduleCatchUpBusy = MethodType(log_interface.LogInterface._isScheduleCatchUpBusy, interface)
    interface._runPendingMissedSchedule = MethodType(log_interface.LogInterface._runPendingMissedSchedule, interface)
    now = date('2026-10-20T04:00:00')
    log_interface.LogInterface._checkScheduledTime(interface, now)
    assert interface._pending_missed_schedule['task'] == task
    interface.runScheduledTask.assert_not_called()
    interface._pause_state = log_interface.STATE_RUNNING
    interface.isTaskRunning.return_value = False
    interface._runPendingMissedSchedule()
    interface.runScheduledTask.assert_called_once()
    assert interface._pending_missed_schedule is None


def test_paused_at_scheduled_minute_logs_skip_when_catchup_disabled(monkeypatch):
    from app import log_interface
    task = {'id': 'daily', 'name': '每日任务', 'time': '04:00', 'enabled': True}
    monkeypatch.setattr(log_interface.cfg, 'get_value', lambda key, default=None:
                        {'scheduled_tasks': [task], 'macos_schedule_catch_up': False}.get(key, default))
    interface = SimpleNamespace(_pause_state=log_interface.STATE_PAUSED, _last_triggered_ts={},
                                _pending_missed_schedule=None, appendLog=Mock(),
                                _updateScheduleStatusLabel=Mock(), runScheduledTask=Mock())
    now = date('2026-10-20T04:00:00')
    log_interface.LogInterface._checkScheduledTime(interface, now)
    log_interface.LogInterface._checkScheduledTime(interface, now)
    assert interface._pending_missed_schedule is None
    interface.runScheduledTask.assert_not_called()
    assert sum('按设置跳过' in call.args[0] for call in interface.appendLog.call_args_list) == 1


def test_on_time_failed_start_is_logged(monkeypatch):
    from app import log_interface
    task = {'id': 'daily', 'name': '每日任务', 'time': '04:00', 'enabled': True}
    monkeypatch.setattr(log_interface.cfg, 'get_value', lambda key, default=None:
                        {'scheduled_tasks': [task], 'scheduled_on_conflict': 'skip'}.get(key, default))
    interface = SimpleNamespace(_pause_state=log_interface.STATE_RUNNING, _last_triggered_ts={},
                                appendLog=Mock(), _updateScheduleStatusLabel=Mock(),
                                isTaskRunning=Mock(return_value=False),
                                _hasActiveStartedProcess=Mock(return_value=False),
                                runScheduledTask=Mock(return_value=False))
    log_interface.LogInterface._checkScheduledTime(interface, date('2026-10-20T04:00:00'))
    assert any('未能启动' in call.args[0] for call in interface.appendLog.call_args_list)


def test_paused_due_task_keeps_checkpoint_until_pending_work_starts(monkeypatch):
    from app import log_interface
    task = {'id': 'daily', 'name': '每日任务', 'time': '04:00', 'enabled': True}
    now = date('2026-10-20T04:00:00')
    clock = [now]
    class Clock:
        @staticmethod
        def currentDateTime():
            return clock[0]
    monkeypatch.setattr(log_interface, 'QDateTime', Clock)
    monkeypatch.setattr(log_interface.cfg, 'get_value', lambda key, default=None:
                        {'scheduled_tasks': [task], 'macos_schedule_catch_up': True}.get(key, default))
    checkpoint = Mock()
    monkeypatch.setattr(log_interface, 'write_checkpoint', checkpoint)
    interface = SimpleNamespace(_pause_state=log_interface.STATE_PAUSED, _last_triggered_ts={},
                                _pending_missed_schedule=None, appendLog=Mock(),
                                _updateScheduleStatusLabel=Mock(), isTaskRunning=Mock(return_value=True),
                                runScheduledTask=Mock(return_value=True), _schedule_running=True,
                                _last_schedule_minute=now.toSecsSinceEpoch() // 60 - 1,
                                _schedule_ignore_until_minute=None, _schedule_timer=Mock())
    interface._isScheduleCatchUpBusy = MethodType(log_interface.LogInterface._isScheduleCatchUpBusy, interface)
    interface._runPendingMissedSchedule = MethodType(log_interface.LogInterface._runPendingMissedSchedule, interface)
    interface._checkScheduledTime = MethodType(log_interface.LogInterface._checkScheduledTime, interface)
    log_interface.LogInterface._onScheduleTimerTimeout(interface)
    assert interface._pending_missed_schedule is not None
    checkpoint.assert_not_called()
    interface._pause_state = log_interface.STATE_RUNNING
    interface.isTaskRunning.return_value = False
    clock[0] = now.addSecs(60)
    log_interface.LogInterface._onScheduleTimerTimeout(interface)
    interface.runScheduledTask.assert_called_once()
    checkpoint.assert_called_once_with(clock[0].toSecsSinceEpoch() // 60)


@pytest.mark.parametrize('previous_offset,expect_check', [(None, True), (0, False)])
def test_first_scheduler_launch_checks_current_minute_but_same_minute_reopen_does_not(monkeypatch, previous_offset, expect_check):
    from app import log_interface
    now = date('2026-10-20T04:00:00')
    minute = now.toSecsSinceEpoch() // 60
    class Clock:
        @staticmethod
        def currentDateTime():
            return now
    callbacks = []
    monkeypatch.setattr(log_interface, 'QDateTime', Clock)
    monkeypatch.setattr(log_interface, 'milliseconds_to_next_minute', lambda value: 1000)
    monkeypatch.setattr(log_interface, 'read_checkpoint', lambda: None if previous_offset is None else minute + previous_offset)
    checkpoint = Mock()
    monkeypatch.setattr(log_interface, 'write_checkpoint', checkpoint)
    monkeypatch.setattr(log_interface.QTimer, 'singleShot', lambda delay, callback: callbacks.append(callback))
    interface = SimpleNamespace(_schedule_timer=Mock(), _schedule_running=False,
                                _recoverSchedulesAtStartup=Mock(), appendLog=Mock())
    log_interface.LogInterface._startScheduleTimer(interface)
    assert bool(callbacks) is expect_check
    if expect_check:
        checkpoint.assert_not_called()
        callbacks[0]()
        interface._recoverSchedulesAtStartup.assert_called_once_with(minute - 1)
    else:
        interface._recoverSchedulesAtStartup.assert_not_called()


def test_checkpoint_write_failure_is_visible_and_does_not_spam(monkeypatch):
    from app import log_interface
    write = Mock(side_effect=[False, False, True, False])
    monkeypatch.setattr(log_interface, 'write_checkpoint', write)
    interface = SimpleNamespace(appendLog=Mock())
    assert not log_interface._write_schedule_checkpoint(interface, 100)
    assert not log_interface._write_schedule_checkpoint(interface, 101)
    assert interface.appendLog.call_count == 1
    assert '状态保存失败' in interface.appendLog.call_args.args[0]
    assert log_interface._write_schedule_checkpoint(interface, 102)
    assert not log_interface._write_schedule_checkpoint(interface, 103)
    assert interface.appendLog.call_count == 2
