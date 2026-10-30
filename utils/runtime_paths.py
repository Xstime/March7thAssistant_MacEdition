"""Locations for mutable application data, separate from bundled resources."""
import os
import sys


def data_dir():
    override = os.environ.get("MARCH7TH_DATA_DIR")
    if override:
        return os.path.abspath(os.path.expanduser(override))
    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support/March7thAssistant")
    return os.getcwd()


def log_dir():
    override = os.environ.get("MARCH7TH_LOG_DIR")
    if override:
        return os.path.abspath(os.path.expanduser(override))
    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/Logs/March7thAssistant")
    return os.path.join(os.getcwd(), "logs")


def private_dir(path):
    """Create application-owned directories without changing existing permissions."""
    os.makedirs(path, mode=0o700, exist_ok=True)
    return path
