"""CPU/解析重活必须在可终止子进程中运行。"""

import pytest


def test_isolated_runner_returns_picklable_result():
    from src.workers.isolated_runner import run_isolated

    assert run_isolated("operator:add", args=(2, 3), timeout_seconds=5) == 5


def test_isolated_runner_surfaces_child_error():
    from src.workers.isolated_runner import IsolatedProcessError, run_isolated

    with pytest.raises(IsolatedProcessError, match="invalid literal"):
        run_isolated("builtins:int", args=("not-a-number",), timeout_seconds=5)


def test_isolated_runner_terminates_timeout_and_next_task_recovers():
    from src.workers.isolated_runner import IsolatedProcessTimeout, run_isolated

    with pytest.raises(IsolatedProcessTimeout):
        run_isolated("time:sleep", args=(5,), timeout_seconds=0.1)
    assert run_isolated("operator:add", args=(4, 5), timeout_seconds=5) == 9
