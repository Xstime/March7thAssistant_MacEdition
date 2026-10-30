import unittest
import base64
import os
import tempfile
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from urllib3.exceptions import ReadTimeoutError
from selenium.common.exceptions import TimeoutException, WebDriverException

from module.game.cloud import CloudGameController


class TestMacOSCloudPrivacy(unittest.TestCase):
    def test_login_exception_does_not_expose_credentials_or_traceback(self):
        controller = object.__new__(CloudGameController)
        controller.driver = MagicMock()
        controller._switch_to_login_iframe = MagicMock(side_effect=RuntimeError('token=secret-login'))
        controller.log_info = controller.log_warning = controller.log_error = MagicMock()
        with tempfile.TemporaryDirectory() as directory, \
                patch('module.game.cloud.sys.platform', 'darwin'), \
                patch('module.game.cloud.log_dir', return_value=directory), \
                patch('module.game.cloud.set_login_state'):
            self.assertFalse(controller._run_qr_login_flow())
        logged = str(controller.log_error.call_args_list) + str(controller.log_warning.call_args_list)
        self.assertNotIn('secret-login', logged)
        self.assertIn('RuntimeError', logged)
        self.assertNotIn('Traceback', logged)

    def test_screenshot_errors_do_not_log_page_or_browser_payload(self):
        controller = object.__new__(CloudGameController)
        controller.driver = MagicMock()
        controller.log_debug = MagicMock()
        controller.driver.current_url = 'https://example.invalid/?token=secret-url'
        controller.driver.title = 'secret-title'
        with patch('module.game.cloud.sys.platform', 'darwin'):
            controller.driver.execute_async_script.side_effect = RuntimeError('token=secret-error')
            with self.assertRaisesRegex(RuntimeError, '视频元素截图失败') as error:
                controller._take_video_screenshot()
            self.assertNotIn('secret-', str(error.exception))
            controller.driver.execute_async_script.side_effect = None
            controller.driver.execute_async_script.return_value = {
                'dataUrl': None, 'debug': {'url': 'secret-payload'}}
            self.assertIsNone(controller._take_video_screenshot())
        self.assertNotIn('secret-', str(controller.log_debug.call_args_list))

    def test_macos_exit_cleans_its_owned_browser_session(self):
        controller = object.__new__(CloudGameController)
        controller.driver = MagicMock()
        controller.stop_game = MagicMock()
        with patch('module.game.cloud.sys.platform', 'darwin'):
            controller._clean_at_exit()
        controller.stop_game.assert_called_once_with()

    def test_macos_exit_does_not_touch_other_sessions_without_a_driver(self):
        controller = object.__new__(CloudGameController)
        controller.driver = None
        controller.stop_game = MagicMock()
        with patch('module.game.cloud.sys.platform', 'darwin'):
            controller._clean_at_exit()
        controller.stop_game.assert_not_called()

    def test_stop_cleans_owned_processes_when_driver_configuration_is_missing(self):
        controller = object.__new__(CloudGameController)
        driver = MagicMock()
        driver.command_executor = None
        controller.driver = driver
        controller._stop_preview_worker = MagicMock()
        controller.close_all_m7a_browser = MagicMock(return_value=[])
        controller.log_debug = controller.log_info = controller.log_warning = MagicMock()
        with tempfile.TemporaryDirectory() as directory, \
                patch('module.game.cloud.sys.platform', 'darwin'), \
                patch('module.game.cloud.log_dir', return_value=directory), \
                patch('utils.preview_exchange.clear_preview'):
            self.assertTrue(controller.stop_game())
        driver.execute.assert_not_called()
        driver.quit.assert_not_called()
        driver.service.stop.assert_called_once()
        controller.close_all_m7a_browser.assert_called_once()
        self.assertIsNone(controller.driver)

    def test_stop_cleans_owned_processes_after_driver_commands_fail(self):
        controller = object.__new__(CloudGameController)
        driver = MagicMock()
        driver.command_executor._client_config.timeout = 60
        driver.execute.side_effect = RuntimeError('disconnected')
        driver.quit.side_effect = RuntimeError('disconnected')
        controller.driver = driver
        controller._stop_preview_worker = MagicMock()
        controller.close_all_m7a_browser = MagicMock(return_value=[])
        controller.log_debug = controller.log_info = controller.log_warning = MagicMock()
        with tempfile.TemporaryDirectory() as directory, \
                patch('module.game.cloud.sys.platform', 'darwin'), \
                patch('module.game.cloud.log_dir', return_value=directory), \
                patch('utils.preview_exchange.clear_preview'):
            self.assertTrue(controller.stop_game())
        self.assertEqual(driver.command_executor._client_config.timeout, 60)
        driver.service.stop.assert_called_once()
        controller.close_all_m7a_browser.assert_called_once()
        self.assertIsNone(controller.driver)

    def test_hung_owned_browser_is_killed_before_restart(self):
        controller = object.__new__(CloudGameController)
        owned = MagicMock()
        controller.get_m7a_browsers = MagicMock(return_value=[owned])
        controller._terminate_chromedriver_processes = MagicMock(return_value=[])
        with patch('module.game.cloud.sys.platform', 'darwin'), \
                patch('module.game.cloud.psutil.wait_procs', side_effect=[([], [owned]), ([owned], [])]):
            self.assertEqual(controller.close_all_m7a_browser(), [owned])
        owned.terminate.assert_called_once()
        owned.kill.assert_called_once()

    def test_failed_termination_is_reported(self):
        controller = object.__new__(CloudGameController)
        owned = MagicMock()
        owned.terminate.side_effect = PermissionError()
        controller.get_m7a_browsers = MagicMock(return_value=[owned])
        controller._terminate_chromedriver_processes = MagicMock(return_value=[])
        with patch('module.game.cloud.sys.platform', 'darwin'):
            with self.assertRaisesRegex(RuntimeError, '无法关闭小助手浏览器进程'):
                controller.close_all_m7a_browser()

    def test_takeover_uses_existing_other_mode_without_closing_or_launching(self):
        controller = object.__new__(CloudGameController)
        controller.cfg = SimpleNamespace(browser_type='chrome', browser_debug_port=9222)
        controller.user_profile_path = '/tmp/owned-profile'
        controller.driver = None
        controller._prepare_browser_and_driver = MagicMock(return_value=('/tmp/chrome', '/tmp/driver'))
        existing = MagicMock()
        controller.get_m7a_browsers = MagicMock(side_effect=lambda headless: [] if headless else [existing])
        controller.close_all_m7a_browser = MagicMock()
        controller._get_port_bind_error = MagicMock()
        controller._get_debug_port_from_cmdline = MagicMock(return_value=9223)
        controller._configure_pointer_lock = MagicMock()
        controller._start_preview_worker = MagicMock()
        controller.log_info = MagicMock()
        controller.log_warning = MagicMock()
        driver = MagicMock()
        with patch('module.game.cloud.sys.platform', 'darwin'), \
                patch('module.game.cloud.ChromeService'), \
                patch('module.game.cloud.webdriver.Chrome', return_value=driver) as chrome:
            controller._connect_or_create_browser(headless=True, existing_only=True)
        self.assertFalse(controller._actual_headless)
        self.assertEqual(chrome.call_args.kwargs['options'].debugger_address, '127.0.0.1:9223')
        controller.close_all_m7a_browser.assert_not_called()
        controller._get_port_bind_error.assert_not_called()
        controller._configure_pointer_lock.assert_called_once_with(False)

    def test_failed_takeover_detaches_without_closing_browser(self):
        controller = object.__new__(CloudGameController)
        controller.cfg = SimpleNamespace(browser_headless_enable=True)
        controller._connect_or_create_browser = MagicMock()
        controller._stop_preview_worker = MagicMock()
        controller.is_game_running = MagicMock(return_value=False)
        controller.driver = MagicMock()
        driver = controller.driver
        with self.assertRaisesRegex(RuntimeError, '没有可接管'):
            controller.attach_existing_game()
        driver.service.stop.assert_called_once()
        driver.quit.assert_not_called()
        self.assertIsNone(controller.driver)

    def test_takeover_rejects_browser_without_verifiable_debug_port(self):
        controller = object.__new__(CloudGameController)
        controller.cfg = SimpleNamespace(browser_type='chrome', browser_debug_port=9222)
        controller.user_profile_path = '/tmp/owned-profile'
        controller.driver = None
        controller._prepare_browser_and_driver = MagicMock(return_value=('/tmp/chrome', '/tmp/driver'))
        controller.get_m7a_browsers = MagicMock(return_value=[MagicMock()])
        controller._get_debug_port_from_cmdline = MagicMock(return_value=None)
        controller.close_all_m7a_browser = MagicMock()
        with patch('module.game.cloud.sys.platform', 'darwin'), \
                patch('module.game.cloud.ChromeService'), \
                patch('module.game.cloud.webdriver.Chrome') as chrome:
            with self.assertRaisesRegex(RuntimeError, '无法确认已有浏览器的调试端口'):
                controller._connect_or_create_browser(headless=True, existing_only=True)
        chrome.assert_not_called()
        controller.close_all_m7a_browser.assert_not_called()

    def test_qr_capture_is_local_and_private(self):
        controller = object.__new__(CloudGameController)
        element = MagicMock()
        element.screenshot_as_png = b"local-png"
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "qr.png")
            with patch("module.game.cloud.sys.platform", "darwin"), \
                    patch("module.game.cloud.requests.get") as request:
                controller._save_qr_from_src(element, path)
                with open(path, "rb") as image:
                    self.assertEqual(image.read(), b"local-png")
                if os.name != "nt":
                    self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)
                request.assert_not_called()
                element.get_attribute.assert_not_called()

    def test_qr_content_is_not_decoded_or_sent_on_macos(self):
        controller = object.__new__(CloudGameController)
        element = MagicMock()
        with patch("module.game.cloud.sys.platform", "darwin"):
            controller._decode_qr_from_element(element, "unused")
        element.get_attribute.assert_not_called()

    def test_driver_cleanup_does_not_kill_unrelated_driver_with_same_path(self):
        controller = object.__new__(CloudGameController)
        controller.driver_path = "/some/chromedriver"
        controller._driver_pid = None
        process = MagicMock()
        process.info = {"pid": 123, "name": "chromedriver"}
        process.exe.return_value = controller.driver_path
        process.ppid.return_value = 987654
        with patch("module.game.cloud.sys.platform", "darwin"), \
                patch("module.game.cloud.psutil.process_iter", return_value=[process]):
            self.assertEqual(controller._terminate_chromedriver_processes(), [])
        process.terminate.assert_not_called()

    def test_browser_discovery_requires_our_profile_on_macos(self):
        controller = object.__new__(CloudGameController)
        controller.user_profile_path = "/test/our-profile"
        controller.browser_path = "/test/Google Chrome for Testing"
        ours = MagicMock(info={"pid": 1, "name": "Google Chrome for Testing"})
        ours.cmdline.return_value = [controller.BROWSER_TAG, "--user-data-dir=/test/our-profile"]
        other = MagicMock(info={"pid": 2, "name": "Google Chrome for Testing"})
        other.cmdline.return_value = [controller.BROWSER_TAG, "--user-data-dir=/test/other-profile"]
        with patch("module.game.cloud.sys.platform", "darwin"), \
                patch("module.game.cloud.psutil.process_iter", return_value=[ours, other]):
            self.assertEqual(controller.get_m7a_browsers(), [ours])

    def test_custom_browser_arguments_cannot_replace_profile_or_expose_debugging(self):
        controller = object.__new__(CloudGameController)
        controller.cfg = SimpleNamespace(browser_scale_factor=1.0, browser_persistent_enable=False,
                                         cloud_game_fullscreen_enable=False,
                                         browser_launch_argument=['--remote-debugging-address=0.0.0.0'])
        with patch('module.game.cloud.sys.platform', 'darwin'):
            with self.assertRaisesRegex(ValueError, '不允许'):
                controller._get_browser_arguments(True)
            controller.cfg.browser_launch_argument = ['--user-data-dir=/tmp/other']
            with self.assertRaisesRegex(ValueError, '不允许'):
                controller._get_browser_arguments(True)
            controller.cfg.browser_launch_argument = []
            self.assertIn('--remote-debugging-address=127.0.0.1', controller._get_browser_arguments(True))


