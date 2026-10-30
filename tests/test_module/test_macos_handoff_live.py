"""A ChromeDriver-owned browser survives control handoff between processes."""
import os
import socket
from types import SimpleNamespace
from unittest.mock import Mock

import psutil
import pytest
from module.game.cloud import CloudGameController


@pytest.mark.skipif(not (os.environ.get('MARCH7TH_TEST_BROWSER') and os.environ.get('MARCH7TH_TEST_DRIVER')),
                    reason='set MARCH7TH_TEST_BROWSER and MARCH7TH_TEST_DRIVER')
def test_owned_chrome_survives_controller_handoff(tmp_path):
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    browser = os.environ['MARCH7TH_TEST_BROWSER']
    driver_path = os.environ['MARCH7TH_TEST_DRIVER']
    profile = str(tmp_path / 'profile')
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    options = Options()
    options.binary_location = browser
    options.add_argument('--headless=new')
    options.add_argument(f'--remote-debugging-port={port}')
    options.add_argument(f'--user-data-dir={profile}')
    options.add_argument(CloudGameController.BROWSER_TAG)
    options.add_experimental_option('detach', True)
    options.ignore_local_proxy_environment_variables()
    first = webdriver.Chrome(service=Service(driver_path), options=options)
    second = None
    controller = object.__new__(CloudGameController)
    controller.driver = first
    controller._stop_preview_worker = Mock()
    controller.log_warning = Mock()
    try:
        first.get('data:text/html,<div id="state">retained</div>')
        controller._detach_existing_driver()
        assert controller.driver is None
        reconnect = Options()
        reconnect.debugger_address = f'127.0.0.1:{port}'
        reconnect.ignore_local_proxy_environment_variables()
        second = webdriver.Chrome(service=Service(driver_path), options=reconnect)
        assert second.find_element('id', 'state').text == 'retained'
    finally:
        if second:
            second.quit()
        for proc in psutil.process_iter(['cmdline']):
            try:
                if f'--user-data-dir={profile}' in (proc.info['cmdline'] or []):
                    proc.terminate()
                    proc.wait(timeout=5)
            except (psutil.Error, OSError):
                pass
