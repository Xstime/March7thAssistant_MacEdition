from module.logger import log
from module.screen import screen
from module.config import cfg
from module.automation import auto
from .mail import Mail
from .assist import Assist
from .dispatch import Dispatch
from .quest import Quest
from .srpass import SRPass
from .achievement import Achievement
from .message import Message


class RewardManager:
    def __init__(self):
        self.assist = Assist("支援", cfg.reward_assist_enable, "visa")
        self.mail = Mail("邮件", cfg.reward_mail_enable, "mail")
        self.dispatch = Dispatch("委托", cfg.reward_dispatch_enable, "dispatch")
        self.quest = Quest("每日实训", cfg.reward_quest_enable, "guide2")
        self.srpass = SRPass("无名勋礼", cfg.reward_srpass_enable, "pass2")
        self.achievement = Achievement("成就", cfg.reward_achievement_enable, "achievement")
        self.message = Message("短信", cfg.reward_message_enable, "incoming_message")
        self.crop = (1263.0 / 1920, 52.0 / 1080, 642.0 / 1920, 982.0 / 1080)

        self.reward_instances = {
            "mail": self.mail,
            "assist": self.assist,
            "dispatch": self.dispatch,
            "quest": self.quest,
            "srpass": self.srpass,
            "achievement": self.achievement,
            "message": self.message,
        }

        self.reward_mapping = {
            "mail": ("./assets/images/share/base/RedExclamationMark.png", 0.9, (1823.0 / 1920, 224.0 / 1080, 91.0 / 1920, 92.0 / 1080)),
            "assist": ("./assets/images/share/menu/assist_reward.png", 2000000, self.crop),
            "dispatch": ("./assets/images/share/menu/dispatch.png", 2000000, self.crop),
            "quest": ("./assets/images/share/menu/quest_reward.png", 2000000, self.crop),
            "srpass": ("./assets/images/share/menu/pass_reward.png", 2000000, self.crop),
            "achievement": ("./assets/images/share/menu/achievement_reward.png", 2000000, self.crop),
            "message": ("./assets/images/share/menu/message_reward.png", 2000000, self.crop),
        }

    def check_and_collect_rewards(self):
        log.hr("开始领取奖励", 0)
        failed = []

        for reward_type, (image_path, confidence, crop) in self.reward_mapping.items():
            if self._find_reward(image_path, confidence, crop):
                instance = self.reward_instances[reward_type]
                result = instance.start()
                if instance.enabled and reward_type in {'mail', 'assist', 'achievement'} and result is False:
                    failed.append(instance.name)
            else:
                reward_name = self._get_reward_name(reward_type)
                log.info(f"未检测到{reward_name}奖励")

        if failed:
            log.warning("奖励领取未确认：" + '、'.join(failed))
            return False
        log.hr("完成", 2)
        return True

    def check_and_collect_specific_reward(self, reward_type):
        reward_name = self._get_reward_name(reward_type)
        log.hr(f"开始领取{reward_name}奖励", 0)
        result = False

        if reward_type in self.reward_mapping:
            image_path, confidence, crop = self.reward_mapping[reward_type]
            # A completed daily may have no remaining red badge. Visit it to
            # verify its 500-point indicator rather than treating absence of a
            # badge as proof of either success or failure.
            if reward_type == "quest" or self._find_reward(image_path, confidence, crop):
                result = self.reward_instances[reward_type].start()
            else:
                log.info(f"未检测到{reward_name}奖励")
        else:
            log.error(f"未知的奖励类型： {reward_type}")

        if result is False:
            log.warning(f"{reward_name}奖励未领取或状态未确认")
        else:
            log.hr("完成", 2)
        return result

    def _get_reward_name(self, reward_type):
        instance = self.reward_instances.get(reward_type)
        return instance.name if instance else "未知"

    def _find_reward(self, image_path, confidence, crop):
        screen.change_to('menu')
        return auto.find_element(image_path, "image", confidence, crop=crop)


def start():
    if not cfg.reward_enable:
        log.info("领取奖励未开启")
        return

    reward_manager = RewardManager()
    return reward_manager.check_and_collect_rewards()


def start_specific(reward_type):
    if not cfg.reward_enable:
        log.info("领取奖励未开启")
        return False

    reward_manager = RewardManager()
    return reward_manager.check_and_collect_specific_reward(reward_type)