class FakeDriver:
    def __init__(self):
        self.commands = []

    def execute_cdp_cmd(self, command, params):
        self.commands.append((command, params))


class FakeLogger:
    def __init__(self):
        self.warnings = []

    def debug(self, _message):
        pass

    def warning(self, message):
        self.warnings.append(message)


class TestCloudGameSessionState(unittest.TestCase):
    def setUp(self):
        self.controller = object.__new__(CloudGameController)
        self.controller.driver = MagicMock()
        self.visible = MagicMock()
        self.visible.is_displayed.return_value = True
        self.hidden = MagicMock()
        self.hidden.is_displayed.return_value = False

    def elements(self, title=(), button=(), player=()):
        self.controller.driver.find_elements.side_effect = lambda by, selector: (
            title if '连接中断' in selector else button if '退出游戏' in selector else player)

    def test_disconnected_player_is_not_an_active_session(self):
        self.elements([self.visible], [self.visible], [self.visible])
        with self.assertRaisesRegex(ConnectionError, '会话已断开'):
            self.controller.is_in_game()

    def test_hidden_old_dialog_does_not_disconnect_live_player(self):
        self.elements([self.hidden], [self.hidden], [self.visible])
        self.assertTrue(self.controller.is_in_game())

    def test_title_without_exit_button_does_not_disconnect(self):
        self.elements([self.visible], [], [self.visible])
        self.assertTrue(self.controller.is_in_game())

    def test_hidden_player_is_not_in_game(self):
        self.elements(player=[self.hidden])
        self.assertFalse(self.controller.is_in_game())

    def test_no_driver_is_not_in_game(self):
        self.controller.driver = None
        self.assertFalse(self.controller.is_in_game())

    def test_macos_workflow_accepts_live_cloud_session_without_window_focus(self):
        controller = self.controller
        controller.is_in_game = MagicMock(return_value=True)
        with patch('module.game.cloud.sys.platform', 'darwin'):
            self.assertTrue(controller.is_game_running())
            self.assertTrue(controller.switch_to_game())

    def test_macos_workflow_rejects_missing_or_disconnected_session(self):
        controller = self.controller
        controller.is_in_game = MagicMock(side_effect=ConnectionError('disconnected'))
        controller.logger = MagicMock()
        with patch('module.game.cloud.sys.platform', 'darwin'):
            self.assertFalse(controller.is_game_running())
            self.assertFalse(controller.switch_to_game())
            controller.driver = None
            self.assertFalse(controller.is_game_running())

    def test_transient_unknown_login_state_does_not_start_qr_login(self):
        controller = self.controller
        controller.cfg = SimpleNamespace(browser_dump_cookies_enable=False,
                                         cloud_game_max_queue_time=1)
        controller.logger = MagicMock()
        controller._check_login = MagicMock(side_effect=[None, True])
        controller._run_qr_login_flow = MagicMock()
        controller._get_login_timeout_seconds = MagicMock(return_value=60)
        controller._get_remaining_playtime = MagicMock(return_value=(1, 0))
        controller._click_enter_game = MagicMock()
        controller._wait_in_queue = MagicMock(return_value=True)
        controller._confirm_viewport_resolution = MagicMock()
        states = []
        with patch("module.game.cloud.time.sleep"), patch("module.game.cloud.set_login_state", side_effect=states.append):
            self.assertTrue(controller.enter_cloud_game())
        controller._run_qr_login_flow.assert_not_called()
        self.assertEqual(states, ['checking', 'success'])


