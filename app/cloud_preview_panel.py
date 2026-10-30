"""Low-frequency, on-demand display of frames captured by the task process."""
import os
import time
from io import BytesIO
from datetime import datetime
from PIL import Image

from utils.frame_health import FrameHealth

from module.localization import tr
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QCheckBox, QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from utils.preview_exchange import has_preview_error, preview_path, read_requested_frame, request_preview


class CloudPreviewPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._stamp = None
        self._request_started = None
        self._request_id = None
        self._pixmap = QPixmap()
        self._frame_health = FrameHealth()
        layout = QVBoxLayout(self)
        controls = QHBoxLayout()
        controls.addWidget(QLabel("云游戏画面预览", self))
        refresh = QPushButton("刷新画面", self)
        refresh.clicked.connect(self.request)
        controls.addWidget(refresh)
        self.auto = QCheckBox("每 10 秒刷新", self)
        controls.addWidget(self.auto)
        zoom = QPushButton("放大查看", self)
        zoom.clicked.connect(self.show_large)
        controls.addWidget(zoom)
        controls.addStretch()
        layout.addLayout(controls)
        self.status = QLabel("运行云游戏任务后可请求画面。", self)
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.image = QLabel(self)
        self.image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image.setMinimumHeight(160)
        layout.addWidget(self.image)
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.refresh)
        self.poll_timer.start(1000)
        self.auto_timer = QTimer(self)
        self.auto_timer.setInterval(10000)
        self.auto_timer.timeout.connect(self._auto_request)
        self.auto.toggled.connect(self._set_auto)

    def _set_auto(self, enabled):
        if enabled:
            self.request()
            self.auto_timer.start()
        else:
            self.auto_timer.stop()

    def request(self):
        try:
            try:
                self._stamp = os.stat(preview_path()).st_mtime_ns
            except OSError:
                self._stamp = None
            self._request_id = request_preview()
            self._request_started = time.monotonic()
            self.status.setText(tr("正在请求浏览器画面…"))
        except OSError as exc:
            self._request_started = None
            self.status.setText(f"无法请求预览：{exc}")

    def _auto_request(self):
        # Do not replace an in-flight request every ten seconds: the worker has
        # its own bounded retry period and may need longer to report failure.
        if self._request_started is None:
            self.request()

    def _check_request_timeout(self):
        if self._request_started is not None and time.monotonic() - self._request_started >= 30:
            self._request_started = None
            self._request_id = None
            self.status.setText(tr("画面请求超时，请确认云游戏正在运行后重试。"))

    def refresh(self):
        if has_preview_error():
            self._request_started = None
            self._request_id = None
            self.status.setText(tr("画面采集失败，请确认云游戏仍在运行后重试。"))
            return
        if self._request_started is not None:
            response = read_requested_frame(self._request_id)
            if response is None:
                self._check_request_timeout()
                return
            data, stamp = response
            pixmap = QPixmap()
            if not pixmap.loadFromData(data):
                self._check_request_timeout()
                return
            self._request_started = None
            self._request_id = None
            try:
                self._stamp = os.stat(preview_path()).st_mtime_ns
            except OSError:
                self._stamp = None
            self._show_frame(pixmap, stamp, data)
            return
        try:
            stamp = os.stat(preview_path()).st_mtime_ns
        except OSError:
            if self._stamp is not None:
                self._stamp = None
                self._pixmap = QPixmap()
                self._frame_health.reset()
                self.image.clear()
                self.status.setText(tr("没有可用画面。"))
            self._check_request_timeout()
            return
        if stamp == self._stamp:
            self._check_request_timeout()
            return
        pixmap = QPixmap(preview_path())
        if pixmap.isNull():
            self._check_request_timeout()
            return
        self._stamp, self._pixmap = stamp, pixmap
        self._show_frame(pixmap, stamp)

    def _show_frame(self, pixmap, stamp, data=None):
        self._pixmap = pixmap
        self.image.setPixmap(pixmap.scaled(480, 270, Qt.AspectRatioMode.KeepAspectRatio,
                                            Qt.TransformationMode.SmoothTransformation))
        message = "采集时间：" + datetime.fromtimestamp(stamp / 1e9).strftime("%Y-%m-%d %H:%M:%S")
        try:
            with Image.open(BytesIO(data) if data is not None else preview_path()) as frame:
                hints = self._frame_health.observe(frame, stamp / 1e9)
            if hints:
                message += " · " + "；".join(hints)
        except (OSError, ValueError):
            self._frame_health.reset()
        self.status.setText(message)
        self._check_request_timeout()

    def show_large(self):
        if self._pixmap.isNull():
            self.status.setText(tr("暂无可放大的画面。"))
            return
        dialog = QDialog(self)
        dialog.setWindowTitle(tr("云游戏画面"))
        layout = QVBoxLayout(dialog)
        label = QLabel(dialog)
        label.setPixmap(self._pixmap.scaled(1280, 720, Qt.AspectRatioMode.KeepAspectRatio,
                                            Qt.TransformationMode.SmoothTransformation))
        layout.addWidget(label)
        dialog.exec()
