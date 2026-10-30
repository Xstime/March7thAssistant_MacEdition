"""Capture requested previews through an independent loopback CDP session."""
import base64
import json
import re
import threading
import time

import websocket

from utils.preview_exchange import pending_request, publish_preview_error, publish_requested_frame


def capture_frame(port, target_id, timeout=4):
    port = int(port)
    if not 1 <= port <= 65535 or not re.fullmatch(r'[a-fA-F0-9]{32}', target_id):
        raise ValueError('invalid local browser target')
    # A target ID from our own WebDriver session, never a URL supplied by a page.
    address = f'ws://127.0.0.1:{port}/devtools/page/{target_id}'
    connection = websocket.create_connection(address, timeout=timeout, suppress_origin=True,
                                              http_no_proxy=['127.0.0.1', 'localhost'])
    try:
        deadline = time.monotonic() + timeout
        connection.send(json.dumps({'id': 1, 'method': 'Page.captureScreenshot',
                                    'params': {'format': 'jpeg', 'quality': 80}}))
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('browser preview timed out')
            connection.settimeout(remaining)
            message = json.loads(connection.recv())
            if message.get('id') != 1:
                continue
            if 'error' in message:
                raise RuntimeError('browser could not capture the preview')
            return base64.b64decode(message['result']['data'], validate=True)
    finally:
        connection.close()


class PreviewWorker:
    def __init__(self, port, target_id, on_error=None):
        self.port = port
        self.target_id = target_id
        self._on_error = on_error
        self._stop = threading.Event()
        self._publish_lock = threading.Lock()
        self._thread = threading.Thread(target=self._run, name='cloud-preview', daemon=True)

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop.set()
        with self._publish_lock:
            pass
        self._thread.join(timeout=1)

    def _run(self):
        previous = None
        attempted_request = None
        attempts = 0
        while not self._stop.wait(1):
            request = None
            try:
                request = pending_request()
                if not request or request == previous:
                    continue
                if request != attempted_request:
                    attempted_request, attempts = request, 0
                if attempts >= 3:
                    continue
                frame = capture_frame(self.port, self.target_id)
                with self._publish_lock:
                    if not self._stop.is_set():
                        previous = publish_requested_frame(frame, previous, expected_request=request)
                        from utils.runtime_diagnostics import record_event
                        record_event('capture')
            except Exception as exc:
                # Each request gets at most three attempts, with bounded backoff.
                attempts += 1
                if self._on_error:
                    self._on_error(f'画面预览暂不可用: {type(exc).__name__}')
                if attempts >= 3 and request:
                    with self._publish_lock:
                        if not self._stop.is_set():
                            publish_preview_error(request)
                self._stop.wait(min(2 ** attempts, 4))
