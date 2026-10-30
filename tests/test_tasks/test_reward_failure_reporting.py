"""Detected rewards must not be reported as collected when actions fail."""
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from tasks.reward import RewardManager
from tasks.reward import mail, assist, achievement


@pytest.mark.parametrize('module,cls', [(mail, mail.Mail), (assist, assist.Assist), (achievement, achievement.Achievement)])
def test_missing_claim_button_is_failure(monkeypatch, module, cls):
    monkeypatch.setattr(module, 'auto', Mock(click_element=Mock(return_value=False)))
    monkeypatch.setattr(module.time, 'sleep', lambda _: None)
    instance = object.__new__(cls)
    assert instance.run() is False


def test_mail_requires_closing_reward_dialog(monkeypatch):
    monkeypatch.setattr(mail, 'auto', Mock(click_element=Mock(side_effect=[True, False])))
    monkeypatch.setattr(mail.time, 'sleep', lambda _: None)
    notify = Mock()
    monkeypatch.setattr(mail.Base, 'send_notification_with_screenshot', notify)
    assert object.__new__(mail.Mail).run() is False
    notify.assert_not_called()


def test_detected_failed_reward_fails_full_collection():
    manager = object.__new__(RewardManager)
    manager.reward_mapping = {'mail': ('image', 0.9, None), 'assist': ('image', 0.9, None)}
    manager.reward_instances = {'mail': SimpleNamespace(enabled=True, name='邮件', start=Mock(return_value=False)),
                                'assist': SimpleNamespace(enabled=True, name='支援', start=Mock(return_value=True))}
    manager._find_reward = Mock(return_value=True)
    assert manager.check_and_collect_rewards() is False
    manager.reward_instances['assist'].start.assert_called_once()


def test_disabled_detected_reward_is_skipped():
    manager = object.__new__(RewardManager)
    manager.reward_mapping = {'mail': ('image', 0.9, None)}
    manager.reward_instances = {'mail': SimpleNamespace(enabled=False, name='邮件', start=Mock(return_value=False))}
    manager._find_reward = Mock(return_value=True)
    assert manager.check_and_collect_rewards() is True
