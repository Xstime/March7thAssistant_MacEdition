import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from utils.config_import import import_task_settings, select_task_settings


def test_only_known_non_sensitive_task_settings_are_selected():
    defaults = {'daily_enable': False, 'power_plan': [], 'reward_token': '',
                'fight_path': '', 'notify_token': '', 'power_options': {}}
    source = {'daily_enable': True, 'power_plan': [['副本', 2]], 'reward_token': 'secret',
              'fight_path': '/private/path', 'notify_token': 'secret',
              'power_options': {'mode': 1, 'api_key': 'secret'}, 'daily_unknown': True}
    assert select_task_settings(source, defaults) == {
        'daily_enable': True, 'power_plan': [['副本', 2]], 'power_options': {'mode': 1}}


def test_import_backs_up_current_config_before_applying(tmp_path):
    source = tmp_path / 'docker.yaml'
    source.write_text('daily_enable: true\n', encoding='utf-8')
    current = tmp_path / 'config.yaml'
    current.write_text('daily_enable: false\n', encoding='utf-8')
    config = SimpleNamespace(config={'daily_enable': False}, config_path=str(current), set_values=Mock())
    count, backup = import_task_settings(str(source), config)
    assert count == 1
    assert Path(backup).read_text(encoding='utf-8') == 'daily_enable: false\n'
    assert os.name == 'nt' or Path(backup).stat().st_mode & 0o077 == 0
    config.set_values.assert_called_once_with({'daily_enable': True})


def test_bad_or_empty_import_does_not_change_config(tmp_path):
    source = tmp_path / 'invalid.yaml'
    source.write_text('- not-a-mapping\n', encoding='utf-8')
    config = SimpleNamespace(config={'daily_enable': False}, config_path=str(tmp_path / 'config.yaml'), set_values=Mock())
    with pytest.raises(ValueError):
        import_task_settings(str(source), config)
    config.set_values.assert_not_called()
