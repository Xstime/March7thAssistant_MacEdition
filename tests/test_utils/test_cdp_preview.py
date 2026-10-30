import time
from pathlib import Path
from unittest.mock import Mock

import pytest

from utils import cdp_preview, preview_exchange


def test_capture_rejects_nonlocal_or_malformed_target():
    with pytest.raises(ValueError):
        cdp_preview.capture_frame(9222, '../../external')
    with pytest.raises(ValueError):
        cdp_preview.capture_frame(65536, 'a' * 32)


def test_worker_captures_only_requested_frames_and_stops(monkeypatch, tmp_path):
    monkeypatch.setenv('MARCH7TH_DATA_DIR', str(tmp_path))
    capture = Mock(return_value=b'jpeg')
    monkeypatch.setattr(cdp_preview, 'capture_frame', capture)
    worker = cdp_preview.PreviewWorker(9222, 'a' * 32)
    worker.start()
    try:
        time.sleep(1.2)
        capture.assert_not_called()
        preview_exchange.request_preview()
        deadline = time.monotonic() + 3
        while not Path(preview_exchange.preview_path()).exists() and time.monotonic() < deadline:
            time.sleep(.05)
        assert Path(preview_exchange.preview_path()).read_bytes() == b'jpeg'
        capture.assert_called_once()
    finally:
        worker.stop()
    assert not worker._thread.is_alive()


def test_replaced_request_does_not_accept_an_old_frame(monkeypatch, tmp_path):
    monkeypatch.setenv('MARCH7TH_DATA_DIR', str(tmp_path))
    preview_exchange.request_preview()
    old = preview_exchange.pending_request()
    preview_exchange.request_preview()
    assert preview_exchange.publish_requested_frame(b'old', None, expected_request=old) is None
    assert not Path(preview_exchange.preview_path()).exists()


def test_failed_request_stops_after_three_attempts_and_reports_error(monkeypatch, tmp_path):
    monkeypatch.setenv('MARCH7TH_DATA_DIR', str(tmp_path))
    preview_exchange.request_preview()
    capture = Mock(side_effect=ConnectionError('offline'))
    monkeypatch.setattr(cdp_preview, 'capture_frame', capture)
    worker = cdp_preview.PreviewWorker(9222, 'a' * 32)
    monkeypatch.setattr(worker._stop, 'wait', lambda delay: worker._stop.is_set())
    publish = cdp_preview.publish_preview_error
    def publish_and_stop(request):
        publish(request)
        worker._stop.set()
    monkeypatch.setattr(cdp_preview, 'publish_preview_error', publish_and_stop)
    worker._run()
    assert capture.call_count == 3
    assert preview_exchange.has_preview_error()
    preview_exchange.request_preview()
    assert not preview_exchange.has_preview_error()


def test_frame_is_bound_to_request_even_if_new_request_arrives_during_publish(monkeypatch, tmp_path):
    monkeypatch.setenv('MARCH7TH_DATA_DIR', str(tmp_path))
    old = preview_exchange.request_preview()
    write = preview_exchange._atomic_write
    new = []
    def racing_write(path, content):
        if path == preview_exchange.preview_path() and not new:
            new.append(preview_exchange.request_preview())
        write(path, content)
    monkeypatch.setattr(preview_exchange, '_atomic_write', racing_write)
    preview_exchange.publish_requested_frame(b'old-image', None, expected_request=old)
    assert preview_exchange.read_requested_frame(new[0]) is None
    assert preview_exchange.read_requested_frame(old)[0] == b'old-image'
    preview_exchange.publish_requested_frame(b'new-image', old, expected_request=new[0])
    assert preview_exchange.read_requested_frame(new[0])[0] == b'new-image'
    preview_exchange.clear_preview()
    assert preview_exchange.read_requested_frame(new[0]) is None
