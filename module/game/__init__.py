import sys
from module.config import cfg
from module.logger import log
from module.game.base import GameControllerBase
from module.game.cloud import CloudGameController
from module.game.local import LocalGameController

cloud_game: CloudGameController = CloudGameController(cfg=cfg, logger=log)
local_game: LocalGameController = LocalGameController(cfg=cfg, logger=log)


def get_game_controller() -> GameControllerBase:
    if cfg.cloud_game_enable:
        return cloud_game
    else:
        if sys.platform == 'darwin':
            raise RuntimeError("macOS 不支持 Windows 本地游戏客户端；请启用云游戏并移除禁用它的环境变量。")
        local_game.reload_config(cfg)
        return local_game
