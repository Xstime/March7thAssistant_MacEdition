from types import SimpleNamespace
from unittest.mock import Mock
from app.log_interface import LogInterface
from app.main_window import MainWindow


def test_macos_task_status_distinguishes_failure_and_user_stop(monkeypatch):
    import app.log_interface as log_interface
    monkeypatch.setattr(log_interface.sys, 'platform', 'darwin')
    target = SimpleNamespace(stopButton=Mock(), pauseButton=Mock(), statusLabel=Mock(),
                             _pending_post_action_timer=None)
    LogInterface._updateFinishedStatus(target, 1)
    assert target.statusLabel.setText.call_args.args[0] == '任务失败，请查看日志'
    LogInterface._updateFinishedStatus(target, 1, user_stopped=True)
    assert target.statusLabel.setText.call_args.args[0] == '任务已停止'
    LogInterface._updateFinishedStatus(target, 0)
    assert '请查看日志' in target.statusLabel.setText.call_args.args[0]


def test_user_stop_notification_is_not_failure(monkeypatch):
    import app.main_window as main_window
    monkeypatch.setattr(main_window.sys, 'platform', 'darwin')
    target = SimpleNamespace(logInterface=SimpleNamespace(last_task_user_stopped=True),
                             _macNotify=Mock(), exit_on_complete=False, startup_task=None)
    MainWindow._onTaskFinished(target, 1)
    assert target._macNotify.call_args.args[:2] == ('finish', '任务已停止')
