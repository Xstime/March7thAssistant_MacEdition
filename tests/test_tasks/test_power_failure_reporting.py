"""Do not report failed battles as completed or discard remaining plans."""
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from tasks.power import instance as instance_module
from tasks.power import power as power_module


def prepare_instance(monkeypatch):
    monkeypatch.setattr(instance_module, 'cfg', SimpleNamespace(instance_team_enable=False, tp_before_instance=False))
    monkeypatch.setattr(instance_module, 'auto', Mock())
    monkeypatch.setattr(instance_module.time, 'sleep', lambda _: None)
    instance = instance_module.Instance
    monkeypatch.setattr(instance, 'validate_instance', Mock(return_value=True))
    monkeypatch.setattr(instance, 'prepare_instance', Mock(return_value=True))
    monkeypatch.setattr(instance, 'start_instance', Mock(return_value=True))
    monkeypatch.setattr(instance, 'complete_run', Mock())
    return instance


def test_battle_failure_is_bounded_and_not_reported_success(monkeypatch):
    instance = prepare_instance(monkeypatch)
    monkeypatch.setattr(instance, 'wait_fight', Mock(return_value=False))
    assert instance.run('饰品提取', '测试副本', 1, 1) is False
    assert instance.wait_fight.call_count == 3
    instance.complete_run.assert_not_called()


def test_failure_to_start_next_round_is_propagated(monkeypatch):
    instance = prepare_instance(monkeypatch)
    monkeypatch.setattr(instance, 'wait_fight', Mock(return_value=True))
    monkeypatch.setattr(instance, 'start_instance_again', Mock(return_value=False))
    assert instance.run('侵蚀隧洞', '测试副本', 1, 2) is False
    instance.complete_run.assert_not_called()


def test_exhausted_retries_are_distinct_from_low_power(monkeypatch):
    cfg = SimpleNamespace(instance_names_challenge_count={'侵蚀隧洞': 1})
    monkeypatch.setattr(power_module, 'cfg', cfg)
    monkeypatch.setattr(power_module.Power, 'get', Mock(return_value=40))
    monkeypatch.setattr(power_module.Instance, 'run', Mock(return_value=False))
    with pytest.raises(power_module.PowerRunError, match='多次运行失败') as error:
        power_module.Power.process('侵蚀隧洞', '测试副本')
    assert error.value.completed == 0
    assert power_module.Instance.run.call_count == 3
    power_module.Power.get.return_value = 0
    assert power_module.Power.process('侵蚀隧洞', '测试副本') == 0


def test_failed_plan_preserves_unfinished_and_later_entries(monkeypatch):
    plan = [['侵蚀隧洞', '副本一', 5], ['拟造花萼（金）', '副本二', 4]]
    values = {'power_plan': plan, 'power_plan_keep': False}
    cfg = Mock(get_value=Mock(side_effect=lambda key, default=None: values.get(key, default)))
    monkeypatch.setattr(power_module, 'cfg', cfg)
    monkeypatch.setattr(power_module.Instance, 'validate_instance', Mock(return_value=True))
    monkeypatch.setattr(power_module.Power, 'process', Mock(side_effect=power_module.PowerRunError('失败', completed=2)))
    with pytest.raises(RuntimeError, match='体力计划未完成'):
        power_module.Power.execute_power_plan()
    cfg.set_value.assert_called_once_with('power_plan', [['侵蚀隧洞', '副本一', 3], plan[1]])


def test_successful_round_is_reported_before_later_failure(monkeypatch):
    instance = prepare_instance(monkeypatch)
    monkeypatch.setattr(instance, 'wait_fight', Mock(side_effect=[True, False]))
    monkeypatch.setattr(instance, 'start_instance_again', Mock(return_value=True))
    completed = Mock()
    assert instance.run('侵蚀隧洞', '测试副本', 2, 2, on_round_completed=completed) is False
    completed.assert_called_once_with(2)
    instance.complete_run.assert_not_called()


def test_retry_does_not_report_previous_round_twice(monkeypatch):
    instance = prepare_instance(monkeypatch)
    monkeypatch.setattr(instance, 'wait_fight', Mock(side_effect=[True, False, True]))
    monkeypatch.setattr(instance, 'start_instance_again', Mock(return_value=True))
    completed = Mock()
    assert instance.run('饰品提取', '测试副本', 2, 2, on_round_completed=completed) is True
    assert [call.args for call in completed.call_args_list] == [(2,), (2,)]
    instance.complete_run.assert_called_once()


