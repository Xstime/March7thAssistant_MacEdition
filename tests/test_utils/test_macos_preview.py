"""Pure tests of the preview publisher, without WebDriver or Qt."""
from pathlib import Path

import utils.macos_preview as p


def test_publish_rate_limit_and_replace(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(p, "_last_publish", 0.0)
    assert p.publish_preview(b"\xff\xd8\xff", directory=tmp_path, now=30.0)
    image = p.preview_path(tmp_path)
    assert image.read_bytes() == b"\xff\xd8\xff"
    assert not p.publish_preview(b"new", directory=tmp_path, now=40.0)
    assert image.read_bytes() == b"\xff\xd8\xff"
    assert p.publish_preview(b"\x89PNG\r\n", directory=tmp_path, now=46.0)
    assert image.read_bytes() == b"\x89PNG\r\n"


def test_oversized_preview_is_rejected(tmp_path: Path):
    assert not p.publish_preview(b"x" * (10 * 1024 * 1024 + 1), directory=tmp_path)
    assert not p.preview_path(tmp_path).exists()
