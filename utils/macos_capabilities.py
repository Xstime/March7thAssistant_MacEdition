"""Tasks that upstream explicitly restricts to the Windows client or tools."""
UNSUPPORTED_TASKS = {
    "fight": "锄大地依赖上游 Windows 专用工具，当前无法在 macOS 上运行。",
    "fight_gui": "锄大地工具界面仅支持 Windows。",
    "fight_update": "锄大地工具更新仅支持 Windows。",
    "universe": "传统模拟宇宙依赖上游 Windows 专用工具，当前无法在 macOS 上运行。",
    "universe_gui": "传统模拟宇宙工具界面仅支持 Windows。",
    "universe_update": "传统模拟宇宙工具更新仅支持 Windows。",
    "game_update": "本地游戏客户端更新仅支持 Windows。",
    "game_pre_download": "本地游戏客户端预下载仅支持 Windows。",
    "app_update": "上游 Windows 版本更新器不适用于 macOS，请使用 macOS 版本的安装包。",
    "_reset_universe_config": "传统模拟宇宙工具仅支持 Windows，无法在 macOS 重置其配置。",
    "_open_universe_dir": "传统模拟宇宙工具仅支持 Windows，macOS 没有对应程序目录。",
    "_reset_fight_config": "锄大地工具仅支持 Windows，无法在 macOS 重置其配置。",
    "_open_fight_dir": "锄大地工具仅支持 Windows，macOS 没有对应程序目录。",
}


def unsupported_reason(task):
    return UNSUPPORTED_TASKS.get(task)
