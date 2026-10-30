import os

from utils import runtime_paths


def test_macos_data_and_logs_are_separate(monkeypatch, tmp_path):
    monkeypatch.setattr(runtime_paths.sys, "platform", "darwin")
    monkeypatch.delenv("MARCH7TH_DATA_DIR", raising=False)
    monkeypatch.delenv("MARCH7TH_LOG_DIR", raising=False)
    monkeypatch.setattr(runtime_paths.os.path, "expanduser", lambda path: str(tmp_path / path[2:]))
    assert runtime_paths.data_dir() == str(tmp_path / "Library/Application Support/March7thAssistant")
    assert runtime_paths.log_dir() == str(tmp_path / "Library/Logs/March7thAssistant")


def test_explicit_data_and_log_overrides_are_independent(monkeypatch, tmp_path):
    monkeypatch.setenv("MARCH7TH_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("MARCH7TH_LOG_DIR", str(tmp_path / "logs"))
    assert runtime_paths.data_dir() == str(tmp_path / "data")
    assert runtime_paths.log_dir() == str(tmp_path / "logs")
    assert not os.path.exists(runtime_paths.data_dir())


def test_private_directory_is_not_world_readable(tmp_path):
    directory = tmp_path / "private"
    runtime_paths.private_dir(str(directory))
    assert os.name == 'nt' or directory.stat().st_mode & 0o077 == 0