class TestCloudGameScreenshotTimeout(unittest.TestCase):
    def setUp(self):
        self.controller = object.__new__(CloudGameController)
        self.controller.driver = MagicMock()
        self.config = SimpleNamespace(timeout=120)
        self.controller.driver.command_executor._client_config = self.config
        self.controller._ensure_window_not_minimized_for_frame_capture = MagicMock()
        self.controller.logger = FakeLogger()

    def test_capture_limits_http_timeout_and_restores_it(self):
        def capture(*args):
            self.assertEqual(self.config.timeout, 15)
            return {'data': base64.b64encode(b'frame').decode()}
        self.controller.driver.execute_cdp_cmd.side_effect = capture
        self.assertEqual(self.controller._take_browser_screenshot(), b'frame')
        self.assertEqual(self.config.timeout, 120)
        self.controller.driver.get_screenshot_as_png.assert_not_called()

    def test_transport_timeout_does_not_enter_webdriver_fallback(self):
        self.controller.driver.execute_cdp_cmd.side_effect = ReadTimeoutError(None, '/', 'stalled')
        with self.assertRaisesRegex(TimeoutError, '截图请求超时'):
            self.controller._take_browser_screenshot()
        self.controller.driver.get_screenshot_as_png.assert_not_called()
        self.assertEqual(self.config.timeout, 120)

    def test_wrapped_transport_timeout_does_not_enter_webdriver_fallback(self):
        def capture(*_args):
            raise WebDriverException('CDP failed') from ReadTimeoutError(None, '/', 'stalled')
        self.controller.driver.execute_cdp_cmd.side_effect = capture
        with self.assertRaisesRegex(TimeoutError, '截图请求超时'):
            self.controller._take_browser_screenshot()
        self.controller.driver.get_screenshot_as_png.assert_not_called()
        self.assertEqual(self.config.timeout, 120)

    def test_implicit_wrapped_timeout_does_not_enter_webdriver_fallback(self):
        def capture(*_args):
            try:
                raise ReadTimeoutError(None, '/', 'stalled')
            except ReadTimeoutError:
                raise WebDriverException('CDP failed')
        self.controller.driver.execute_cdp_cmd.side_effect = capture
        with self.assertRaisesRegex(TimeoutError, '截图请求超时'):
            self.controller._take_browser_screenshot()
        self.controller.driver.get_screenshot_as_png.assert_not_called()

    def test_non_timeout_cdp_error_allows_webdriver_fallback(self):
        self.controller.driver.execute_cdp_cmd.side_effect = WebDriverException('CDP failed')
        self.controller.driver.get_screenshot_as_png.return_value = b'png'
        self.assertEqual(self.controller._take_browser_screenshot(), b'png')
        self.controller.driver.get_screenshot_as_png.assert_called_once_with()
        self.assertEqual(self.config.timeout, 120)

    def test_renderer_timeout_does_not_enter_webdriver_fallback(self):
        self.controller.driver.execute_cdp_cmd.side_effect = TimeoutException('renderer stalled')
        with self.assertRaises(TimeoutError):
            self.controller._take_browser_screenshot()
        self.controller.driver.get_screenshot_as_png.assert_not_called()

    def test_shorter_existing_timeout_is_preserved_during_fallback(self):
        self.config.timeout = 3
        self.controller.driver.execute_cdp_cmd.return_value = {}
        def fallback():
            self.assertEqual(self.config.timeout, 3)
            return b'png'
        self.controller.driver.get_screenshot_as_png.side_effect = fallback
        self.assertEqual(self.controller._take_browser_screenshot(), b'png')
        self.assertEqual(self.config.timeout, 3)

    def test_unbounded_timeout_is_capped_and_restored(self):
        self.config.timeout = None
        def capture(*args):
            self.assertEqual(self.config.timeout, 15)
            raise ReadTimeoutError(None, '/', 'stalled')
        self.controller.driver.execute_cdp_cmd.side_effect = capture
        with self.assertRaises(TimeoutError):
            self.controller._take_browser_screenshot()
        self.assertIsNone(self.config.timeout)


