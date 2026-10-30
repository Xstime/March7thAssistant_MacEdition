import os

from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

from app.cloud_login_panel import CloudLoginPanel


def test_qr_panel_tracks_local_image(tmp_path, monkeypatch):
    monkeypatch.setenv("MARCH7TH_LOG_DIR", str(tmp_path))
    app = QApplication.instance() or QApplication([])
    panel = CloudLoginPanel()
    panel.refresh()
    assert panel.isHidden()
    path = tmp_path / "qrcode_login.png"
    image = QImage(16, 16, QImage.Format.Format_RGB32)
    image.fill(0xffffffff)
    assert image.save(str(path))
    panel.refresh()
    assert not panel.isHidden()
    assert not panel.image.pixmap().isNull()
    os.unlink(path)
    panel.refresh()
    assert panel.isHidden()
    assert panel.image.pixmap().isNull()
    panel.timer.stop()
    panel.deleteLater()
    app.processEvents()


def test_panel_tracks_login_stages_and_never_shows_stale_qr(tmp_path, monkeypatch, qtbot):
    from types import SimpleNamespace
    from utils import login_state
    monkeypatch.setenv('MARCH7TH_LOG_DIR', str(tmp_path))
    monkeypatch.setattr(login_state, 'data_dir', lambda: str(tmp_path))
    monkeypatch.setattr(login_state, '_last_state', None)
    monkeypatch.setattr(login_state.sys, 'platform', 'darwin')
    process = SimpleNamespace(pid=os.getpid())
    process.processId = lambda: process.pid
    panel = CloudLoginPanel(task_process=lambda: process)
    qtbot.addWidget(panel)
    path = tmp_path / 'qrcode_login.png'
    image = QImage(16, 16, QImage.Format.Format_RGB32)
    image.fill(0xffffffff)
    assert image.save(str(path))
    # A leftover file alone is not evidence that the current task requested login.
    panel.refresh()
    assert panel.isHidden()
    login_state.set_login_state('waiting_qr')
    panel.refresh()
    assert not panel.isHidden() and panel.image.isHidden()
    assert '生成登录二维码' in panel.message.text()
    login_state.set_login_state('waiting_scan')
    panel.refresh()
    assert not panel.image.isHidden()
    assert '扫码' in panel.message.text()
    login_state.set_login_state('waiting_confirm')
    panel.refresh()
    assert panel.image.isHidden()
    assert '手机上确认' in panel.message.text()
    login_state.set_login_state('verifying')
    panel.refresh()
    assert '验证' in panel.message.text()
    login_state.set_login_state('timed_out')
    process.pid = 0
    panel.refresh()
    assert not panel.isHidden()
    assert '超时' in panel.message.text()
    assert panel.image.isHidden()
