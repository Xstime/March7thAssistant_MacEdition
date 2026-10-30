"""The manual browser launcher must not disrupt running tasks or mislabel errors."""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from app.tools.game_starter import GameLaunchThread, GameStartStatus


@pytest.mark.parametrize('browser_type,explicit,expected', [
    ('integrated', False, GameStartStatus.BROWSER_DOWNLOAD_FAIL),
    ('chrome', False, GameStartStatus.BROWSER_LAUNCH_FAIL),
    ('integrated', True, GameStartStatus.BROWSER_LAUNCH_FAIL),
])
def test_launch_failure_identifies_the_selected_browser(monkeypatch, browser_type, explicit, expected):
    for name in ('MARCH7TH_BROWSER_PATH', 'MARCH7TH_DRIVER_PATH'):
        if explicit:
            monkeypatch.setenv(name, '/local/test')
        else:
            monkeypatch.delenv(name, raising=False)
    game = Mock(start_game_process=Mock(return_value=False), is_integrated_browser_downloaded=Mock(return_value=False))
    cfg = SimpleNamespace(cloud_game_enable=True, browser_type=browser_type)
    worker = GameLaunchThread(game, cfg)
    outcomes = []
    worker.finished_signal.connect(outcomes.append)
    worker.run()
    assert outcomes == [expected]
    if browser_type != 'integrated' or explicit:
        game.is_integrated_browser_downloaded.assert_not_called()


def test_manual_browser_launch_does_not_interrupt_running_task(monkeypatch):
    from app import main_window
    button = Mock()
    window = SimpleNamespace(navigationInterface=Mock(widget=Mock(return_value=button)),
                             logInterface=Mock(_hasActiveStartedProcess=Mock(return_value=True)))
    monkeypatch.setattr(main_window.sys, 'platform', 'darwin')
    monkeypatch.setattr(main_window, 'cfg', SimpleNamespace(cloud_game_enable=True))
    warning = Mock()
    monkeypatch.setattr(main_window.InfoBar, 'warning', warning)
    get_game = Mock()
    monkeypatch.setattr(main_window, 'get_game_controller', get_game)
    main_window.MainWindow.startGame(window)
    get_game.assert_not_called()
    button.setEnabled.assert_any_call(False)
    button.setEnabled.assert_called_with(True)
    assert '任务正在运行' in warning.call_args.kwargs['title']


def test_browser_open_success_does_not_claim_game_has_started(monkeypatch):
    from app import main_window
    button = Mock()
    window = SimpleNamespace(navigationInterface=Mock(widget=Mock(return_value=button)))
    monkeypatch.setattr(main_window.sys, 'platform', 'darwin')
    monkeypatch.setattr(main_window, 'cfg', SimpleNamespace(cloud_game_enable=True))
    success = Mock()
    monkeypatch.setattr(main_window.InfoBar, 'success', success)
    main_window.MainWindow.on_game_launched(window, GameStartStatus.SUCCESS)
    assert '浏览器已打开' in success.call_args.kwargs['title']
    assert '登录并进入游戏' in success.call_args.kwargs['content']
    button.setEnabled.assert_called_with(True)


def test_starting_cloud_task_hands_off_gui_browser(qtbot, monkeypatch):
    from app import log_interface
    from types import SimpleNamespace
    controller = Mock()
    controller.driver = object()
    monkeypatch.setattr(log_interface, 'get_game_controller', Mock(return_value=controller))
    monkeypatch.setattr(log_interface, 'cfg', SimpleNamespace(cloud_game_enable=True, get_value=Mock(return_value=False)))
    monkeypatch.setattr(log_interface.sys, 'platform', 'darwin')
    interface = log_interface.LogInterface()
    qtbot.addWidget(interface)
    monkeypatch.setattr(interface, '_startTask', Mock())
    interface.startTask('daily')
    controller._detach_existing_driver.assert_called_once()
    interface._startTask.assert_called_once_with('daily')
    assert interface._gui_browser_handed_off is True
    interface.cleanup()


def test_failed_handoff_does_not_start_task(qtbot, monkeypatch):
    from app import log_interface
    from types import SimpleNamespace
    controller = Mock()
    controller.driver = object()
    controller._detach_existing_driver.return_value = False
    monkeypatch.setattr(log_interface, 'get_game_controller', Mock(return_value=controller))
    monkeypatch.setattr(log_interface, 'cfg', SimpleNamespace(cloud_game_enable=True, get_value=Mock(return_value=False)))
    monkeypatch.setattr(log_interface.sys, 'platform', 'darwin')
    interface = log_interface.LogInterface()
    qtbot.addWidget(interface)
    monkeypatch.setattr(interface, '_startTask', Mock())
    monkeypatch.setattr(interface, 'appendLog', Mock())
    interface.startTask('daily')
    interface._startTask.assert_not_called()
    assert not getattr(interface, '_gui_browser_handed_off', False)
    assert '任务未启动' in interface.appendLog.call_args.args[0]
    interface.cleanup()
