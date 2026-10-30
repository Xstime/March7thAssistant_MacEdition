"""macOS must not advertise Windows-only tools as usable."""
from types import SimpleNamespace, MethodType
from unittest.mock import Mock
import pytest


def test_card_editor_marks_unsupported_without_persisting_label(qtbot, monkeypatch):
    from app.card import card_edit_dialog as editor
    monkeypatch.setattr(editor.sys, 'platform', 'darwin')
    row = editor.MenuItemRow(task_id='fight')
    qtbot.addWidget(row)
    assert 'macOS 不支持' in row.task_combo.currentText()
    assert 'macOS 不支持' not in row.get_data()['label']
    assert row.get_data()['task_id'] == 'fight'


def test_home_menu_marks_unsupported_and_blocks_windows_file_operation(monkeypatch):
    from app import home_interface as home
    monkeypatch.setattr(home.sys, 'platform', 'darwin')
    warning = Mock()
    monkeypatch.setattr(home.InfoBar, 'warning', warning)
    remove = Mock()
    monkeypatch.setattr(home.os, 'remove', remove)
    interface = SimpleNamespace()
    interface._get_extra_task_action = MethodType(home.HomeInterface._get_extra_task_action, interface)
    card = {'action_type': 'menu', 'menu_items': [
        {'label': '锄大地', 'task_id': 'fight'},
        {'label': '重置配置', 'task_id': '_reset_fight_config'},
        {'label': '每日实训', 'task_id': 'daily'}]}
    actions = home.HomeInterface._build_card_action(interface, card)
    assert '锄大地（macOS 不支持）' in actions
    assert '重置配置（macOS 不支持）' in actions
    assert '每日实训' in actions
    actions['重置配置（macOS 不支持）']()
    warning.assert_called_once()
    remove.assert_not_called()


def test_macos_rejects_disabled_cloud_client(monkeypatch):
    import module.game as game
    monkeypatch.setattr(game.sys, 'platform', 'darwin')
    monkeypatch.setattr(game, 'cfg', SimpleNamespace(cloud_game_enable=False))
    with pytest.raises(RuntimeError, match='不支持 Windows 本地游戏客户端'):
        game.get_game_controller()


def test_upstream_homepage_uses_macos_browser(monkeypatch):
    import webbrowser
    from app import home_interface as home
    monkeypatch.setattr(home.sys, 'platform', 'darwin')
    open_url = Mock()
    monkeypatch.setattr(webbrowser, 'open', open_url)
    interface = SimpleNamespace()
    action = home.HomeInterface._get_extra_task_action(interface, '_open_fight_homepage')
    action()
    open_url.assert_called_once_with('https://github.com/linruowuyin/Fhoe-Rail')
