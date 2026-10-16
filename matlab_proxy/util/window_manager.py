# Copyright 2026 The MathWorks, Inc.
"""Starts a supported window manager on Linux (used only for Simulink Online)."""

import asyncio
import os
import shutil
from typing import Final, List, NamedTuple

from matlab_proxy.util import mwi, system
from matlab_proxy.util.mwi.exceptions import WindowManagerError

logger = mwi.logger.get()


class _WindowManager(NamedTuple):
    name: str  # binary name; also the PATH-lookup key
    command: List[str]  # launch command (binary name + any WM-specific arguments)


# Supported window managers, in order of preference. openbox is preferred as it is
# packaged across Linux distributions (including arm64 RHEL-family images); fluxbox
# is retained as a fallback so existing deployments keep working. To support another
# window manager, append an entry here. --sm-disable stops openbox from contacting a
# session manager, which is meaningless in the disposable Xvfb session we run.
_SUPPORTED_WINDOW_MANAGERS: Final[List[_WindowManager]] = [
    _WindowManager("openbox", ["openbox", "--sm-disable"]),
    _WindowManager("fluxbox", ["fluxbox", "-screen", "0", "-log", "/dev/null"]),
]


async def start(display):
    """Starts the first supported window manager found on PATH against `display`.

    Window managers are only used for Simulink Online, a Linux-only concern, so this
    must only be invoked on Linux.

    Returns the launched process, or None if no display was given or no supported
    window manager is installed. Raises WindowManagerError if a window manager is
    found but fails to launch.
    """
    assert system.is_linux(), "window_manager.start() is only meaningful on Linux"

    if display is None:
        logger.warning("No DISPLAY set. Unable to start window manager.")
        return None

    wm = next((w for w in _SUPPORTED_WINDOW_MANAGERS if shutil.which(w.name)), None)
    if wm is None:
        logger.warning(
            "To use Simulink Online, you must install the window manager openbox on the system PATH, then restart matlab-proxy. For instructions, see https://github.com/mathworks/matlab-proxy#requirements.."
        )
        return None

    env = {k: v for k, v in os.environ.copy().items() if not k.startswith("MWI_")}
    env["DISPLAY"] = display
    logger.info(f"Starting the {wm.name} window manager with DISPLAY={display}")

    try:
        # Discard the WM's stdout/stderr: window managers emit benign startup chatter
        # (e.g. openbox's "Xinerama/XRandR extension is not present" note under Xvfb)
        # that would clutter the console. Spawn failures still surface below.
        return await asyncio.create_subprocess_exec(
            *wm.command,
            close_fds=False,
            env=env,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
    except Exception as err:
        raise WindowManagerError(
            f"Unable to start the {wm.name} window manager due to the following error: {err}"
        ) from err
