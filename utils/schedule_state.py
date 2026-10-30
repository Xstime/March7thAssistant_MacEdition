"""Private scheduler checkpoint and bounded journal for macOS."""
import json
import os
import tempfile
import time

from utils.runtime_paths import data_dir, log_dir, private_dir


def checkpoint_path():
    return os.path.join(data_dir(), 'runtime', 'schedule-checkpoint.json')


def read_checkpoint():
    try:
        with open(checkpoint_path(), encoding='utf-8') as stream:
            value = json.load(stream).get('last_minute')
        return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else None
    except (OSError, ValueError, TypeError, AttributeError):
        return None


def write_checkpoint(minute):
    if not isinstance(minute, int) or isinstance(minute, bool) or minute <= 0:
        return False
    path = checkpoint_path()
    try:
        private_dir(os.path.dirname(path))
        fd, temporary = tempfile.mkstemp(prefix='.schedule-', dir=os.path.dirname(path))
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                json.dump({'last_minute': minute}, stream)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return True
    except OSError:
        return False


def record_schedule_event(message):
    try:
        directory = private_dir(log_dir())
        path = os.path.join(directory, 'scheduler.log')
        if os.path.exists(path) and os.path.getsize(path) >= 1024 * 1024:
            os.replace(path, path + '.1')
        fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        with os.fdopen(fd, 'a', encoding='utf-8') as stream:
            stream.write(time.strftime('%Y-%m-%d %H:%M:%S') + ' ' + str(message).replace('\n', ' ') + '\n')
    except OSError:
        pass
