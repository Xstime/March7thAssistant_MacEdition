"""Offline smoke test of the packaged ARM64 OCR runtime and bundled models."""
import json
import platform
import time
import tempfile
import os
import subprocess

from PIL import Image, ImageDraw, ImageFont


def run_browser_manager():
    """Check the bundled Selenium Manager without accessing the network."""
    from selenium.webdriver.common.selenium_manager import SeleniumManager
    from utils.macos_browser import ARM64, macho_architectures

    override = os.environ.pop('SE_MANAGER_PATH', None)
    try:
        manager = SeleniumManager._get_binary()
        arm64 = ARM64 in macho_architectures(manager)
        result = subprocess.run([str(manager), '--version'], capture_output=True, text=True, timeout=10)
        passed = arm64 and result.returncode == 0 and bool(result.stdout.strip())
        print(json.dumps({'passed': passed, 'arm64': arm64,
                          'version': result.stdout.strip(),
                          'scope': 'bundled manager executable; no browser download'}, ensure_ascii=False))
        return 0 if passed else 1
    finally:
        if override is not None:
            os.environ['SE_MANAGER_PATH'] = override


def run_browser_install():
    """Exercise the actual integrated-browser setup in the selected data directory."""
    from module.game import cloud_game
    from utils.macos_browser import validate_browser_pair

    try:
        browser, driver = cloud_game._prepare_browser_and_driver('chrome', integrated=True)
        validate_browser_pair(browser, driver)
        print(json.dumps({'passed': True, 'architecture': platform.machine(),
                          'browser_present': os.path.isfile(browser),
                          'driver_present': os.path.isfile(driver)}, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({'passed': False, 'error_type': type(exc).__name__}, ensure_ascii=False))
        return 1


def run(engine='onnx_cpu'):
    from module.ocr import ocr

    image = Image.new('RGB', (700, 180), 'white')
    font = ImageFont.truetype('/System/Library/Fonts/STHeiti Medium.ttc', 48)
    ImageDraw.Draw(image).text((30, 40), '每日实训 领取奖励', font=font, fill='black')
    start = time.monotonic()
    ocr._get_selected_mode = lambda: engine
    ocr.instance_ocr()
    init_seconds = time.monotonic() - start
    try:
        start = time.monotonic()
        result = ocr.recognize_multi_lines(image)
        elapsed = time.monotonic() - start
        texts = [item[1][0] for item in result] if result else []
        matching = [item for item in (result or []) if '每日实训' in item[1][0]]
        boxes_valid = bool(matching) and all(
            all(0 <= point[0] < image.width and 0 <= point[1] < image.height for point in item[0])
            and 10 <= min(point[0] for point in item[0]) <= 70
            and 20 <= min(point[1] for point in item[0]) <= 90
            for item in matching
        )
        passed = ocr._resolved_mode == engine and boxes_valid
        print(json.dumps({'passed': passed, 'architecture': platform.machine(),
                          'engine': ocr._resolved_mode, 'text': texts,
                          'coordinates_valid': boxes_valid,
                          'initialization_seconds': round(init_seconds, 3),
                          'recognition_seconds': round(elapsed, 3)}, ensure_ascii=False))
        return 0 if passed else 1
    finally:
        ocr.exit_ocr()


def run_frame_health():
    from PIL import Image
    from utils.frame_health import FrameHealth

    monitor = FrameHealth()
    frame = Image.new('RGB', (96, 54), 'black')
    hints = []
    for instant in (0, 10, 20):
        hints = monitor.observe(frame, instant)
    passed = bool(hints and '预览持续较暗' in hints[0])
    print(json.dumps({'passed': passed, 'dark_preview_hint': passed}, ensure_ascii=False))
    return 0 if passed else 1


def run_browser():
    import logging
    from types import SimpleNamespace
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from module.game import cloud_game
    from utils.cdp_preview import capture_frame
    from module.automation.cdp_input import CdpInput
    from utils.runtime_paths import data_dir, private_dir

    browser, driver = cloud_game._prepare_browser_and_driver('chrome', True)
    with tempfile.TemporaryDirectory(prefix='browser-selftest-', dir=private_dir(data_dir())) as profile:
        options = Options()
        options.ignore_local_proxy_environment_variables()
        options.binary_location = browser
        options.add_argument('--headless=new')
        options.add_argument(f'--user-data-dir={profile}')
        options.add_argument('--window-size=800,600')
        session = webdriver.Chrome(service=Service(driver), options=options)
        try:
            session.get('data:text/html,<html><body style="background:red">test</body></html>')
            session.execute_script('''window.__m7_events=[];
                document.addEventListener('click', e=>window.__m7_events.push(['click', e.clientX, e.clientY]));
                document.addEventListener('keydown', e=>window.__m7_events.push(['keydown', e.key]));''')
            cdp_input = CdpInput(SimpleNamespace(execute_cdp_cmd=session.execute_cdp_cmd,
                                                  _actual_headless=True),
                                 logging.getLogger('macos-selftest'))
            cdp_input.mouse_move(100, 100)
            cdp_input.press_mouse(wait_time=0)
            cdp_input.press_key('a', wait_time=0)
            events = session.execute_script('return window.__m7_events')
            input_ok = ['click', 100, 100] in events and ['keydown', 'a'] in events
            before = session.get_screenshot_as_png()
            address = session.capabilities['goog:chromeOptions']['debuggerAddress']
            port = int(address.rsplit(':', 1)[1])
            preview_before = capture_frame(port, session.current_window_handle)
            session.execute_script("document.body.style.background='blue'")
            after = session.get_screenshot_as_png()
            preview_after = capture_frame(port, session.current_window_handle)
            passed = (input_ok and before.startswith(b'\x89PNG\r\n\x1a\n') and before != after and
                      preview_before.startswith(b'\xff\xd8\xff') and preview_before != preview_after)
            print(json.dumps({'passed': passed, 'browser_version': session.capabilities.get('browserVersion'),
                              'architecture': platform.machine(), 'screenshots_changed': before != after,
                              'independent_preview_changed': preview_before != preview_after,
                              'cdp_input': input_ok}))
            return 0 if passed else 1
        finally:
            session.quit()