def test_partial_success_is_kept_when_later_retries_fail(monkeypatch):
    cfg = SimpleNamespace(instance_names_challenge_count={'侵蚀隧洞': 2})
    monkeypatch.setattr(power_module, 'cfg', cfg)
    monkeypatch.setattr(power_module.Power, 'get', Mock(return_value=200))
    calls = []
    def battle(instance_type, instance_name, attempts_per_run, runs, on_round_completed):
        calls.append((attempts_per_run, runs))
        if len(calls) == 1:
            on_round_completed(2)
        return False
    monkeypatch.setattr(power_module.Instance, 'run', battle)
    with pytest.raises(power_module.PowerRunError) as error:
        power_module.Power.process('侵蚀隧洞', '测试副本', planned_attempts=5)
    assert error.value.completed == 2
    assert calls == [(2, 2), (2, 1), (2, 1)]


def test_insufficient_power_after_failure_does_not_hide_failure(monkeypatch):
    cfg = SimpleNamespace(instance_names_challenge_count={'侵蚀隧洞': 1})
    monkeypatch.setattr(power_module, 'cfg', cfg)
    monkeypatch.setattr(power_module.Power, 'get', Mock(side_effect=[80, 0]))
    def battle(instance_type, instance_name, attempts_per_run, runs, on_round_completed):
        on_round_completed(1)
        return False
    monkeypatch.setattr(power_module.Instance, 'run', battle)
    with pytest.raises(power_module.PowerRunError, match='剩余体力不足') as error:
        power_module.Power.process('侵蚀隧洞', '测试副本', planned_attempts=2)
    assert error.value.completed == 1


def test_exception_after_confirmed_round_retains_progress(monkeypatch):
    cfg = SimpleNamespace(instance_names_challenge_count={'侵蚀隧洞': 1})
    monkeypatch.setattr(power_module, 'cfg', cfg)
    monkeypatch.setattr(power_module.Power, 'get', Mock(return_value=80))
    def battle(instance_type, instance_name, attempts_per_run, runs, on_round_completed):
        on_round_completed(1)
        raise RuntimeError('connection lost')
    monkeypatch.setattr(power_module.Instance, 'run', battle)
    with pytest.raises(power_module.PowerRunError, match='副本执行异常') as error:
        power_module.Power.process('侵蚀隧洞', '测试副本', planned_attempts=2)
    assert error.value.completed == 1


def test_resource_read_error_after_failure_retains_progress(monkeypatch):
    cfg = SimpleNamespace(instance_names_challenge_count={'侵蚀隧洞': 1})
    monkeypatch.setattr(power_module, 'cfg', cfg)
    monkeypatch.setattr(power_module.Power, 'get', Mock(side_effect=[80, RuntimeError('disconnected')]))
    def battle(instance_type, instance_name, attempts_per_run, runs, on_round_completed):
        on_round_completed(1)
        return False
    monkeypatch.setattr(power_module.Instance, 'run', battle)
    with pytest.raises(power_module.PowerRunError, match='读取体力') as error:
        power_module.Power.process('侵蚀隧洞', '测试副本', planned_attempts=2)
    assert error.value.completed == 1


def test_confirmed_plan_progress_is_saved_before_interruption(monkeypatch):
    plan = [['侵蚀隧洞', '副本一', 5], ['拟造花萼（金）', '副本二', 4]]
    values = {'power_plan': plan, 'power_plan_keep': False}
    cfg = Mock(get_value=Mock(side_effect=lambda key, default=None: values.get(key, default)))
    monkeypatch.setattr(power_module, 'cfg', cfg)
    monkeypatch.setattr(power_module.Instance, 'validate_instance', Mock(return_value=True))
    def interrupted(instance_type, instance_name, planned_attempts, on_progress):
        on_progress(2)
        raise KeyboardInterrupt()
    monkeypatch.setattr(power_module.Power, 'process', interrupted)
    with pytest.raises(KeyboardInterrupt):
        power_module.Power.execute_power_plan()
    cfg.set_value.assert_called_once_with('power_plan', [['侵蚀隧洞', '副本一', 3], plan[1]])


