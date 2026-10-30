import os
import time
from utils import task_progress


def test_progress_is_private_and_scoped_to_current_process(monkeypatch, tmp_path):
    monkeypatch.setattr(task_progress.sys, 'platform', 'darwin')
    monkeypatch.setattr(task_progress, 'data_dir', lambda: str(tmp_path))
    task_progress.set_major_step(2, 3)
    started = time.time() - 1
    task_progress.set_phase('running', '清体力')
    event = task_progress.read_progress(os.getpid(), started)
    assert (event['phase'], event['detail'], event['step'], event['total']) == ('running', '清体力', 2, 3)
    assert os.name == 'nt' or os.stat(task_progress.progress_path(os.getpid())).st_mode & 0o777 == 0o600
    assert task_progress.read_progress(os.getpid(), time.time() + 2) is None
    task_progress.set_major_step(0, 0)
    task_progress.set_phase('login', '检查登录')
    assert task_progress.read_progress(os.getpid(), started)['step'] is None


def test_invalid_phase_does_not_write(monkeypatch, tmp_path):
    monkeypatch.setattr(task_progress.sys, 'platform', 'darwin')
    monkeypatch.setattr(task_progress, 'data_dir', lambda: str(tmp_path))
    task_progress.set_phase('not-a-phase', 'ignored')
    assert not os.path.exists(task_progress.progress_path(os.getpid()))
