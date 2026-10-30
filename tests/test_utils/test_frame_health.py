from PIL import Image
from utils.frame_health import FrameHealth


def test_dark_preview_requires_repeated_observations_and_is_a_hint():
    monitor = FrameHealth()
    image = Image.new('RGB', (200, 120), (0, 0, 0))
    assert monitor.observe(image, 0) == []
    assert monitor.observe(image, 10) == []
    assert monitor.observe(image, 20) == ['预览持续较暗，加载过程中也可能出现']
    assert monitor.observe(Image.new('RGB', (200, 120), 'white'), 30) == []


def test_static_preview_requires_contiguous_samples_and_resets_on_change():
    monitor = FrameHealth()
    image = Image.new('RGB', (200, 120), (90, 120, 150))
    for instant in (0, 20, 40):
        assert monitor.observe(image, instant) == []
    assert monitor.observe(image, 60) == ['预览长时间未变化，静止界面也可能如此']
    assert monitor.observe(Image.new('RGB', (200, 120), 'white'), 70) == []


def test_sparse_or_out_of_order_samples_do_not_imply_a_frozen_video():
    monitor = FrameHealth()
    image = Image.new('RGB', (64, 64), 'white')
    for instant in (0, 31, 62, 93, 10):
        assert monitor.observe(image, instant) == []
