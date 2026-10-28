"""Read-only local preview window for screenshot data shared by CLI worker."""
from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from utils.macos_preview import preview_path
from module.localization import tr


class PreviewDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("云游戏画面预览"))
        self.resize(850, 550)
        self._signature = None

        root = QVBoxLayout(self)
        self.status = QLabel(tr("等待自动化任务生成第一张截图…"))
        root.addWidget(self.status)
        self.image_label = QLabel(tr("暂无游戏画面"))
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumSize(450, 260)
        root.addWidget(self.image_label, 1)

        buttons = QHBoxLayout()
        refresh_button = QPushButton(tr("刷新"))
        refresh_button.clicked.connect(lambda: self.refresh(force=True))
        buttons.addStretch(1)
        buttons.addWidget(refresh_button)
        root.addLayout(buttons)

        self.timer = QTimer(self)
        self.timer.setInterval(2500)
        self.timer.timeout.connect(self.refresh)
        self.timer.start()

    def refresh(self, force=False):
        path = preview_path()
        try:
            st = path.stat()
            signature = (st.st_mtime_ns, st.st_size)
            if not force and signature == self._signature:
                return
            with path.open("rb") as src:
                raw = src.read()
            pix = QPixmap()
            if not pix.loadFromData(raw):
                self.status.setText(tr("截图文件尚未准备完成"))
                return
            target = self.image_label.size()
            self.image_label.setPixmap(pix.scaled(
                target, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            ))
            self.status.setText("截图时间：" + datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S"))
            self._signature = signature
        except FileNotFoundError:
            self.status.setText(tr("等待自动化任务生成第一张截图…"))
        except OSError as e:
            self.status.setText(f"读取画面失败：{e}")
