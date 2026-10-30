import os
import time
from PIL import Image
from app.cloud_preview_panel import CloudPreviewPanel


def test_preview_reports_persistent_darkness_without_declaring_failure(qtbot, monkeypatch, tmp_path):
    path = tmp_path / 'preview.png'
    monkeypatch.setattr('app.cloud_preview_panel.preview_path', lambda: str(path))
    monkeypatch.setattr('app.cloud_preview_panel.has_preview_error', lambda: False)
    panel = CloudPreviewPanel()
    qtbot.addWidget(panel)
    image = Image.new('RGB', (160, 90), 'black')
    start = time.time() - 20
    for index in range(3):
        image.save(path)
        stamp = int((start + index * 10) * 1_000_000_000)
        os.utime(path, ns=(stamp, stamp))
        panel.refresh()
    assert '预览持续较暗' in panel.status.text()
    assert '加载过程中也可能出现' in panel.status.text()
    image = Image.new('RGB', (160, 90), 'white')
    image.save(path)
    stamp += 10_000_000_000
    os.utime(path, ns=(stamp, stamp))
    panel.refresh()
    assert '预览持续较暗' not in panel.status.text()


def test_preview_times_out_without_worker_and_auto_does_not_replace_request(qtbot, monkeypatch, tmp_path):
    from types import SimpleNamespace
    from unittest.mock import Mock
    from app import cloud_preview_panel as preview
    clock = [100.0]
    monkeypatch.setattr(preview, 'time', SimpleNamespace(monotonic=lambda: clock[0]))
    monkeypatch.setattr(preview, 'preview_path', lambda: str(tmp_path / 'missing'))
    monkeypatch.setattr(preview, 'has_preview_error', lambda: False)
    request = Mock()
    monkeypatch.setattr(preview, 'request_preview', request)
    panel = CloudPreviewPanel()
    qtbot.addWidget(panel)
    panel.request()
    clock[0] += 10
    panel._auto_request()
    request.assert_called_once()
    panel.refresh()
    assert '正在请求' in panel.status.text()
    clock[0] += 20
    panel.refresh()
    assert '超时' in panel.status.text()
    panel._auto_request()
    assert request.call_count == 2


def test_existing_frame_is_not_mistaken_for_new_response(qtbot, monkeypatch, tmp_path):
    from types import SimpleNamespace
    from unittest.mock import Mock
    from PIL import Image
    from app import cloud_preview_panel as preview
    clock = [100.0]
    path = tmp_path / 'preview.png'
    Image.new('RGB', (10, 10), 'red').save(path)
    monkeypatch.setattr(preview, 'time', SimpleNamespace(monotonic=lambda: clock[0]))
    monkeypatch.setattr(preview, 'preview_path', lambda: str(path))
    monkeypatch.setattr(preview, 'has_preview_error', lambda: False)
    monkeypatch.setattr(preview, 'request_preview', Mock())
    panel = CloudPreviewPanel()
    qtbot.addWidget(panel)
    panel.request()
    panel.refresh()
    assert '正在请求' in panel.status.text()
    assert panel._request_started is not None
    clock[0] += 30
    panel.refresh()
    assert '超时' in panel.status.text()


def test_preview_response_clears_pending_request(qtbot, monkeypatch, tmp_path):
    from types import SimpleNamespace
    from unittest.mock import Mock
    from PIL import Image
    from app import cloud_preview_panel as preview
    clock = [100.0]
    path = tmp_path / 'preview.png'
    monkeypatch.setattr(preview, 'time', SimpleNamespace(monotonic=lambda: clock[0]))
    monkeypatch.setattr(preview, 'preview_path', lambda: str(path))
    monkeypatch.setattr(preview, 'has_preview_error', lambda: False)
    monkeypatch.setattr(preview, 'request_preview', Mock())
    panel = CloudPreviewPanel()
    qtbot.addWidget(panel)
    panel.request()
    Image.new('RGB', (10, 10), 'green').save(path)
    monkeypatch.setattr(preview, 'read_requested_frame', lambda request: (path.read_bytes(), path.stat().st_mtime_ns))
    panel.refresh()
    assert panel._request_started is None
    assert '采集时间' in panel.status.text()
