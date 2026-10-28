"""Private, local QR login monitor for native macOS GUI.

The existing cloud-game implementation writes a local QR image while waiting
for mobile verification. Present that exact image in Qt without transmitting
it to a web service. This component cannot read browser cookies or tokens.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from utils.macos_paths import logs_dir
from module.localization import tr


class QRLoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("云·星穹铁道 - 扫码登录"))
        self.setMinimumWidth(330)
        self.setModal(False)
        layout = QVBoxLayout(self)
        caption = QLabel(tr("请使用手机扫码并确认登录，二维码过期后会自动刷新。"))
        caption.setWordWrap(True)
        layout.addWidget(caption)
        self.picture = QLabel(tr("正在生成二维码…"))
        self.picture.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.picture.setMinimumSize(290, 290)
        layout.addWidget(self.picture)
        buttons = QHBoxLayout()
        close = QPushButton(tr("关闭"))
        close.clicked.connect(self.hide)
        buttons.addStretch(1)
        buttons.addWidget(close)
        layout.addLayout(buttons)

    def set_image(self, filename: Path) -> bool:
        image = QPixmap(str(filename))
        if image.isNull():
            self.picture.setText(tr("二维码暂时不可用，稍后自动重试。"))
            return False
        self.picture.setPixmap(image.scaled(
            290, 290,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        ))
        return True


class QRLoginMonitor(QObject):
    """Show each new login QR once, while respecting manual dismissals."""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent_window = parent
        self.path = logs_dir() / "qrcode_login.png"
        self.dialog = QRLoginDialog(parent)
        self._last_signature = None
        self._last_displayed_signature = None
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._check)
        self.timer.start()

    def _check(self):
        try:
            st = self.path.stat()
            signature = (st.st_mtime_ns, st.st_size)
        except FileNotFoundError:
            if self._last_signature is not None:
                self.dialog.hide()
            self._last_signature = None
            self._last_displayed_signature = None
            return
        except OSError:
            return

        if signature == self._last_signature:
            return
        self._last_signature = signature
        if not self.dialog.set_image(self.path):
            return
        if signature != self._last_displayed_signature:
            self._last_displayed_signature = signature
            self.dialog.show()
            self.dialog.raise_()
