"""Opt-in local browser test of QR UI transitions; no account or network required."""
import base64
import html
import os
import time
from io import BytesIO
from urllib.parse import quote
from unittest.mock import Mock

import pytest
from PIL import Image
from module.game.cloud import CloudGameController


@pytest.mark.skipif(not (os.environ.get('MARCH7TH_TEST_BROWSER') and os.environ.get('MARCH7TH_TEST_DRIVER')),
                    reason='set MARCH7TH_TEST_BROWSER and MARCH7TH_TEST_DRIVER for live browser test')
def test_local_qr_flow_displays_then_clears_image(monkeypatch, tmp_path):
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    import module.game.cloud as cloud_module
    monkeypatch.setenv('MARCH7TH_DATA_DIR', str(tmp_path / 'data'))
    monkeypatch.setenv('MARCH7TH_LOG_DIR', str(tmp_path / 'logs'))
    options = Options()
    options.binary_location = os.environ['MARCH7TH_TEST_BROWSER']
    options.add_argument('--headless=new')
    options.add_argument(f'--user-data-dir={tmp_path / "profile"}')
    options.ignore_local_proxy_environment_variables()
    driver = webdriver.Chrome(service=Service(os.environ['MARCH7TH_TEST_DRIVER']), options=options)
    try:
        buffer = BytesIO()
        Image.new('RGB', (80, 80), 'black').save(buffer, format='PNG')
        image = base64.b64encode(buffer.getvalue()).decode('ascii')
        inner = f'''<div class="qr-login-btn" style="width:20px;height:20px">二维码</div>
            <img class="qr-loaded" src="data:image/png;base64,{image}">
            <div id="scan" style="display:none">扫码成功</div>
            <script>setTimeout(()=>document.getElementById('scan').style.display='block', 5000)</script>'''
        page = '<iframe id="mihoyo-login-platform-iframe" srcdoc="' + html.escape(inner, quote=True) + '"></iframe>'
        driver.get('data:text/html;charset=utf-8,' + quote(page))
        controller = object.__new__(CloudGameController)
        controller.driver = driver
        controller.logger = Mock()
        seen = []
        qr_path = tmp_path / 'logs' / 'qrcode_login.png'
        def record(state):
            seen.append(state)
            if state == 'waiting_scan':
                assert qr_path.exists()
                assert qr_path.stat().st_mode & 0o777 == 0o600
        monkeypatch.setattr(cloud_module, 'set_login_state', record)
        assert controller._run_qr_login_flow(time.monotonic() + 30, 30) is True
        assert seen == ['waiting_qr', 'waiting_scan', 'waiting_confirm']
        assert not qr_path.exists()
    finally:
        driver.quit()
