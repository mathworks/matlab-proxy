# Copyright 2026 The MathWorks, Inc.
"""Starts an Xvfb virtual display on Linux (gives MATLAB a display for graphics)."""

import asyncio
import os
import select
import shutil

from matlab_proxy.settings import get_process_startup_timeout
from matlab_proxy.util import mwi, system
from matlab_proxy.util.mwi.exceptions import XvfbError

logger = mwi.logger.get()

# Shown (logged and surfaced in the UI) when Xvfb is not installed. MATLAB still
# runs, but without a virtual display graphical features are unavailable.
XVFB_NOT_AVAILABLE_WARNING = (
    "Unable to find Xvfb on the system PATH. To enable graphics such as "
    "plots and figures in the MATLAB desktop, you must add Xvfb to the system "
    "PATH and restart matlab-proxy.\nFor instructions, see "
    "https://github.com/mathworks/matlab-proxy#requirements."
)


def is_available() -> bool:
    """Returns True if Xvfb is on the system PATH."""
    return shutil.which("Xvfb") is not None


async def start():
    """Starts an Xvfb virtual display and returns (process, display).

    Xvfb is only used on Linux, so this must only be invoked on Linux.

    Returns:
        tuple[process, str] | None: The launched Xvfb process and its display (e.g.
        ":2") on success, or None if Xvfb is not installed -- in which case MATLAB
        runs without a virtual display.

    Raises:
        XvfbError: If Xvfb is installed but fails to start.
    """
    assert system.is_linux(), "xvfb.start() is only meaningful on Linux"

    if not is_available():
        # The user-facing warning (with install guidance) is surfaced once at
        # startup; here we just note why no display is being created.
        logger.info(
            "Xvfb is not available on the system PATH; starting MATLAB without a virtual display."
        )
        return None

    xvfb_cmd, dpipe = _create_xvfb_cmd()
    # Do not leak matlab-proxy's own MWI_-prefixed configuration into Xvfb.
    env = {k: v for k, v in os.environ.copy().items() if not k.startswith("MWI_")}

    try:
        xvfb, display_port = await _create_xvfb_process(xvfb_cmd, dpipe, env)
    # FileNotFoundError: Xvfb vanished from the PATH between the probe and launch.
    # XvfbError: Xvfb failed to report a display number within the startup timeout.
    except (FileNotFoundError, XvfbError) as err:
        raise XvfbError(
            "Unable to start the Xvfb process. Ensure Xvfb is installed and is available on the System Path. See https://github.com/mathworks/matlab-proxy#requirements for information on Xvfb"
        ) from err

    display = ":" + str(display_port)
    logger.info(f"Started Xvfb with PID={xvfb.pid} on DISPLAY={display}")
    return xvfb, display


def _create_xvfb_cmd():
    """Builds the Xvfb launch command and the pipe it writes its display number to.

    Returns:
        tuple[List, List]: The Xvfb command (with the pipe's write descriptor
        embedded via -displayfd) and the (read, write) descriptor pair.
    """
    # Using os.pipe() can lead to race conditions (ie. usage of same set of file
    # descriptors between 2 processes) when called in quick succession and also when
    # running tests. Using os.pipe2() with os.O_NONBLOCK avoids race conditions.
    dpipe = os.pipe2(os.O_NONBLOCK)

    # Allow child process to use the file descriptor created by parent.
    os.set_inheritable(dpipe[1], True)

    xvfb_cmd = [
        "Xvfb",
        "-displayfd",
        # Write descriptor
        str(dpipe[1]),
        "-screen",
        "0",
        "3840x2160x24",
        "-dpi",
        "100",
        "-extension",
        "RANDR",
    ]

    return xvfb_cmd, dpipe


async def _create_xvfb_process(xvfb_cmd, pipe, env):
    """Spawns Xvfb and reads back the display number it chose.

    The Xvfb process is run with '-displayfd' set, so Xvfb picks an available display
    number and writes it to the provided write descriptor (pipe[1]). We read it from
    the read descriptor, waiting at most the process startup timeout for it to appear.

    Args:
        xvfb_cmd (List): Command to run the Xvfb process.
        pipe (List): A (read, write) file descriptor pair.
        env (Dict): Environment variables for the Xvfb process.

    Returns:
        tuple: The Xvfb process object and the display number it started on.

    Raises:
        XvfbError: If Xvfb does not report a display number within the timeout.
    """
    # Pipe errors, if any, to the process object instead of stdout.
    xvfb = await asyncio.create_subprocess_exec(
        *xvfb_cmd, close_fds=False, env=env, stderr=asyncio.subprocess.PIPE
    )

    read_descriptor, write_descriptor = pipe
    number_of_bytes = 200

    logger.debug("Waiting for XVFB process to initialize and provide Display Number")

    # Wait for the timeout specified by matlab-proxy for launching processes.
    ready_descriptors, _, _ = select.select(
        [read_descriptor], [], [], get_process_startup_timeout()
    )

    if read_descriptor in ready_descriptors:
        logger.debug("Reading display number from the read descriptor.")
        line = os.read(read_descriptor, number_of_bytes).decode("utf-8")
        # Xvfb writes the display number with a trailing newline; strip it.
        display_port = line.strip()
    else:
        # Check for errors and raise exception.
        error = ""
        while not xvfb.stderr.at_eof():
            line = await xvfb.stderr.readline()
            error += line.decode("utf-8")

        await xvfb.wait()
        raise XvfbError(f"Unable to start the Xvfb process: \n {error}")

    # Close the read and write descriptors.
    os.close(read_descriptor)
    os.close(write_descriptor)

    return xvfb, display_port
