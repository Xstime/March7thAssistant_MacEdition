from unittest.mock import Mock

import pytest

from tasks.activity import doubleactivity


@pytest.mark.parametrize(
    ('text', 'expected'),
    [('奖励剩余次数 2/12', 2), ('0／12', 0), ('12 / 12', 12),
     ('无法识别', None), ('13/12', None), ('0/0', None)],
)
def test_reward_count_requires_a_valid_fraction(monkeypatch, text, expected):
    auto = Mock()
    auto.find_element.return_value = True
    auto.ocr_result = [(None, (text, 0.99))]
    monkeypatch.setattr(doubleactivity, 'auto', auto)
    activity = doubleactivity.DoubleActivity('测试活动', True, 'type', {'type': 'name'})
    assert activity._get_reward_count() == expected


def test_missing_label_does_not_use_stale_ocr(monkeypatch):
    auto = Mock()
    auto.find_element.return_value = False
    auto.ocr_result = [(None, ('0/12', 0.99))]
    monkeypatch.setattr(doubleactivity, 'auto', auto)
    activity = doubleactivity.DoubleActivity('测试活动', True, 'type', {'type': 'name'})
    assert activity.run() is False


def test_zero_is_completed_but_unreadable_is_retried():
    activity = doubleactivity.DoubleActivity('测试活动', True, 'type', {'type': 'name'})
    activity._run_instances = Mock()
    activity._get_reward_count = Mock(side_effect=[0, None])
    assert activity.run() is True
    assert activity.run() is False
    activity._run_instances.assert_not_called()
