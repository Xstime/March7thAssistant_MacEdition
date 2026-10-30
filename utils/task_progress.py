"""Private, atomic task progress exchanged between the worker and GUI."""
import json
import os
import sys
import tempfile
import time

from utils.runtime_paths import data_dir, private_dir

_PHASES = {'initializing', 'login', 'queue', 'loading', 'recognizing', 'running', 'waiting'}
_step = None
_total = None


def progress_path(pid):
    return os.path.join(data_dir(), 'runtime', f'progress-{int(pid)}.json')


def set_major_step(step, total):
    global _step, _total
    if isinstance(step, int) and isinstance(total, int) and 0 < step <= total <= 100:
        _step, _total = step, total
    else:
        _step = _total = None


def set_phase(phase, detail=''):
    if sys.platform != 'darwin' or phase not in _PHASES:
        return
    event = {'pid': os.getpid(), 'time': time.time(), 'phase': phase,
             'detail': str(detail)[:80], 'step': _step, 'total': _total}
    path = progress_path(os.getpid())
    try:
        private_dir(os.path.dirname(path))
        fd, temporary = tempfile.mkstemp(prefix='.progress-', dir=os.path.dirname(path))
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                json.dump(event, stream, ensure_ascii=False)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    except OSError:
        pass


def read_progress(pid, started_at):
    try:
        with open(progress_path(pid), encoding='utf-8') as stream:
            event = json.load(stream)
        if (event.get('pid') != pid or event.get('phase') not in _PHASES or
                not started_at <= event.get('time', 0) <= time.time() + 5):
            return None
        return event
    except (OSError, ValueError, TypeError, AttributeError):
        return None
