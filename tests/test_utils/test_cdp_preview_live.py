"""Opt-in test against a locally supplied ARM64 Chrome and chromedriver."""
import os
import socket
import time
from pathlib import Path

import pytest

from utils.cdp_preview import PreviewWorker
from utils.preview_exchange import request_preview, preview_path, read_requested_frame


@pytest.mark.skipif(not (os.environ.get('MARCH7TH_TEST_BROWSER') and os.environ.get('MARCH7TH_TEST_DRIVER')),
                    reason='set MARCH7TH_TEST_BROWSER and MARCH7TH_TEST_DRIVER for live browser test')
def test_preview_updates_without_task_screenshots(monkeypatch, tmp_path):
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    monkeypatch.setenv('MARCH7TH_DATA_DIR', str(tmp_path))
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    opts = Options()
    opts.binary_location = os.environ['MARCH7TH_TEST_BROWSER']
    opts.add_argument('--headless=new')
    opts.add_argument(f'--remote-debugging-port={port}')
    opts.add_argument(f'--user-data-dir={tmp_path / "browser-profile"}')
    opts.ignore_local_proxy_environment_variables()
    driver = webdriver.Chrome(service=Service(os.environ['MARCH7TH_TEST_DRIVER']), options=opts)
    worker = None
    try:
        driver.get('data:text/html,<html><body style="background:red">preview</body></html>')
        errors = []
        worker = PreviewWorker(port, driver.current_window_handle, errors.append)
        worker.start()
        first = request_preview()
        image = Path(preview_path())
        deadline = time.monotonic() + 8
        while read_requested_frame(first) is None and time.monotonic() < deadline:
            time.sleep(.1)
        assert read_requested_frame(first) is not None, errors
        before = read_requested_frame(first)[0]
        driver.execute_script("document.body.style.background='blue'")
        second = request_preview()
        deadline = time.monotonic() + 8
        while read_requested_frame(second) is None and time.monotonic() < deadline:
            time.sleep(.1)
        assert read_requested_frame(second) is not None, errors
        assert read_requested_frame(second)[0] != before, errors
        assert image.read_bytes() == read_requested_frame(second)[0]
    finally:
        if worker:
            worker.stop()
        driver.quit()