class TestCloudGameBackgroundRendering(unittest.TestCase):
    def test_macos_uses_native_display_scale_even_with_legacy_setting(self):
        controller = object.__new__(CloudGameController)
        controller.cfg = SimpleNamespace(browser_scale_factor=0.5, browser_persistent_enable=False,
                                         cloud_game_fullscreen_enable=False, browser_launch_argument=[])
        with patch('module.game.cloud.sys.platform', 'darwin'):
            args = controller._get_browser_arguments(False)
            self.assertFalse(any(arg.startswith('--force-device-scale-factor') for arg in args))
            controller.cfg.browser_launch_argument = ['--force-device-scale-factor=0.5']
            with self.assertRaises(ValueError):
                controller._get_browser_arguments(False)

    def test_visible_browser_keeps_rendering_without_front_window_focus(self):
        controller = object.__new__(CloudGameController)
        controller.cfg = SimpleNamespace(browser_scale_factor=1, browser_persistent_enable=False,
                                         cloud_game_fullscreen_enable=False, browser_launch_argument=[])
        args = controller._get_browser_arguments(False)
        self.assertIn('--disable-backgrounding-occluded-windows', args)
        self.assertIn('--disable-renderer-backgrounding', args)
        self.assertIn('--disable-background-timer-throttling', args)
        self.assertNotIn('--headless=new', args)


