from module.config import cfg
from module.logger import log
from module.screen import screen
from module.automation import auto
from module.notification.notification import NotificationLevel
from tasks.base.base import Base
from .rewardtemplate import RewardTemplate
import time


class Quest(RewardTemplate):
    def run(self):
        get_reward = False
        # 领取活跃度
        for _ in range(20):
            if not auto.click_element("./assets/images/zh_CN/reward/quest/receive.png", "image", 0.8, crop=(265.0 / 1920, 394.0 / 1080, 1400.0 / 1920, 504.0 / 1080)):
                break
            time.sleep(0.5)
            get_reward = True
        else:
            log.warning("每日实训领取次数超过上限")
            return False

        # 领取奖励
        if auto.click_element("./assets/images/share/reward/quest/gift.png", "image", 0.9, max_retries=10, crop=(415.0 / 1920, 270.0 / 1080, 1252.0 / 1920, 114.0 / 1080)):
            if not auto.click_element("./assets/images/zh_CN/base/click_close.png", "image", 0.8, max_retries=10):
                return False
            get_reward = True

        # 判断完成
        if not auto.find_element("./assets/images/screen/guide/guide2.png", "image", 0.9, max_retries=10):
            return False
        if auto.find_element("./assets/images/share/reward/quest/500.png", "image", 0.9, max_retries=5, crop=(415.0 / 1920, 270.0 / 1080, 1252.0 / 1920, 114.0 / 1080)):
            cfg.set_value("daily_tasks", {})
            if get_reward:
                Base.send_notification_with_screenshot(cfg.notify_template['DailyPracticeCompleted'], NotificationLevel.ALL)
            return True
        Base.send_notification_with_screenshot(cfg.notify_template['DailyPracticeNotCompleted'], NotificationLevel.ERROR)
        return False
