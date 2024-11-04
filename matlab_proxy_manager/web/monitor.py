# Copyright 2024 The MathWorks, Inc.
import asyncio

from matlab_proxy_manager.utils import logger
from matlab_proxy_manager.utils import helpers

log = logger.get()


class OrphanedProcessMonitor:
    """
    Class that provides behavior to track the idle state of the proxy manager app.
    It periodically checks if the parent process is alive and triggers a shutdown event if not.
    """

    def __init__(self, app, delay: int = 1) -> None:
        self.app = app
        self.delay = delay

    async def start(self) -> None:
        """
        Starts the monitoring process. Periodically checks if the parent process is alive.
        If the parent process is not alive, it triggers the shutdown process.
        """
        while True:
            try:
                if not helpers.does_process_exist(self.app.get("parent_pid")):
                    log.info("Parent doesn't exist, calling self-shutdown")
                    await self.shutdown()
                    break
            except Exception as ex:
                log.debug("Couldn't check for parent's liveness with err: %s", ex)
            await asyncio.sleep(self.delay)

    async def shutdown(self) -> None:
        """
        Triggers the shutdown process by setting the shutdown event.
        """

        try:
            # Set the shutdown async event to signal app shutdown to the app runner
            self.app.get("shutdown_event").set()
        except Exception as ex:
            log.debug("Unable to set proxy manager shutdown event, err: %s", ex)
