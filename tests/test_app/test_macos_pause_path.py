import os

from app.log_interface import LogInterface


def test_pause_control_is_outside_app_bundle(monkeypatch, tmp_path):
    monkeypatch.setattr('app.log_interface.sys.platform', 'darwin')
    monkeypatch.setenv('MARCH7TH_DATA_DIR', str(tmp_path))
    assert LogInterface._pauseControlPath(None) == os.path.join(str(tmp_path), 'temp', 'pause.json')
