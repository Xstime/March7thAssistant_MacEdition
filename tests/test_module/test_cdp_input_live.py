"""Opt-in macOS browser test for CDP input and screenshot coordinates."""
import os
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import Mock
from urllib.parse import quote

import pytest
from PIL import Image
from module.automation.cdp_input import CdpInput
from module.game.cloud import CloudGameController
from module.automation.automation import Automation
from module.automation.screenshot import Screenshot


@pytest.mark.skipif(not (os.environ.get('MARCH7TH_TEST_BROWSER') and os.environ.get('MARCH7TH_TEST_DRIVER')),
                    reason='set MARCH7TH_TEST_BROWSER and MARCH7TH_TEST_DRIVER for live browser test')
@pytest.mark.parametrize('headless', [True, False])
def test_scaled_visible_canvas_preserves_screenshot_and_click_coordinates(tmp_path, headless):
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    options = Options()
    options.binary_location = os.environ['MARCH7TH_TEST_BROWSER']
    if headless:
        options.add_argument('--headless=new')
    options.add_argument(f'--user-data-dir={tmp_path / "profile"}')
    options.ignore_local_proxy_environment_variables()
    driver = webdriver.Chrome(service=Service(os.environ['MARCH7TH_TEST_DRIVER']), options=options)
    try:
        driver.get('data:text/html,' + quote('''<style>body{margin:0;background:white}
            button{position:absolute;left:1700px;top:900px;width:100px;height:60px;background:red}
            </style><button id="target" onclick="document.title='clicked'"></button>'''))
        controller = object.__new__(CloudGameController)
        controller.driver = driver
        controller._actual_headless = False
        controller.cfg = SimpleNamespace(cloud_game_fullscreen_enable=False)
        controller._confirm_viewport_resolution()
        assert 0 < controller._viewport_scale < 1
        image = Image.open(BytesIO(driver.get_screenshot_as_png())).convert('RGB')
        assert image.size == (1920, 1080)
        assert image.getpixel((1750, 930))[0] > 200
        assert image.getpixel((1750, 930))[1] < 100
        CdpInput(controller, Mock()).mouse_click(1750, 930)
        assert driver.title == 'clicked'
    finally:
        driver.quit()


@pytest.mark.skipif(not (os.environ.get('MARCH7TH_TEST_BROWSER') and os.environ.get('MARCH7TH_TEST_DRIVER')),
                    reason='set MARCH7TH_TEST_BROWSER and MARCH7TH_TEST_DRIVER for live browser test')
@pytest.mark.parametrize('scale', [0.5, 1.0, 1.5, 2.0])
def test_headless_click_keyboard_and_screenshot_share_coordinates(tmp_path, monkeypatch, scale):
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    options = Options()
    options.binary_location = os.environ['MARCH7TH_TEST_BROWSER']
    options.add_argument('--headless=new')
    options.add_argument(f'--force-device-scale-factor={scale}')
    options.add_argument(f'--user-data-dir={tmp_path / "profile"}')
    options.ignore_local_proxy_environment_variables()
    driver = webdriver.Chrome(service=Service(os.environ['MARCH7TH_TEST_DRIVER']), options=options)
    try:
        driver.execute_cdp_cmd('Emulation.setDeviceMetricsOverride', {
            'width': 1920, 'height': 1080, 'deviceScaleFactor': 1, 'mobile': False})
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': CloudGameController.DISABLE_POINTER_LOCK_SCRIPT, 'runImmediately': True})
        html = '''<html><style>body{margin:0;background:white}#target{position:absolute;
            left:400px;top:200px;width:100px;height:60px;background:rgb(255,0,0)}</style>
            <button id="target"></button><input id="text" style="position:absolute;left:400px;top:300px">
            <script>window.events=[];
            for (const type of ['mousedown','mousemove','mouseup','click','keydown','keyup'])
                document.addEventListener(type,e=>window.events.push({type:e.type,buttons:e.buttons,
                    x:e.clientX,y:e.clientY,key:e.key,code:e.code,target:e.target.id}));</script></html>'''
        driver.get('data:text/html;charset=utf-8,' + quote(html))
        pointer_lock = driver.execute_async_script('''const done=arguments[0];
            document.getElementById('target').requestPointerLock()
                .then(()=>done('allowed')).catch(e=>done(e.name));''')
        assert pointer_lock == 'NotAllowedError'
        assert driver.execute_script('return document.pointerLockElement === null')
        image = Image.open(BytesIO(driver.get_screenshot_as_png())).convert('RGB')
        assert image.size == (1920, 1080)
        assert image.getpixel((450, 230))[0] > 200
        input_handler = CdpInput(SimpleNamespace(execute_cdp_cmd=driver.execute_cdp_cmd,
                                                  _actual_headless=True), Mock())
        input_handler.press_key('b', wait_time=0)
        assert any(event['type'] == 'keydown' and event['key'] == 'b'
                   for event in driver.execute_script('return window.events'))
        import module.game as game_module
        import module.automation.screenshot as screenshot_module
        import numpy as np
        monkeypatch.setattr(screenshot_module, 'cfg', SimpleNamespace(cloud_game_enable=True))
        controller = object.__new__(CloudGameController)
        controller.driver = driver
        controller.cfg = SimpleNamespace(cloud_game_use_paid_time=False, browser_headless_enable=True)
        controller.logger = Mock()
        monkeypatch.setattr(game_module, 'cloud_game', controller)
        cropped, crop_position, factor = Screenshot.take_screenshot('unused', crop=(0.125, 0.1, 0.5, 0.5))
        assert crop_position == (240, 108, 960, 540)
        assert cropped.convert('RGB').getpixel((210, 122))[0] > 200
        automation = object.__new__(Automation)
        automation.screenshot_pos = crop_position
        automation.screenshot_scale_factor = factor
        automation.mouse_click = input_handler.mouse_click
        bounds = automation.calculate_positions(np.zeros((60, 100)), (160, 92), relative=False)
        assert bounds == ((400, 200), (500, 260))
        assert automation.click_element_with_pos(bounds)
        input_handler.press_key('a', wait_time=0)
        events = driver.execute_script('return window.events')
        click = next(event for event in events if event['type'] == 'click')
        release = next(event for event in events if event['type'] == 'mouseup')
        assert (click['target'], click['x'], click['y']) == ('target', 450, 230)
        assert release['buttons'] == 0
        assert any(event['type'] == 'keydown' and event['code'] == 'KeyA' and event['key'] == 'a' for event in events)
        assert any(event['type'] == 'keyup' and event['code'] == 'KeyA' for event in events)
        input_handler.press_key_down('shift')
        input_handler.press_key('a', wait_time=0)
        input_handler.press_key_up('shift')
        shifted = driver.execute_script('return window.events')
        assert any(event['type'] == 'keydown' and event['code'] == 'KeyA' and event['key'] == 'A' for event in shifted)
        input_handler.mouse_down(450, 230)
        input_handler.mouse_move(460, 240)
        input_handler.mouse_up()
        dragged = driver.execute_script('return window.events')
        assert any(event['type'] == 'mousemove' and event['buttons'] == 1 and event['x'] == 460 for event in dragged)
        input_handler.mouse_move(450, 310)
        input_handler.press_mouse(wait_time=0)
        input_handler.secretly_write('Ab3-中文', interval=0)
        assert driver.execute_script('return document.getElementById("text").value') == 'Ab3-中文'
    finally:
        driver.quit()
