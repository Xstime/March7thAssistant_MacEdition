"""Private, bounded metadata for the macOS task diagnostics panel."""
import json
import os
import tempfile
import time

from utils.runtime_paths import data_dir, log_dir, private_dir

_last_write = {}
_last_recognition_time = None


def _path(pid, event):
    if event not in ('capture', 'ocr'):
        raise ValueError('unknown diagnostic event')
    return os.path.join(data_dir(), 'runtime', f'diagnostic-{int(pid)}-{event}.json')


def record_event(event, *, engine=None, recognized=None):
    """Never record screenshots, OCR text, account data, or URLs."""
    global _last_recognition_time
    if event == 'ocr' and recognized:
        _last_recognition_time = time.time()
    now = time.monotonic()
    key = (event, engine, recognized)
    if now - _last_write.get(key, float('-inf')) < 5:
        return
    payload = {'pid': os.getpid(), 'time': time.time()}
    if event == 'ocr':
        payload.update(engine=str(engine or 'unknown')[:64], recognized_at=_last_recognition_time)
    path = _path(os.getpid(), event)
    try:
        private_dir(os.path.dirname(path))
        fd, temporary = tempfile.mkstemp(prefix='.diagnostic-', dir=os.path.dirname(path))
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                json.dump(payload, stream)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        _last_write[key] = now
    except OSError:
        # Monitoring must never abort a task.
        pass


def read_event(pid, event, started_at):
    try:
        with open(_path(pid, event), encoding='utf-8') as stream:
            value = json.load(stream)
        if value.get('pid') != pid or not started_at <= value.get('time', 0) <= time.time() + 5:
            return None
        return value
    except (OSError, ValueError, TypeError, AttributeError):
        return None


def clear_events(pid):
    for event in ('capture', 'ocr'):
        try:
            os.unlink(_path(pid, event))
        except FileNotFoundError:
            pass


def record_sample(sample):
    """Record bounded resource metadata, without task contents or identifiers."""
    try:
        directory = private_dir(log_dir())
        path = os.path.join(directory, 'runtime-diagnostics.jsonl')
        if os.path.exists(path) and os.path.getsize(path) >= 1024 * 1024:
            os.replace(path, path + '.1')
        fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        with os.fdopen(fd, 'a', encoding='utf-8') as stream:
            stream.write(json.dumps(sample, ensure_ascii=False) + '\n')
    except OSError:
        pass
