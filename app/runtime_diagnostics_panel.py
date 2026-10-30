"""Low-frequency, read-only diagnostics for the current owned task tree."""
from datetime import datetime
import time

import psutil
from module.localization import tr
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from utils.runtime_diagnostics import read_event, record_sample


def _clock(value):
    if not isinstance(value, (float, int)):
        return '暂无'
    try:
        return datetime.fromtimestamp(value).strftime('%H:%M:%S')
    except (OverflowError, OSError, ValueError):
        return '暂无'


class ProcessSampler:
    def __init__(self):
        self._previous = {}

    def sample(self, pid):
        root = psutil.Process(pid)
        started = root.create_time()
        try:
            children = root.children(recursive=True)
            browser = False
        except (psutil.AccessDenied, PermissionError):
            children = []
            browser = None
        processes = [root] + children
        now = time.monotonic()
        new = {}
        cpu = 0.0
        measured = False
        memory = 0
        for process in processes:
            try:
                with process.oneshot():
                    key = (process.pid, process.create_time())
                    times = process.cpu_times()
                    total = times.user + times.system
                    memory += process.memory_info().rss
                    name = process.name().lower()
                    if browser is not None:
                        browser |= any(token in name for token in ('chrome', 'chromium', 'microsoft edge')) and 'driver' not in name
                old = self._previous.get(key)
                if old and now > old[0]:
                    cpu += max(0.0, total - old[1]) / (now - old[0]) * 100
                    measured = True
                new[key] = (now, total)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        self._previous = new
        return {'started': started, 'cpu': cpu if measured else None, 'memory': memory, 'browser': browser,
                'tree_available': browser is not None}


class RuntimeDiagnosticsPanel(QWidget):
    def __init__(self, task_process, parent=None):
        super().__init__(parent)
        self._task_process = task_process
        self._sampler = ProcessSampler()
        self._last_record = 0.0
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel('运行诊断', self))
        self.status = QLabel('任务未运行', self)
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(5000)

    def refresh(self):
        process = self._task_process()
        pid = int(process.processId()) if process is not None else 0
        if not pid:
            self._sampler = ProcessSampler()
            self.status.setText(tr('任务未运行'))
            return
        try:
            sample = self._sampler.sample(pid)
            capture = read_event(pid, 'capture', sample['started']) or {}
            ocr = read_event(pid, 'ocr', sample['started']) or {}
            duration = max(0, int(time.time() - sample['started']))
            browser_status = ('状态不可用' if sample['browser'] is None else
                              '运行中' if sample['browser'] else '未检测到')
            scope = '任务及子进程' if sample['tree_available'] else '仅任务进程'
            cpu = f"{sample['cpu']:.1f}%" if sample['cpu'] is not None else '测量中'
            self.status.setText(
                f"{scope} CPU {cpu} · 内存 {sample['memory'] / 1048576:.0f} MiB · "
                f"浏览器{browser_status} · "
                f"运行 {duration // 60:02d}:{duration % 60:02d}\n"
                f"OCR {ocr.get('engine', '尚未初始化')} · 最近画面 {_clock(capture.get('time'))} · "
                f"最近识别 {_clock(ocr.get('recognized_at'))}"
            )
            if time.monotonic() - self._last_record >= 60:
                record_sample({'time': time.time(), 'cpu_percent': sample['cpu'],
                               'memory_bytes': sample['memory'], 'tree_available': sample['tree_available'],
                               'browser_running': sample['browser'], 'ocr_engine': ocr.get('engine'),
                               'last_capture': capture.get('time'), 'last_recognition': ocr.get('recognized_at'),
                               'duration_seconds': duration})
                self._last_record = time.monotonic()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, OSError):
            self.status.setText(tr('任务状态暂不可用'))
