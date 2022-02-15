# Copyright 2020 The MathWorks, Inc.
import signal
import socket
import sys
import argparse
import os
import matlab_proxy
from aiohttp import web
from matlab_proxy import mwi_environment_variables as mwi_env
from matlab_proxy.util import mwi_logger

logger = mwi_logger.get()


def is_python_version_newer_than_3_6():
    """Returns True if the python version being used is 3.7 or higher, else False.

    Returns:
        Boolean: True if python version >= 3.7, False otherwise.
    """
    return sys.version_info[:2] >= (3, 7)


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


def __get_supported_termination_signals():
    """Returns supported set handlers for asynchronous events.

    Returns:
        List: Containing supported set handlers.
    """
    return [signal.SIGHUP, signal.SIGINT, signal.SIGQUIT, signal.SIGTERM]


def add_signal_handlers(loop):
    """Adds signal handlers to event loop.
    This is necessary to shutdown the server safely when an interrupt is raised.

    Args:
        loop (loop): Asyncio event loop

    Returns:
        loop: Asyncio event loop with signal handlers added.
    """
    for signal in __get_supported_termination_signals():
        logger.debug(f"Registering handler for signal: {signal} ")
        loop.add_signal_handler(signal, lambda: loop.stop())

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
