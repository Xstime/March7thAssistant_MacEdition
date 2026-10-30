import plistlib

from utils import macos_autostart


def test_login_agent_is_opt_in_and_removable(tmp_path, monkeypatch):
    path = tmp_path / 'LaunchAgents' / 'agent.plist'
    monkeypatch.setattr(macos_autostart, 'agent_path', lambda: str(path))
    assert not macos_autostart.is_enabled()
    assert macos_autostart.enable()
    with path.open('rb') as stream:
        data = plistlib.load(stream)
    assert data['RunAtLoad'] is True
    assert data['KeepAlive'] is False
    assert data['ProgramArguments'][1] == '--autostart'
    assert macos_autostart.disable()
    assert not path.exists()


def test_existing_unrelated_agent_is_never_overwritten_or_deleted(tmp_path, monkeypatch):
    path = tmp_path / 'agent.plist'
    path.write_bytes(plistlib.dumps({'Label': 'another.application'}))
    before = path.read_bytes()
    monkeypatch.setattr(macos_autostart, 'agent_path', lambda: str(path))
    assert not macos_autostart.enable()
    assert not macos_autostart.disable()
    assert path.read_bytes() == before
