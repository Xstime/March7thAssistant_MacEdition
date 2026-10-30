"""Opt-in per-user login launch agent; never starts or stops a running app."""
import os
import plistlib
import sys
import tempfile

LABEL = 'org.march7thassistant.macos.autostart'


def agent_path():
    return os.path.expanduser('~/Library/LaunchAgents/' + LABEL + '.plist')


def _owned(path, executable):
    try:
        if os.path.islink(path):
            return False
        with open(path, 'rb') as stream:
            value = plistlib.load(stream)
        return (value.get('Label') == LABEL and
                value.get('ProgramArguments') == [executable, '--autostart'])
    except (OSError, ValueError, plistlib.InvalidFileException):
        return False


def is_enabled():
    return _owned(agent_path(), sys.executable)


def enable():
    path = agent_path()
    if os.path.lexists(path) and not _owned(path, sys.executable):
        return False
    directory = os.path.dirname(path)
    os.makedirs(directory, mode=0o700, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.march7-', suffix='.plist', dir=directory)
    try:
        with os.fdopen(fd, 'wb') as stream:
            plistlib.dump({'Label': LABEL, 'ProgramArguments': [sys.executable, '--autostart'],
                           'RunAtLoad': True, 'KeepAlive': False}, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return is_enabled()


def disable():
    path = agent_path()
    if not os.path.lexists(path):
        return True
    if not _owned(path, sys.executable):
        return False
    os.unlink(path)
    return True
