"""
app/agentic_AI/runtime.py

How a background task enters async code.

Every graph invocation in this codebase starts from a synchronous background
task and reaches Postgres through psycopg's async driver — which **cannot run on
Windows' default ProactorEventLoop** and raises `InterfaceError` on connect.

Setting `WindowsSelectorEventLoopPolicy` at import is not enough on its own, and
this is the trap: the call sites import `checkpointer` *lazily, inside the
coroutine*, so the policy lands after `asyncio.run()` has already built its loop.
The policy is then correct for the next run and useless for this one, which makes
the failure look intermittent and import-order dependent.

`run_async` removes the ordering question entirely by naming the loop it wants at
the point of use. The policy is still set below, for any path that calls
`asyncio.run` directly.

Deliberately dependency-free so it can be imported at module scope anywhere
without dragging the saver — and its Postgres driver — along with it.
"""
from __future__ import annotations

import asyncio
import selectors
import sys
from typing import Any, Coroutine, TypeVar

T = TypeVar("T")

IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def _selector_loop() -> asyncio.AbstractEventLoop:
    return asyncio.SelectorEventLoop(selectors.SelectSelector())


def run_async(coro: Coroutine[Any, Any, T]) -> T:
    """
    Run a coroutine from synchronous code, on a loop psycopg can use.

    Use this instead of `asyncio.run` anywhere a graph might be invoked. Off
    Windows it is exactly `asyncio.run`.
    """
    if not IS_WINDOWS:
        return asyncio.run(coro)

    try:
        return asyncio.run(coro, loop_factory=_selector_loop)
    except TypeError:
        # `loop_factory` arrived in Python 3.12. On older runtimes the policy set
        # at import is what carries this, so fall back to it.
        return asyncio.run(coro)