class TestCloudGameStalledShutdown(unittest.TestCase):
    def test_unresponsive_driver_does_not_skip_process_cleanup(self):
        controller = object.__new__(CloudGameController)
        controller.driver = driver = MagicMock()
        config = SimpleNamespace(timeout=120)
        driver.command_executor._client_config = config
        def stalled(*args):
            self.assertEqual(config.timeout, 15)
            raise ReadTimeoutError(None, '/', 'stalled')
        driver.execute.side_effect = stalled
        driver.quit.side_effect = stalled
        controller.log_debug = MagicMock()
        controller.log_info = MagicMock()
        controller.log_warning = MagicMock()
        controller.close_all_m7a_browser = MagicMock(return_value=[object()])
        with patch.object(os.path, 'exists', return_value=False):
            self.assertTrue(controller.stop_game())
        controller.close_all_m7a_browser.assert_called_once()
        self.assertIsNone(controller.driver)
        self.assertEqual(config.timeout, 120)


class TestCloudGamePointerLock(unittest.TestCase):
    def create_controller(self):
        controller = object.__new__(CloudGameController)
        controller.driver = FakeDriver()
        controller.logger = FakeLogger()
        return controller

    def test_pointer_lock_is_denied_in_headless_mode(self):
        controller = self.create_controller()

        controller._configure_pointer_lock(headless=True)

        self.assertEqual(
            controller.driver.commands[0][0],
            "Page.addScriptToEvaluateOnNewDocument",
        )
        params = controller.driver.commands[0][1]
        self.assertTrue(params["runImmediately"])
        self.assertIn("requestPointerLock", params["source"])
        self.assertIn("document.exitPointerLock", params["source"])

    def test_pointer_lock_is_unchanged_in_visible_mode(self):
        controller = self.create_controller()

        controller._configure_pointer_lock(headless=False)

        self.assertEqual(controller.driver.commands, [])


