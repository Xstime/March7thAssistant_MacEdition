from unittest.mock import Mock

from utils import process_tree


def test_only_owned_processes_are_terminated_and_survivors_killed(monkeypatch):
    root = Mock()
    child = Mock()
    root.children.return_value = [child]
    monkeypatch.setattr(process_tree.psutil, 'Process', Mock(return_value=root))
    wait = Mock(return_value=([child], [root]))
    monkeypatch.setattr(process_tree.psutil, 'wait_procs', wait)
    process_tree.terminate_tree(42, timeout=1)
    root.children.assert_called_once_with(recursive=True)
    child.terminate.assert_called_once()
    root.terminate.assert_called_once()
    child.kill.assert_not_called()
    root.kill.assert_called_once()
    wait.assert_called_once_with([child, root], timeout=1)
