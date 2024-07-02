# Copyright 2020-2024 The MathWorks, Inc.

from typing import Dict, Set, Union
from contextlib import suppress

import asyncio

from matlab_proxy.util import mwi, system, windows

logger = mwi.logger.get()


def get_event_loop():
    """Returns an asyncio event loop by checking the Operating System and
    uses the appropriate asyncio API

    Returns:
        asyncio.loop: asyncio event loop.
    """
    try:
        # Try to get an existing event loop.
        # If there's no running event loop, raises RuntimeError.
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # If execution reached this except block, it implies that there
        # was no running event loop. So, create one.
        if system.is_posix():
            loop = asyncio.get_event_loop()
        else:
            loop = windows.get_event_loop()

    return loop


async def cancel_tasks(tasks: Union[Dict[str, asyncio.Task], Set[asyncio.Task]]):
    """Cancels asyncio tasks.

    Args:
        tasks: If a Dict[str, asyncio.Task], contains (task_name, task) as entries.
               If a Set[asyncio.Task], contains a set of asyncio.Task objects.
    """
    if isinstance(tasks, dict):
        for name, task in list(tasks.items()):
            if task:
                await __cancel_task(task)
                logger.debug(f"{name} task stopped successfully")

    elif isinstance(tasks, set):
        for task in tasks:
            if task:
                await __cancel_task(task)
                logger.debug(f"Task stopped successfully")


async def __cancel_task(task):
    """Cancels a given asyncio task, suppressing CancelledError.

    Args:
        task (asyncio.Task): The asyncio task to be cancelled.
    """
    with suppress(asyncio.CancelledError):
        task.cancel()
        await task
