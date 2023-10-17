# Copyright (c) 2020-2023 The MathWorks, Inc.
import argparse
import os
import socket

from pathlib import Path

import matlab_proxy
from matlab_proxy.util import mwi, system
from matlab_proxy.util.event_loop import *
from matlab_proxy.util.mwi import environment_variables as mwi_env

logger = mwi.logger.get()

# Global value to detect whether interrupt signal handler has been triggered or not.
interrupt_signal_caught = False


def parse_cli_args():
    """Parses CLI arguments passed to the main() function.

    Returns:
        dict: Containing the parsed arguments
    """
    # Parse the --config flag provided to the console script executable.
    parsed_args = {}
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        help="A json file which stores the config specific to the environment.",
        default=matlab_proxy.get_default_config_name(),
    )
    args = parser.parse_args()

    parsed_args["config"] = args.config

    return parsed_args


def prepare_site(app, runner):
    """Prepares to launch a TCPSite. If MWI_APP_PORT env variable is set,
    it will setup a site to launch on that port, else will launch on a random available port.

    Args:
        app (Application): An aiohttp.web.Application to launch a site.
        runner (AppRunner): An aiohhtp.web.Apprunner

    Returns:
        [TCPSite]: A TCPSite on which the integration will start.
    """
    from aiohttp import web

    port = app["settings"]["app_port"]
    # SSL_CONFIG validated and inserted in settings.py
    ssl_context = app["settings"]["ssl_context"]

    if port:
        logger.debug(f"Using {mwi_env.get_env_name_app_port()} to launch the server")
        site = web.TCPSite(
            runner,
            host=app["settings"]["host_interface"],
            port=port,
            ssl_context=ssl_context,
        )

    else:
        while True:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.bind(("", 0))
                p = s.getsockname()[1]
                s.close()
                logger.debug(f"Trying to launch the site on port {p}")
                site = web.TCPSite(
                    runner,
                    host=app["settings"]["host_interface"],
                    port=p,
                    ssl_context=ssl_context,
                )
                break
            except:
                logger.info(f"Failed to launch the site on port {p}")

    return site


def add_signal_handlers(loop):
    """Adds signal handlers to event loop.
    This is necessary to shutdown the server safely when an interrupt is raised.

    Args:
        loop (loop): Asyncio event loop

    Returns:
        loop: Asyncio event loop with signal handlers added.
    """

    def catch_interrupt_signal(*args):
        """Nested method which works as a interrupt signal handler.

        Raises:
            SystemExit: Raises SystemExit which will stop execution of loop.run_forever() in app.main()
        """
        logger.debug("Interrupt Signal handler called")

        # Only raise SystemExit when the handler is invoked for the first time.
        # Ignore subsequent handler invocations of interrupt signals. This is
        # required so that asyncio event loop gracefully cancels pending tasks
        # and exits.
        global interrupt_signal_caught
        if interrupt_signal_caught is False:
            interrupt_signal_caught = True
            raise SystemExit

        logger.debug("Interrupt is already being serviced.")

    for interrupt_signal in system.get_supported_termination_signals():
        logger.debug(f"Registering handler for signal: {interrupt_signal} ")

        if system.is_posix():
            loop.add_signal_handler(interrupt_signal, catch_interrupt_signal)
        else:
            # loop.add_signal_handler() is not yet supported in Windows.
            # Using the 'signal' package instead.
            import signal

            signal.signal(interrupt_signal, catch_interrupt_signal)

    return loop


def prettify(boundary_filler=" ", text_arr=[]):
    """Prettify array of strings with borders for stdout

    Args:
        boundary_filler (str, optional): Upper and lower border filler for text. Defaults to " ".
        text_arr (list, optional):The text array to prettify. Each element will be added to a newline. Defaults to [].

    Returns:
        [str]: Prettified String
    """

    import sys

    if not sys.stdout.isatty():
        return (
            "\n============================\n"
            + "\n".join(text_arr)
            + "\n============================\n"
        )

    size = os.get_terminal_size()
    cols, _ = size.columns, size.lines

    if any(len(text) > cols for text in text_arr):
        result = ""
        for text in text_arr:
            result += text + "\n"
        return result

    upper = "\n" + "".ljust(cols, boundary_filler) + "\n" if len(text_arr) > 0 else ""
    lower = "".ljust(cols, boundary_filler) if len(text_arr) > 0 else ""

    content = ""
    for text in text_arr:
        content += text.center(cols) + "\n"

    result = upper + content + lower

    return result


def get_child_processes(parent_process):
    """Get list of child processes from a parent process.

    Args:
        parent_process (asyncio.subprocess.Process): Parent Process

    Raises:
        err: Assertion Error when either Parent process is not running

    Returns:
        list: list of child processes of type psutil.Process()
    """
    import psutil

    # Work with psutil.Process() rather than asyncio.subprocess.Process()
    # to get hold child processes
    parent_process_psutil = psutil.Process(parent_process.pid)

    while True:
        try:
            # Before checking for any child processes, ensure that the parent process is running
            assert (
                parent_process_psutil.is_running()
            ), "Can't check for child processes as the parent process is no longer running."

            child_processes = parent_process_psutil.children(recursive=False)

            if not child_processes:
                logger.debug("Waiting for the child processes to be created...")
                continue

        except AssertionError as err:
            raise err

        if child_processes:
            break

    return child_processes


def get_access_url(app):
    """Returns the url at which the server will be accessible at

    Args:
        app (aiohttp.web.Application): The web application from aiottp package

    Returns:
        str: complete url at which the server will be accessible.
    """
    base_url = app["settings"]["base_url"]
    port = app["settings"]["app_port"]

    ssl_context = app["settings"]["ssl_context"]
    host_interface = app["settings"]["host_interface"]

    access_protocol = "https" if ssl_context else "http"

    # When host interface is set to 0.0.0.0, in a windows system, the server will not be accessible.
    # Setting the value to 127.0.0.1, will allow it be remotely and locally accessible.

    # NOTE: When windows container support is introduced this will need to be tweaked accordingly.
    if host_interface == "0.0.0.0" and system.is_windows():
        host_interface = "127.0.0.1"

    url = f"{access_protocol}://{host_interface}:{port}{base_url}"

    return url


def is_valid_path(path: Path):
    """Returns true if path supplied is a valid path to a file or directory

    Args:
        path (pathlib.Path): pathlib.Path object of a file or directory

    Returns:
        bool: True if a valid path is supplied else False
    """
    path = Path(path)
    return path.is_dir() or path.is_file()
