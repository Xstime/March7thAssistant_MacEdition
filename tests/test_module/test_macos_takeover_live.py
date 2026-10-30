"""Opt-in test attaching to an isolated existing Chrome, without an account."""
import os
import socket
import subprocess
import time
from types import SimpleNamespace
from unittest.mock import Mock
from urllib.parse import quote

import pytest
from module.game.cloud import CloudGameController


@pytest.mark.skipif(not (os.environ.get('MARCH7TH_TEST_BROWSER') and os.environ.get('MARCH7TH_TEST_DRIVER')),
                    reason='set MARCH7TH_TEST_BROWSER and MARCH7TH_TEST_DRIVER')
@pytest.mark.parametrize('scenario', ['player', 'no_player', 'broken_driver'])
def test_takeover_attaches_and_cleans_up_existing_browser(tmp_path, scenario):
    browser = os.environ['MARCH7TH_TEST_BROWSER']
    chromedriver = os.environ['MARCH7TH_TEST_DRIVER']
    profile = str(tmp_path / 'profile')
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    html = ('<div class="game-player" style="width:100px;height:100px">local test</div>'
            if scenario != 'no_player' else '<div>no player</div>')
    page = 'data:text/html,' + quote(html)
    proc = subprocess.Popen([browser, '--headless=new', '--remote-debugging-address=127.0.0.1',
                             f'--remote-debugging-port={port}', f'--user-data-dir={profile}',
                             CloudGameController.BROWSER_TAG, '--no-first-run', page],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    controller = object.__new__(CloudGameController)
    controller.cfg = SimpleNamespace(browser_type='chrome', browser_debug_port=port, browser_headless_enable=True)
    controller.user_profile_path = profile
    controller.driver = None
    controller._prepare_browser_and_driver = Mock(return_value=(browser, chromedriver))
    controller._start_preview_worker = Mock()
    controller._stop_preview_worker = Mock()
    controller.log_info = controller.log_warning = controller.log_debug = Mock()
    try:
        deadline = time.monotonic() + 20
        while True:
            try:
                with socket.create_connection(('127.0.0.1', port), timeout=0.2):
                    break
            except OSError:
                if proc.poll() is not None or time.monotonic() >= deadline:
                    raise RuntimeError('isolated browser did not start')
                time.sleep(0.1)
        if scenario != 'no_player':
            controller.attach_existing_game()
            assert controller.driver.find_element('css selector', '.game-player').text == 'local test'
            if scenario == 'broken_driver':
                controller.driver.command_executor = None
                assert controller.stop_game()
                proc.wait(timeout=5)
            else:
                controller._detach_existing_driver()
        else:
            with pytest.raises(RuntimeError, match='没有可接管'):
                controller.attach_existing_game()
        assert controller.driver is None
        if scenario != 'broken_driver':
            assert proc.poll() is None
            with socket.create_connection(('127.0.0.1', port), timeout=2):
                pass
    finally:
        if controller.driver:
            controller._detach_existing_driver()
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
