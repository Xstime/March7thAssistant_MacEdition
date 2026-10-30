from pathlib import Path

from utils import preview_exchange as preview


def test_only_requested_frames_are_published_and_cleared(tmp_path, monkeypatch):
    monkeypatch.setenv('MARCH7TH_DATA_DIR', str(tmp_path))
    assert preview.publish_requested_frame(b'first', None) is None
    preview.request_preview()
    token = preview.publish_requested_frame(b'first', None)
    image = Path(preview.preview_path())
    assert image.read_bytes() == b'first'
    assert image.stat().st_mode & 0o077 == 0
    assert preview.publish_requested_frame(b'second', token) == token
    assert image.read_bytes() == b'first'
    preview.request_preview()
    assert preview.publish_requested_frame(b'second', token) != token
    assert image.read_bytes() == b'second'
    preview.clear_preview()
    assert not image.exists()
