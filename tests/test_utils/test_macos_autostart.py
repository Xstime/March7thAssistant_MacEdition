"""macOS launchd service specification without executing launchctl."""
import plistlib
from pathlib import Path

import utils.autostart as autostart


def test_macos_login_agent_args_are_not_shell_strings(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(autostart, "IS_MACOS", True)
    monkeypatch.setattr(autostart.sys, "frozen", True, raising=False)
    monkeypatch.setattr(autostart.sys, "executable", "/Applications/Test.app/Contents/MacOS/Test")
    assert autostart._mac_launcher_args() == [
        "/Applications/Test.app/Contents/MacOS/Test", "--autostart"
    ]
    assert autostart.cli_command("power") == [
        "/Applications/Test.app/Contents/MacOS/Test", "--cli", "power"
    ]
    assert autostart._mac_launch_agent_path(tmp_path).parent == tmp_path / "Library" / "LaunchAgents"


def test_mac_launch_agent_writes_expected_plist(monkeypatch, tmp_path: Path):
    import utils.macos_paths as paths

    monkeypatch.setattr(autostart, "IS_MACOS", True)
    monkeypatch.setattr(autostart.sys, "frozen", True, raising=False)
    monkeypatch.setattr(autostart.sys, "executable", "/test/App")
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    commands = []
    monkeypatch.setattr(autostart, "_mac_launchd_command", lambda action, path: commands.append((action, path)))
    assert autostart.enable()
    target = autostart._mac_launch_agent_path()
    with target.open("rb") as file:
        data = plistlib.load(file)
    assert data["ProgramArguments"] == ["/test/App", "--autostart"]
    assert data["KeepAlive"] is False
    assert "bootstrap" in [cmd for cmd, _ in commands]
    assert autostart.disable()
    assert not target.exists()
