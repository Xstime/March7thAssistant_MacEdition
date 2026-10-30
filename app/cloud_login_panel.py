"""Display only the current task's local QR image and login state."""
import os
import psutil

from module.localization import tr
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from utils.login_state import read_login_state
from utils.runtime_paths import log_dir

_MESSAGES = {
    'checking': '正在检查登录状态…',
    'waiting_qr': '正在生成登录二维码…',
    'waiting_scan': '请使用米游社 App 扫码，并在手机上确认登录。',
    'waiting_confirm': '已扫码，请在手机上确认登录。',
    'verifying': '正在验证登录状态…',
    'success': '登录成功，正在继续启动云游戏。',
    'failed': '登录未完成，请查看日志后重试。',
    'timed_out': '等待登录超时，请重新启动任务。',
}


class CloudLoginPanel(QWidget):
    qrAvailable = Signal()

    def __init__(self, parent=None, task_process=None):
        super().__init__(parent)
        self.path = os.path.join(log_dir(), 'qrcode_login.png')
        self._task_process = task_process
        self._pid = 0
        self._started = 0
        self._state = None
        self._stamp = None
        self.image = QLabel(self)
        self.image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image.setFixedSize(210, 210)
        self.message = QLabel(_MESSAGES['waiting_scan'], self)
        self.message.setWordWrap(True)
        layout = QHBoxLayout(self)
        layout.addWidget(self.image)
        text = QVBoxLayout()
        text.addWidget(QLabel('云游戏登录', self))
        text.addWidget(self.message)
        text.addStretch()
        layout.addLayout(text, 1)
        self.hide()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(1000)

    def _current_state(self):
        if self._task_process is None:
            return None
        process = self._task_process()
        pid = int(process.processId()) if process is not None else 0
        if pid:
            try:
                if pid != self._pid:
                    self._pid, self._started = pid, psutil.Process(pid).create_time()
                    self._state = None
                state = read_login_state(pid, self._started)
                if state:
                    self._state = state
                return self._state
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, OSError):
                return None
        if self._pid:
            terminal = read_login_state(self._pid, self._started)
            if terminal in ('success', 'failed', 'timed_out'):
                self._state = terminal
        # Keep terminal feedback visible after the task exits, but never show an
        # orphaned QR image from an earlier session.
        return self._state if self._state in ('success', 'failed', 'timed_out') else None

    def refresh(self):
        state = self._current_state()
        if self._task_process is not None and state != 'waiting_scan':
            self._stamp = None
            self.image.clear()
            self.image.hide()
            if state:
                self.message.setText(_MESSAGES[state])
                self.show()
            else:
                self.hide()
            return
        try:
            stamp = os.stat(self.path).st_mtime_ns
        except OSError:
            self._stamp = None
            self.image.clear()
            self.image.hide()
            if state == 'waiting_scan':
                self.message.setText(tr('等待二维码显示…'))
                self.show()
            else:
                self.hide()
            return
        if stamp == self._stamp:
            return
        pixmap = QPixmap(self.path)
        if pixmap.isNull():
            return
        first_image = self._stamp is None
        self._stamp = stamp
        self.message.setText(_MESSAGES['waiting_scan'])
        self.image.setPixmap(pixmap.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio,
                                           Qt.TransformationMode.FastTransformation))
        self.image.show()
        self.show()
        if first_image:
            self.qrAvailable.emit()
