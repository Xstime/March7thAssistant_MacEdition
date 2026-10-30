import os
from app.runtime_diagnostics_panel import ProcessSampler, RuntimeDiagnosticsPanel


def test_process_sampler_counts_current_process():
    sampler = ProcessSampler()
    result = sampler.sample(os.getpid())
    assert result['memory'] > 0
    assert result['started'] > 0
    assert result['cpu'] is None
    assert sampler.sample(os.getpid())['cpu'] >= 0


def test_panel_handles_idle_task(qtbot):
    panel = RuntimeDiagnosticsPanel(lambda: None)
    qtbot.addWidget(panel)
    panel.refresh()
    assert panel.status.text() == '任务未运行'


def test_panel_displays_current_task_metrics(qtbot, monkeypatch):
    monkeypatch.setattr('app.runtime_diagnostics_panel.record_sample', lambda sample: None)
    process = type('Process', (), {'processId': lambda self: os.getpid()})()
    panel = RuntimeDiagnosticsPanel(lambda: process)
    qtbot.addWidget(panel)
    panel.refresh()
    assert '内存' in panel.status.text()
    assert '浏览器' in panel.status.text()
    assert '最近识别' in panel.status.text()
