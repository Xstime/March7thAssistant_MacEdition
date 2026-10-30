"""Verify real config survives abrupt task-process termination."""
import os
import pytest
from pathlib import Path
import subprocess
import sys

from ruamel.yaml import YAML

pytestmark = pytest.mark.skipif(sys.platform != 'darwin', reason='macOS data path checkpoint')


def test_confirmed_plan_checkpoint_survives_abrupt_exit(tmp_path):
    data = tmp_path / 'data'
    logs = tmp_path / 'logs'
    env = os.environ.copy()
    env.update(MARCH7TH_DATA_DIR=str(data), MARCH7TH_LOG_DIR=str(logs),
               MARCH7TH_CONFIG_READONLY='0', QT_QPA_PLATFORM='offscreen')
    source = '''
import os
from module.config import cfg
from tasks.power.power import Power
from tasks.power.instance import Instance
cfg.set_value("power_plan", [["侵蚀隧洞", "副本一", 5], ["拟造花萼（金）", "副本二", 4]])
cfg.set_value("power_plan_keep", False)
Instance.validate_instance = staticmethod(lambda *args: True)
def interrupted(instance_type, instance_name, planned_attempts, on_progress):
    on_progress(2)
    os._exit(73)
Power.process = staticmethod(interrupted)
Power.execute_power_plan()
'''
    result = subprocess.run([sys.executable, '-c', source], env=env, capture_output=True, timeout=30)
    assert result.returncode == 73, result.stderr.decode('utf-8', errors='replace')
    with (data / 'config.yaml').open(encoding='utf-8') as stream:
        stored = YAML(typ='safe').load(stream)
    assert stored['power_plan'] == [['侵蚀隧洞', '副本一', 3], ['拟造花萼（金）', '副本二', 4]]
