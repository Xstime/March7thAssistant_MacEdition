"""Import non-sensitive task settings from an upstream YAML configuration."""
import os
import shutil
import tempfile
import time

from ruamel.yaml import YAML

TASK_PREFIXES = ('daily_', 'power_', 'reward_', 'echo_of_war_', 'weekly_',
                 'currencywars_', 'universe_', 'fight_', 'build_target_', 'instance_')
SENSITIVE_PARTS = ('password', 'token', 'secret', 'cookie', 'webhook', 'apikey',
                   'api_key', 'credential', 'account', 'path', 'command', 'script')


def _clean_nested(value):
    if isinstance(value, dict):
        return {key: _clean_nested(item) for key, item in value.items()
                if isinstance(key, str) and not any(part in key.lower() for part in SENSITIVE_PARTS)}
    if isinstance(value, list):
        return [_clean_nested(item) for item in value]
    return value


def _compatible(value, expected):
    if value is None or expected is None:
        return value is None and expected is None
    for kind in (bool, dict, list, str, int, float):
        if isinstance(expected, kind):
            return isinstance(value, kind) and (kind is not int or not isinstance(value, bool))
    return False


def select_task_settings(source, defaults):
    if not isinstance(source, dict):
        raise ValueError('配置文件必须是 YAML 映射')
    result = {}
    for key, value in source.items():
        if not isinstance(key, str) or key not in defaults:
            continue
        name = key.lower()
        if not (name.startswith(TASK_PREFIXES) or name == 'refresh_hour'):
            continue
        if any(part in name for part in SENSITIVE_PARTS):
            continue
        # Task settings are scalar or plain lists/dicts, never executable objects.
        expected = defaults[key]
        if not _compatible(value, expected):
            continue
        if isinstance(value, (str, int, float, bool, list, dict)) or value is None:
            result[key] = _clean_nested(value)
    return result


def import_task_settings(source_path, config):
    if os.path.getsize(source_path) > 5 * 1024 * 1024:
        raise ValueError('配置文件超过 5 MB')
    with open(source_path, 'r', encoding='utf-8') as stream:
        source = YAML(typ='safe').load(stream)
    selected = select_task_settings(source, config.config)
    if not selected:
        raise ValueError('配置文件中没有可导入的任务设置')
    backup = None
    if os.path.isfile(config.config_path):
        directory = os.path.dirname(os.path.abspath(config.config_path))
        stamp = time.strftime('%Y%m%d-%H%M%S')
        fd, backup = tempfile.mkstemp(prefix=f'config.yaml.before-import-{stamp}-', suffix='.bak', dir=directory)
        try:
            with os.fdopen(fd, 'wb') as target, open(config.config_path, 'rb') as current:
                shutil.copyfileobj(current, target)
                target.flush()
                os.fsync(target.fileno())
        except Exception:
            os.unlink(backup)
            raise
    config.set_values(selected)
    return len(selected), backup