class TestCloudGameDebugPort(unittest.TestCase):
    def create_controller(self):
        controller = object.__new__(CloudGameController)
        controller.logger = FakeLogger()
        return controller

    def test_find_available_port_prefers_configured_range(self):
        controller = self.create_controller()

        with patch.object(
            controller,
            "_is_port_available",
            side_effect=[False, False, True],
        ):
            port = controller._find_available_port(9222)

        self.assertEqual(port, 9224)
        self.assertEqual(controller.logger.warnings, [])

    def test_port_bind_error_is_preserved_for_diagnostics(self):
        bind_error = OSError(10013, "permission denied")
        socket_context = MagicMock()
        socket_context.__enter__.return_value.bind.side_effect = bind_error

        with patch("module.game.cloud.socket.socket", return_value=socket_context):
            result = CloudGameController._get_port_bind_error(9222)

        self.assertIs(result, bind_error)

    def test_find_available_port_falls_back_to_system_assigned_port(self):
        controller = self.create_controller()

        with (
            patch.object(controller, "_is_port_available", return_value=False),
            patch.object(controller, "_get_system_assigned_port", return_value=49152),
        ):
            port = controller._find_available_port(9222)

        self.assertEqual(port, 49152)
        self.assertEqual(
            controller.logger.warnings,
            ["端口范围 9222-9231 均不可用，将使用系统分配的端口 49152"],
        )

    def test_system_assigned_port_reports_socket_error(self):
        socket_context = MagicMock()
        socket_context.__enter__.return_value.bind.side_effect = OSError(
            10013,
            "permission denied",
        )

        with patch("module.game.cloud.socket.socket", return_value=socket_context):
            with self.assertRaisesRegex(
                RuntimeError,
                r"系统自动分配可用端口失败（错误码 10013:",
            ):
                CloudGameController._get_system_assigned_port()

    def test_system_assigned_port_uses_port_zero(self):
        socket_context = MagicMock()
        socket_context.__enter__.return_value.getsockname.return_value = (
            "127.0.0.1",
            49152,
        )

        with patch("module.game.cloud.socket.socket", return_value=socket_context):
            port = CloudGameController._get_system_assigned_port()

        socket_context.__enter__.return_value.bind.assert_called_once_with(
            ("127.0.0.1", 0)
        )
        self.assertEqual(port, 49152)


