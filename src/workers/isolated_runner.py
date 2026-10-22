"""以 spawn 子进程运行可导入函数，并在硬超时后终止整个进程。"""

from __future__ import annotations

import importlib
import multiprocessing
import traceback
from typing import Any


class IsolatedProcessError(RuntimeError):
    pass


class IsolatedProcessTimeout(TimeoutError):
    pass


def _resolve_target(target: str):
    module_name, separator, attribute = target.partition(":")
    if not separator or not module_name or not attribute:
        raise ValueError("target 必须采用 module:function 格式")
    value = importlib.import_module(module_name)
    for part in attribute.split("."):
        value = getattr(value, part)
    return value


def _child(connection, target: str, args: tuple[Any, ...], kwargs: dict[str, Any]) -> None:
    try:
        result = _resolve_target(target)(*args, **kwargs)
        connection.send(("ok", result))
    except BaseException as exc:
        connection.send(("error", f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"))
    finally:
        connection.close()


def run_isolated(
    target: str,
    *,
    args: tuple[Any, ...] = (),
    kwargs: dict[str, Any] | None = None,
    timeout_seconds: float,
) -> Any:
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds 必须大于 0")
    context = multiprocessing.get_context("spawn")
    parent, child = context.Pipe(duplex=False)
    process = context.Process(
        target=_child,
        args=(child, target, tuple(args), dict(kwargs or {})),
        daemon=True,
    )
    process.start()
    child.close()
    try:
        if not parent.poll(timeout_seconds):
            if process.is_alive():
                process.terminate()
            process.join(timeout=5)
            if process.is_alive():
                process.kill()
                process.join(timeout=5)
            raise IsolatedProcessTimeout(f"子进程超过 {timeout_seconds} 秒硬超时")
        status, payload = parent.recv()
        process.join(timeout=5)
        if status == "error":
            raise IsolatedProcessError(payload)
        return payload
    finally:
        parent.close()
        if process.is_alive():
            process.terminate()
            process.join(timeout=5)
