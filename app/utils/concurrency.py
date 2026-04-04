"""CPU-bound helpers: run blocking work off the event loop (bcrypt, etc.)."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Callable, ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")

_executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="moapril-")


async def run_in_thread(fn: Callable[P, R], *args: P.args, **kwargs: P.kwargs) -> R:
    import asyncio

    loop = asyncio.get_running_loop()
    if kwargs:
        return await loop.run_in_executor(_executor, partial(fn, *args, **kwargs))
    return await loop.run_in_executor(_executor, fn, *args)


def shutdown_executor() -> None:
    _executor.shutdown(wait=False, cancel_futures=True)
