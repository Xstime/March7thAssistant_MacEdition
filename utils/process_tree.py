"""Terminate only descendants of an explicitly owned task process."""
import psutil


def terminate_tree(pid, timeout=2):
    try:
        root = psutil.Process(pid)
        processes = root.children(recursive=True) + [root]
    except psutil.NoSuchProcess:
        return
    for process in processes:
        try:
            process.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    _, alive = psutil.wait_procs(processes, timeout=timeout)
    for process in alive:
        try:
            # psutil verifies the process identity and protects against PID reuse.
            process.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
