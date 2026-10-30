from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from module.automation import cdp_input


def make_input(dispatch):
    return cdp_input.CdpInput(SimpleNamespace(execute_cdp_cmd=dispatch), Mock())


def test_released_mouse_has_no_buttons_pressed(monkeypatch):
    monkeypatch.setattr(cdp_input.sys, 'platform', 'darwin')
    dispatch = Mock()
    handler = make_input(dispatch)
    handler.mouse_down(1, 2)
    handler.mouse_up()
    assert dispatch.call_args_list[-1].args[1]['buttons'] == 0


def test_mouse_move_preserves_held_button_and_modifier(monkeypatch):
    monkeypatch.setattr(cdp_input.sys, 'platform', 'darwin')
    dispatch = Mock()
    handler = make_input(dispatch)
    handler.active_modifiers = 8
    handler.mouse_down(1, 2)
    handler.mouse_move(3, 4)
    payload = dispatch.call_args.args[1]
    assert payload['buttons'] == 1 and payload['modifiers'] == 8
    handler.mouse_up()
    handler.mouse_move(5, 6)
    assert dispatch.call_args.args[1]['buttons'] == 0
    handler.press_mouse(wait_time=0)
    assert dispatch.call_args_list[-1].args[1]['buttons'] == 0


def test_click_attempts_release_when_interrupted(monkeypatch):
    monkeypatch.setattr(cdp_input.sys, 'platform', 'darwin')
    monkeypatch.setattr(cdp_input.time, 'sleep', Mock(side_effect=RuntimeError('interrupted')))
    dispatch = Mock()
    handler = make_input(dispatch)
    with pytest.raises(RuntimeError, match='interrupted'):
        handler.press_mouse()
    assert dispatch.call_args_list[-1].args[1]['type'] == 'mouseReleased'
    assert dispatch.call_args_list[-1].args[1]['buttons'] == 0


def test_key_is_released_when_interrupted(monkeypatch):
    monkeypatch.setattr(cdp_input.sys, 'platform', 'darwin')
    monkeypatch.setattr(cdp_input.time, 'sleep', Mock(side_effect=RuntimeError('interrupted')))
    dispatch = Mock()
    handler = make_input(dispatch)
    with pytest.raises(RuntimeError, match='interrupted'):
        handler.press_key('a')
    assert dispatch.call_args_list[-1].args[1]['type'] == 'keyUp'


def test_input_error_cannot_be_silently_reported_as_success(monkeypatch):
    monkeypatch.setattr(cdp_input.sys, 'platform', 'darwin')
    handler = make_input(Mock(side_effect=ConnectionError('browser closed')))
    with pytest.raises(ConnectionError, match='browser closed'):
        handler.mouse_move(1, 2)


def test_secret_input_error_does_not_echo_text(monkeypatch):
    monkeypatch.setattr(cdp_input.sys, 'platform', 'darwin')
    def dispatch(command, payload):
        if command == 'Input.insertText':
            raise RuntimeError('sensitive test text')
    handler = make_input(dispatch)
    with pytest.raises(RuntimeError, match='键盘输入失败') as error:
        handler.secretly_write('sensitive test text', interval=0)
    assert 'sensitive test text' not in str(error.value)
    assert 'sensitive test text' not in str(handler.logger.mock_calls)


def test_headless_key_focus_does_not_send_redundant_mouse_move(monkeypatch):
    monkeypatch.setattr(cdp_input.sys, 'platform', 'darwin')
    dispatch = Mock()
    cloud = SimpleNamespace(execute_cdp_cmd=dispatch, _actual_headless=True)
    handler = cdp_input.CdpInput(cloud, Mock())
    handler.press_key('a', wait_time=0)
    assert [call.args[0] for call in dispatch.call_args_list] == ['Input.dispatchKeyEvent', 'Input.dispatchKeyEvent']


def test_windowed_focus_still_moves_mouse(monkeypatch):
    monkeypatch.setattr(cdp_input.sys, 'platform', 'darwin')
    dispatch = Mock()
    cloud = SimpleNamespace(execute_cdp_cmd=dispatch, _actual_headless=False)
    handler = cdp_input.CdpInput(cloud, Mock())
    handler.focus()
    assert dispatch.call_args.args[0] == 'Input.dispatchMouseEvent'
    assert dispatch.call_args.args[1]['type'] == 'mouseMoved'
