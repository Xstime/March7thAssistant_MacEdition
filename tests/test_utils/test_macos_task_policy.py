"""Task-level browser fallback must not change persisted preferences."""
import os

import pytest

from utils.macos_task_policy import configure_for_task


def test_fight_runs_visible_without_rewriting_config(monkeypatch):
    monkeypatch.setenv("MARCH7TH_BROWSER_HEADLESS_ENABLE", "true")
    assert configure_for_task("fight", cloud_game_enabled=True) == "visible"
    assert os.environ["MARCH7TH_BROWSER_HEADLESS_ENABLE"] == "false"


def test_safe_task_does_not_override_user_setting(monkeypatch):
    monkeypatch.setenv("MARCH7TH_BROWSER_HEADLESS_ENABLE", "true")
    assert configure_for_task("power", cloud_game_enabled=True) == "headless-or-user-configured"
    assert os.environ["MARCH7TH_BROWSER_HEADLESS_ENABLE"] == "true"


def test_windows_only_task_fails_explicitly():
    with pytest.raises(RuntimeError, match="暂不支持"):
        configure_for_task("game_update", cloud_game_enabled=True)


def test_local_game_is_rejected_on_macos():
    with pytest.raises(RuntimeError, match="仅支持"):
        configure_for_task("daily", cloud_game_enabled=False)
