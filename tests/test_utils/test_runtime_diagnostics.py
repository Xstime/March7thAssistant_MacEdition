import json
import os
import time

from utils import runtime_diagnostics as diag


def test_private_events_track_capture_and_recognition_without_text(monkeypatch, tmp_path):
    monkeypatch.setattr(diag, 'data_dir', lambda: str(tmp_path))
    monkeypatch.setattr(diag, '_last_write', {})
    monkeypatch.setattr(diag, '_last_recognition_time', None)
    pid = os.getpid()
    start = time.time() - 1
    diag.record_event('capture')
    diag.record_event('ocr', engine='onnx_cpu', recognized=True)
    capture = diag.read_event(pid, 'capture', start)
    result = diag.read_event(pid, 'ocr', start)
    assert capture['pid'] == pid
    assert result['engine'] == 'onnx_cpu'
    assert start <= result['recognized_at'] <= time.time()
    assert set(result) == {'pid', 'time', 'engine', 'recognized_at'}
    assert os.name == 'nt' or os.stat(diag._path(pid, 'ocr')).st_mode & 0o777 == 0o600
    assert diag.read_event(pid, 'ocr', time.time() + 10) is None
    diag.record_event('ocr', engine='onnx_cpu', recognized=False)
    assert diag.read_event(pid, 'ocr', start)['recognized_at'] == result['recognized_at']


def test_bad_or_partial_event_is_ignored(monkeypatch, tmp_path):
    monkeypatch.setattr(diag, 'data_dir', lambda: str(tmp_path))
    path = diag._path(42, 'capture')
    os.makedirs(os.path.dirname(path))
    with open(path, 'w') as stream:
        stream.write('{')
    assert diag.read_event(42, 'capture', 0) is None


def test_resource_samples_are_private_and_bounded(monkeypatch, tmp_path):
    monkeypatch.setattr(diag, 'log_dir', lambda: str(tmp_path))
    diag.record_sample({'cpu_percent': 4.2, 'memory_bytes': 1024})
    path = tmp_path / 'runtime-diagnostics.jsonl'
    assert json.loads(path.read_text()) == {'cpu_percent': 4.2, 'memory_bytes': 1024}
    assert os.name == 'nt' or path.stat().st_mode & 0o777 == 0o600
    path.write_text('x' * (1024 * 1024))
    diag.record_sample({'cpu_percent': 3.0})
    assert (tmp_path / 'runtime-diagnostics.jsonl.1').exists()
    assert json.loads(path.read_text()) == {'cpu_percent': 3.0}
