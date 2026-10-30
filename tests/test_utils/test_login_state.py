import os
import time
from utils import login_state


def test_login_state_is_private_and_scoped_to_worker(monkeypatch, tmp_path):
    monkeypatch.setattr(login_state.sys, 'platform', 'darwin')
    monkeypatch.setattr(login_state, 'data_dir', lambda: str(tmp_path))
    monkeypatch.setattr(login_state, '_last_state', None)
    started = time.time() - 1
    login_state.set_login_state('waiting_scan')
    path = login_state.state_path(os.getpid())
    assert os.stat(path).st_mode & 0o777 == 0o600
    assert login_state.read_login_state(os.getpid(), started) == 'waiting_scan'
    assert login_state.read_login_state(os.getpid(), time.time() + 1) is None
    assert login_state.read_login_state(os.getpid() + 1, started) is None
    login_state.set_login_state('waiting_confirm')
    assert login_state.read_login_state(os.getpid(), started) == 'waiting_confirm'
    text = open(path, encoding='utf8').read()
    assert set(__import__('json').loads(text)) == {'pid', 'time', 'state'}
