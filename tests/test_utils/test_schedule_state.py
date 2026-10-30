import json
from utils import schedule_state


def test_checkpoint_is_private_atomic_and_rejects_invalid_values(monkeypatch, tmp_path):
    monkeypatch.setattr(schedule_state, 'data_dir', lambda: str(tmp_path))
    assert schedule_state.read_checkpoint() is None
    assert not schedule_state.write_checkpoint(-1)
    assert schedule_state.write_checkpoint(1234567)
    path = tmp_path / 'runtime' / 'schedule-checkpoint.json'
    assert path.stat().st_mode & 0o777 == 0o600
    assert schedule_state.read_checkpoint() == 1234567
    path.write_text('{broken')
    assert schedule_state.read_checkpoint() is None
    path.write_text(json.dumps({'last_minute': True}))
    assert schedule_state.read_checkpoint() is None


def test_schedule_journal_persists_without_multiline_records(monkeypatch, tmp_path):
    monkeypatch.setattr(schedule_state, 'log_dir', lambda: str(tmp_path))
    schedule_state.record_schedule_event('任务延误\n下一行')
    path = tmp_path / 'scheduler.log'
    assert path.stat().st_mode & 0o777 == 0o600
    assert '任务延误 下一行' in path.read_text()
