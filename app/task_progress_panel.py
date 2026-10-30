"""Display worker-reported progress without guessing task success."""
import psutil
from module.localization import tr
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from utils.task_progress import read_progress
from utils.pause import STATE_PAUSED, STATE_PAUSING

_PHASE_LABELS = {
    'initializing': '初始化中', 'login': '登录中', 'queue': '排队中',
    'loading': '云游戏加载中', 'recognizing': '识别画面中', 'running': '正在执行任务',
    'waiting': '等待下一次任务',
}


class TaskProgressPanel(QWidget):
    def __init__(self, task_process, parent=None, pause_state=None, external_active=None):
        super().__init__(parent)
        self._task_process = task_process
        self._pause_state = pause_state or (lambda: None)
        self._external_active = external_active or (lambda: False)
        self._pid = 0
        self._started = 0
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.status = QLabel('等待任务', self)
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(1000)

    def refresh(self):
        process = self._task_process()
        pid = int(process.processId()) if process is not None else 0
        if not pid:
            self._pid = 0
            self.status.setText('正在执行其他任务' if self._external_active() else '等待任务')
            return
        if self._pause_state() in (STATE_PAUSED, STATE_PAUSING):
            self.status.setText(tr('任务已暂停'))
            return
        try:
            if self._pid != pid:
                self._started = psutil.Process(pid).create_time()
                self._pid = pid
            event = read_progress(pid, self._started)
            if not event:
                self.status.setText(tr('初始化中'))
                return
            phase = _PHASE_LABELS[event['phase']]
            detail = event.get('detail')
            step, total = event.get('step'), event.get('total')
            prefix = f'阶段 {step}/{total} · ' if (isinstance(step, int) and isinstance(total, int)
                                                   and 0 < step <= total <= 100) else ''
            suffix = f'：{detail}' if isinstance(detail, str) and detail else ''
            self.status.setText(f'{prefix}{phase}{suffix}')
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, OSError):
            self.status.setText(tr('任务状态暂不可用'))