def test_keep_plan_mode_does_not_checkpoint_repeated_plan(monkeypatch):
    plan = [['侵蚀隧洞', '副本一', 5]]
    values = {'power_plan': plan, 'power_plan_keep': True}
    cfg = Mock(get_value=Mock(side_effect=lambda key, default=None: values.get(key, default)))
    monkeypatch.setattr(power_module, 'cfg', cfg)
    monkeypatch.setattr(power_module.Instance, 'validate_instance', Mock(return_value=True))
    def interrupted(instance_type, instance_name, planned_attempts, on_progress):
        on_progress(2)
        raise KeyboardInterrupt()
    monkeypatch.setattr(power_module.Power, 'process', interrupted)
    with pytest.raises(KeyboardInterrupt):
        power_module.Power.execute_power_plan()
    cfg.set_value.assert_not_called()


def test_failed_checkpoint_stops_further_battles(monkeypatch):
    cfg = SimpleNamespace(instance_names_challenge_count={'侵蚀隧洞': 1})
    monkeypatch.setattr(power_module, 'cfg', cfg)
    monkeypatch.setattr(power_module.Power, 'get', Mock(return_value=80))
    def battle(instance_type, instance_name, attempts_per_run, runs, on_round_completed):
        on_round_completed(1)
        pytest.fail('checkpoint failure must stop the battle flow')
    monkeypatch.setattr(power_module.Instance, 'run', Mock(side_effect=battle))
    with pytest.raises(power_module.PowerRunError) as error:
        power_module.Power.process('侵蚀隧洞', '测试副本', planned_attempts=2,
                                   on_progress=Mock(side_effect=OSError('disk error')))
    assert error.value.completed == 1
    assert power_module.Instance.run.call_count == 1


def test_invalid_entries_are_preserved_during_successful_checkpoint(monkeypatch):
    malformed = ['broken', None]
    plan = [malformed, ['侵蚀隧洞', '副本一', 3], None]
    values = {'power_plan': plan, 'power_plan_keep': False}
    cfg = Mock(get_value=Mock(side_effect=lambda key, default=None: values.get(key, default)))
    monkeypatch.setattr(power_module, 'cfg', cfg)
    monkeypatch.setattr(power_module.Instance, 'validate_instance', Mock(return_value=True))
    def interrupted(instance_type, instance_name, planned_attempts, on_progress):
        on_progress(1)
        raise KeyboardInterrupt()
    monkeypatch.setattr(power_module.Power, 'process', interrupted)
    with pytest.raises(KeyboardInterrupt):
        power_module.Power.execute_power_plan()
    cfg.set_value.assert_called_once_with('power_plan', [malformed, ['侵蚀隧洞', '副本一', 2], None])


def test_no_power_preserves_invalid_entries_later_in_plan(monkeypatch):
    plan = [['侵蚀隧洞', '副本一', 3], None, ['broken']]
    values = {'power_plan': plan, 'power_plan_keep': False}
    cfg = Mock(get_value=Mock(side_effect=lambda key, default=None: values.get(key, default)))
    monkeypatch.setattr(power_module, 'cfg', cfg)
    monkeypatch.setattr(power_module.Instance, 'validate_instance', Mock(return_value=True))
    monkeypatch.setattr(power_module.Power, 'process', Mock(return_value=0))
    assert power_module.Power.execute_power_plan() is False
    cfg.set_value.assert_called_once_with('power_plan', plan)


def test_invalid_counts_are_preserved_and_never_executed(monkeypatch):
    plan = [['侵蚀隧洞', '副本一', 'invalid'], ['侵蚀隧洞', '副本二', -1], ['侵蚀隧洞', '副本三', True]]
    values = {'power_plan': plan, 'power_plan_keep': False}
    cfg = Mock(get_value=Mock(side_effect=lambda key, default=None: values.get(key, default)))
    monkeypatch.setattr(power_module, 'cfg', cfg)
    process = Mock()
    monkeypatch.setattr(power_module.Power, 'process', process)
    assert power_module.Power.execute_power_plan() is False
    process.assert_not_called()
    cfg.set_value.assert_called_once_with('power_plan', plan)


def test_readonly_config_stops_plan_before_battle(monkeypatch):
    class ReadonlyConfig:
        _readonly = True
        def get_value(self, key, default=None):
            return {'power_plan': [['侵蚀隧洞', '副本一', 3]], 'power_plan_keep': False}.get(key, default)
    monkeypatch.setattr(power_module, 'cfg', ReadonlyConfig())
    process = Mock()
    monkeypatch.setattr(power_module.Power, 'process', process)
    with pytest.raises(RuntimeError, match='只读模式'):
        power_module.Power.execute_power_plan()
    process.assert_not_called()
