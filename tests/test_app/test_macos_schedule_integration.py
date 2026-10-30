"""Run a real Qt event loop against an isolated persisted scheduler checkpoint."""
from unittest.mock import Mock
from PySide6.QtCore import QDateTime
from app.log_interface import LogInterface
from utils import schedule_state
from module.config import cfg


def test_qt_startup_recovers_missed_task_from_checkpoint(qtbot, monkeypatch, tmp_path):
    monkeypatch.setattr(schedule_state, 'data_dir', lambda: str(tmp_path / 'data'))
    monkeypatch.setattr(schedule_state, 'log_dir', lambda: str(tmp_path / 'logs'))
    now = QDateTime.currentDateTime()
    due = now.addSecs(-5 * 60)
    task = {'id': 'integration-daily', 'name': '测试计划', 'time': due.toString('HH:mm'),
            'program': 'self', 'args': 'daily', 'enabled': True}
    assert schedule_state.write_checkpoint(now.toSecsSinceEpoch() // 60 - 10)
    original = cfg.get_value
    def get_value(key, default=None):
        values = {'scheduled_tasks': [task], 'macos_schedule_catch_up': True,
                  'scheduled_run_enable': False}
        return values[key] if key in values else original(key, default)
    monkeypatch.setattr(cfg, 'get_value', get_value)
    interface = LogInterface()
    qtbot.addWidget(interface)
    run = Mock(return_value=True)
    monkeypatch.setattr(interface, 'runScheduledTask', run)
    qtbot.waitUntil(lambda: run.called, timeout=5000)
    run.assert_called_once_with(task, tasks=[task], manual=False)
    assert schedule_state.read_checkpoint() >= now.toSecsSinceEpoch() // 60
    assert '定时任务延误' in (tmp_path / 'logs' / 'scheduler.log').read_text()
    interface.cleanup()
