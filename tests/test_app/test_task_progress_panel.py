import os
from types import SimpleNamespace
from app.task_progress_panel import TaskProgressPanel
from utils.pause import STATE_PAUSED
from utils import task_progress


def test_worker_stage_and_pause_are_displayed(qtbot, monkeypatch, tmp_path):
    monkeypatch.setattr(task_progress.sys, 'platform', 'darwin')
    monkeypatch.setattr(task_progress, 'data_dir', lambda: str(tmp_path))
    process = SimpleNamespace(processId=lambda: os.getpid())
    state = {'paused': None}
    panel = TaskProgressPanel(lambda: process, pause_state=lambda: state['paused'])
    qtbot.addWidget(panel)
    task_progress.set_major_step(2, 3)
    task_progress.set_phase('running', '清体力')
    panel.refresh()
    assert panel.status.text() == '阶段 2/3 · 正在执行任务：清体力'
    state['paused'] = STATE_PAUSED
    panel.refresh()
    assert panel.status.text() == '任务已暂停'


def test_external_task_is_not_shown_as_idle(qtbot):
    panel = TaskProgressPanel(lambda: None, external_active=lambda: True)
    qtbot.addWidget(panel)
    panel.refresh()
    assert panel.status.text() == '正在执行其他任务'
