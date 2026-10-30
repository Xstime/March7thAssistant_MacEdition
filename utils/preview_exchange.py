"""Small private, on-demand preview exchange between GUI and task processes."""
import os
import tempfile
import uuid

from utils.runtime_paths import data_dir, private_dir


def _directory():
    return os.path.join(data_dir(), "runtime")


def _atomic_write(path, content):
    private_dir(os.path.dirname(path))
    fd, temporary = tempfile.mkstemp(prefix='.preview-', dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(content)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def request_preview():
    request = uuid.uuid4().hex.encode('ascii')
    _atomic_write(os.path.join(_directory(), 'preview.request'), request)
    return request


def preview_path():
    return os.path.join(_directory(), 'preview.img')


def pending_request():
    try:
        with open(os.path.join(_directory(), 'preview.request'), 'rb') as stream:
            return stream.read(128)
    except FileNotFoundError:
        return None


def publish_requested_frame(frame, previous_request, expected_request=None):
    request = pending_request()
    if expected_request is not None and request != expected_request:
        return previous_request
    if request and request != previous_request and frame:
        # The request id and image are one atomic record. A response from an
        # older request can never be mistaken for the current one by the GUI.
        _atomic_write(preview_path(), frame)
        _atomic_write(os.path.join(_directory(), 'preview.response'), request + b'\n' + frame)
        return request
    return previous_request


def read_requested_frame(request):
    if not request:
        return None
    try:
        path = os.path.join(_directory(), 'preview.response')
        with open(path, 'rb') as stream:
            stamp = os.fstat(stream.fileno()).st_mtime_ns
            response, separator, frame = stream.read().partition(b'\n')
        if separator and response == request and frame:
            return frame, stamp
    except OSError:
        pass
    return None


def publish_preview_error(request):
    if request and pending_request() == request:
        _atomic_write(os.path.join(_directory(), 'preview.error'), request)


def has_preview_error():
    try:
        request = pending_request()
        with open(os.path.join(_directory(), 'preview.error'), 'rb') as stream:
            return bool(request and stream.read(128) == request)
    except OSError:
        return False


def clear_preview():
    for name in ('preview.request', 'preview.img', 'preview.error', 'preview.response'):
        try:
            os.unlink(os.path.join(_directory(), name))
        except FileNotFoundError:
            pass
