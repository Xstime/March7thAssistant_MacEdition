"""Local login-state metadata, without QR contents or account information."""
import json
import os
import sys
import tempfile
import time

from utils.runtime_paths import data_dir, private_dir

_STATES = {'checking', 'waiting_qr', 'waiting_scan', 'waiting_confirm',
           'verifying', 'success', 'failed', 'timed_out'}
_last_state = None


def state_path(pid):
    return os.path.join(data_dir(), 'runtime', f'login-{int(pid)}.json')


def set_login_state(state):
    global _last_state
    if sys.platform != 'darwin' or state not in _STATES or state == _last_state:
        return
    path = state_path(os.getpid())
    event = {'pid': os.getpid(), 'time': time.time(), 'state': state}
    try:
        private_dir(os.path.dirname(path))
        fd, temporary = tempfile.mkstemp(prefix='.login-', dir=os.path.dirname(path))
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                json.dump(event, stream)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        _last_state = state
    except OSError:
        pass


def read_login_state(pid, started_at):
    try:
        with open(state_path(pid), encoding='utf-8') as stream:
            event = json.load(stream)
        if (event.get('pid') != pid or event.get('state') not in _STATES or
                not started_at <= event.get('time', 0) <= time.time() + 5):
            return None
        return event['state']
    except (OSError, ValueError, TypeError, AttributeError):
        return None