def test_hidden_scan_success_element_does_not_end_qr_wait(monkeypatch, tmp_path):
    from unittest.mock import Mock
    from selenium.webdriver.common.by import By
    import module.game.cloud as cloud_module

    controller = object.__new__(CloudGameController)
    controller.driver = Mock()
    controller.log_info = Mock()
    controller.log_debug = Mock()
    controller.log_warning = Mock()
    hidden, visible = Mock(), Mock()
    hidden.is_displayed.return_value = False
    visible.is_displayed.return_value = True
    scans = iter([[hidden], [visible]])
    def find_elements(by, selector):
        if by == By.XPATH:
            return next(scans)
        return []
    controller.driver.find_elements.side_effect = find_elements
    states = []
    monkeypatch.setattr(cloud_module, 'set_login_state', states.append)
    monkeypatch.setattr(cloud_module.time, 'sleep', Mock())
    path = tmp_path / 'qr.png'
    path.write_bytes(b'local')
    controller._wait_scan_success_with_refresh(str(path))
    assert hidden.is_displayed.call_count == 1
    assert visible.is_displayed.call_count == 1
    assert states == ['waiting_confirm']
    assert not path.exists()


class TestMacOSHeadlessFallback(unittest.TestCase):
    def make_controller(self):
        from module.game.cloud import CloudGameController
        controller = object.__new__(CloudGameController)
        controller.cfg = SimpleNamespace(browser_headless_enable=True)
        controller._connect_or_create_browser = MagicMock()
        controller._confirm_viewport_resolution = MagicMock()
        controller.stop_game = MagicMock(return_value=True)
        controller.log_warning = controller.log_error = MagicMock()
        return controller

    def test_selenium_session_creation_error_is_classified_for_fallback(self):
        from selenium.common.exceptions import SessionNotCreatedException
        from module.game.cloud import HeadlessBrowserStartError
        controller = object.__new__(CloudGameController)
        controller.cfg = SimpleNamespace(browser_type='chrome', browser_debug_port=9222)
        controller.user_profile_path = '/tmp/owned-profile'
        controller.driver = None
        controller._prepare_browser_and_driver = MagicMock(return_value=('/tmp/chrome', '/tmp/driver'))
        controller._get_port_bind_error = MagicMock(return_value=None)
        controller.get_m7a_browsers = MagicMock(return_value=[])
        controller.close_all_m7a_browser = MagicMock(return_value=[])
        controller._get_browser_arguments = MagicMock(return_value=[])
        controller.log_info = controller.log_warning = controller.log_debug = controller.log_error = MagicMock()
        with patch('module.game.cloud.sys.platform', 'darwin'), \
                patch('module.game.cloud.is_docker_started', return_value=False), \
                patch('module.game.cloud.ChromeService'), \
                patch('module.game.cloud.webdriver.Chrome', side_effect=SessionNotCreatedException('failure')):
            with self.assertRaises(HeadlessBrowserStartError):
                controller._connect_or_create_browser(headless=True)

    def test_headless_session_failure_falls_back_without_changing_config(self):
        from module.game.cloud import HeadlessBrowserStartError
        controller = self.make_controller()
        controller._connect_or_create_browser.side_effect = [HeadlessBrowserStartError(), None]
        with patch('module.game.cloud.sys.platform', 'darwin'), patch('module.game.cloud.set_phase'):
            self.assertTrue(controller.start_game_process())
        self.assertEqual([call.kwargs['headless'] for call in controller._connect_or_create_browser.call_args_list],
                         [True, False])
        controller.stop_game.assert_called_once()
        controller._confirm_viewport_resolution.assert_called_once()
        self.assertTrue(controller.cfg.browser_headless_enable)

    def test_other_failures_do_not_trigger_visible_browser(self):
        controller = self.make_controller()
        controller._connect_or_create_browser.side_effect = RuntimeError('configuration failure')
        with patch('module.game.cloud.sys.platform', 'darwin'), patch('module.game.cloud.set_phase'):
            self.assertFalse(controller.start_game_process())
        controller._connect_or_create_browser.assert_called_once_with(headless=True)
        controller.stop_game.assert_not_called()

    def test_failed_cleanup_does_not_start_a_second_browser(self):
        from module.game.cloud import HeadlessBrowserStartError
        controller = self.make_controller()
        controller._connect_or_create_browser.side_effect = HeadlessBrowserStartError()
        controller.stop_game.return_value = False
        with patch('module.game.cloud.sys.platform', 'darwin'), patch('module.game.cloud.set_phase'):
            self.assertFalse(controller.start_game_process())
        controller._connect_or_create_browser.assert_called_once_with(headless=True)

    def test_window_fallback_login_does_not_restart_headless(self):
        controller = self.make_controller()
        controller.cfg = SimpleNamespace(browser_headless_enable=True,
            browser_headless_restart_on_not_logged_in=True, browser_dump_cookies_enable=False,
            cloud_game_max_queue_time=1)
        controller._actual_headless = False
        controller.logger = MagicMock()
        controller._check_login = MagicMock(side_effect=[False, True, True])
        controller._run_qr_login_flow = MagicMock()
        controller._get_login_timeout_seconds = MagicMock(return_value=60)
        controller._get_remaining_playtime = MagicMock(return_value=(1, 0))
        controller._click_enter_game = MagicMock()
        controller._wait_in_queue = MagicMock(return_value=True)
        controller._restart_browser = MagicMock()
        with patch('module.game.cloud.sys.platform', 'darwin'), \
                patch('module.game.cloud.time.sleep'), patch('module.game.cloud.set_login_state'), \
                patch('module.game.cloud.set_phase'):
            self.assertTrue(controller.enter_cloud_game())
        controller._restart_browser.assert_not_called()
        controller._run_qr_login_flow.assert_not_called()


def test_failed_driver_detach_retains_ownership_for_cleanup():
    controller = object.__new__(CloudGameController)
    driver = MagicMock()
    driver.service.stop.side_effect = OSError('service failure')
    controller.driver = driver
    controller._stop_preview_worker = MagicMock()
    controller.log_warning = MagicMock()
    assert controller._detach_existing_driver() is False
    assert controller.driver is driver
