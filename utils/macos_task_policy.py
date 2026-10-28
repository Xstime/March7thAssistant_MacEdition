"""Conservative macOS cloud task compatibility policy.

Per-task overrides are only applied in the CLI worker process. The user's
stored configuration is never rewritten. Full runs use visible Chrome until
the mixed-task flow is separately verified as headless-safe.
"""
from __future__ import annotations

import os


VISIBLE_BROWSER_TASKS = frozenset({"main", "fight", "universe"})
UNSUPPORTED_MACOS_LOCAL_TASKS = frozenset({
    "game_update", "game_pre_download", "mobileui_update",
    "fight_gui", "universe_gui",
})


def configure_for_task(task: str, cloud_game_enabled: bool) -> str:
    """Return the selected browser policy, or raise on Windows-only tasks."""
    if task in UNSUPPORTED_MACOS_LOCAL_TASKS:
        raise RuntimeError(
            f"任务 {task} 需要尚未适配的 Windows 本地游戏功能，macOS 版本暂不支持"
        )
    if not cloud_game_enabled:
        raise RuntimeError("macOS 版本目前仅支持云·星穹铁道自动化")
    if task in VISIBLE_BROWSER_TASKS:
        os.environ["MARCH7TH_BROWSER_HEADLESS_ENABLE"] = "false"
        return "visible"
    return "headless-or-user-configured"
