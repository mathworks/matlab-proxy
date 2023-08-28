# Copyright 2022-2023 The MathWorks, Inc.
import asyncio

from matlab_proxy import util
from matlab_proxy.util import mwi
from matlab_proxy.util.mwi import environment_variables as mwi_env


""" This file contains methods specific to non-posix / windows OS.
"""

logger = mwi.logger.get()


def get_event_loop():
    """Return the same ProactorEventLoop regardless of the python version.
    If there is no event loop running, will create a ProactorEventloop and set is as the
    event loop for the current process.

    Returns:
        loop: asyncio loop of type ProactorEventLoop.
    """
    # Different python versions return different event loops with varying capabilities.
    # Ex: Can't create a subprocesses if we use WindowsSelectorEventLoop for python < 3.7
    loop = asyncio.get_event_loop()

    if not isinstance(loop, asyncio.windows_events.ProactorEventLoop):
        loop = asyncio.ProactorEventLoop()
        asyncio.set_event_loop(loop)

    return loop


async def start_matlab(matlab_cmd, matlab_env):
    """Start the MATLAB process in windows. Returns the actual MATLAB process from the intermediate process.

    Args:
        matlab_cmd (List): Command to launch the MATLAB process.
        matlab_env (dict): Dictionary of environment variables to be passed to the MATLAB process.

    Raises:
        AssertionError: When assertions are not met.

    Returns:
        psutil.Process(): The MATLAB process object.
    """
    import psutil

    intermediate_proc = await asyncio.create_subprocess_exec(
        *matlab_cmd,
        env=matlab_env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )

    # In testing mode, the devel.py file is run, which is the fake MATLAB server.
    # So, there is no need to check for an intermediate process when testing and can return
    # the same process as a psutil.Process() object.
    if mwi_env.is_testing_mode_enabled() or mwi_env.is_development_mode_enabled():
        proc = psutil.Process(intermediate_proc.pid)

        return proc

    matlab = None

    try:
        children = util.get_child_processes(intermediate_proc)

        # Ensure that only 1 child process has been created.
        assert (
            len(children) == 1
        ), "Multiple child processes were created. Was expecting only 1."

        # Check if the name of the process is MATLAB.exe
        matlab = children[0]
        assert (
            "MATLAB.exe" == matlab.name()
        ), "Expecting the child process name to be MATLAB.exe"

    except AssertionError as err:
        raise err
    except psutil.NoSuchProcess:
        # We reach here when the intermediate process launched by matlab-proxy died
        # before we can query for its child processes. Hence, to find the actual MATLAB
        # process, we check all the processes name and parent process id. Ideally, this
        # approach should work in all cases unless MATLAB itself has exited / crashed.
        logger.debug(
            "Intermediate process not found. Querying all process to find MATLAB"
        )
        for process in psutil.process_iter():
            if (
                process.name() == "MATLAB.exe"
                and process.ppid() == intermediate_proc.pid
            ):
                matlab = process
                break

    assert matlab != None, "MATLAB Process ID not found"

    # Return the actual MATLAB processes
    return matlab
