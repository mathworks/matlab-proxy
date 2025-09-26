# Copyright 2020-2025 The MathWorks, Inc.
"""Functions to access & control the logging behavior of the app"""

from . import environment_variables as mwi_env

from pathlib import Path
from rich.console import Console
from rich.table import Table
import logging
import os
import sys
import time

logging.getLogger("aiohttp_session").setLevel(logging.ERROR)


def get(init=False):
    """Get the logger used by this application.
        Set init=True to initialize the logger
    Returns:
        Logger: The logger used by this application.
    """
    if init is True:
        return __set_logging_configuration()

    return __get_mw_logger()


def __get_mw_logger_name():
    """Name of logger used by the app

    Returns:
        String: The name of the Logger.
    """
    return "MATLABProxyApp"


def __get_mw_logger():
    """Returns logger for use in this app.

    Returns:
        Logger: A logger object
    """
    return logging.getLogger(__get_mw_logger_name())


def __set_logging_configuration():
    """Sets the logging environment for the app

    Returns:
        Logger: Logger object with the set configuration.
    """
    # Create the Logger for MATLABProxy
    logger = __get_mw_logger()

    # log_level is either set by environment or is the default value.
    log_level = os.getenv(
        mwi_env.get_env_name_logging_level(), __get_default_log_level()
    ).upper()

    if __is_not_valid_log_level(log_level):
        default_log_level = __get_default_log_level()
        logging.warning(
            f"Unknown log level '{log_level}' set. Defaulting to log level '{default_log_level}'..."
        )
        log_level = default_log_level

    ## Set logging object
    if mwi_env.Experimental.use_rich_logger():
        from rich.logging import RichHandler

        rich_handler = RichHandler(
            keywords=[__get_mw_logger_name()],
        )
        rich_handler.setFormatter(logging.Formatter("%(name)s %(message)s"))
        logger.addHandler(rich_handler)
    else:
        colored_formatter = _ColoredFormatter(
            "%(color)s[%(levelname)1.1s %(asctime)s %(name)s]%(end_color)s %(message)s"
        )
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(colored_formatter)
        logger.addHandler(stream_handler)

    logger.setLevel(log_level)

    log_file = os.getenv(mwi_env.get_env_name_log_file(), None)
    if log_file:
        try:
            log_file = Path(log_file)
            # Need to create the file if it doesn't exist or else logging.FileHandler
            # would open it in 'write' mode instead of 'append' mode.
            log_file.touch(exist_ok=True)
            logger.info(f"Initializing logger with log file:{log_file}")
            file_handler = logging.FileHandler(filename=log_file, mode="a")
            formatter = logging.Formatter(
                fmt="[%(levelname)s %(asctime)s %(name)s] %(message)s"
            )
            file_handler.setFormatter(formatter)
            file_handler.setLevel(log_level)
            logger.addHandler(file_handler)

        except PermissionError:
            print(
                f"PermissionError: Permission denied to create log file at: {log_file}"
            )
            sys.exit(1)

        except Exception as err:
            print(f"Failed to use log file: {log_file} with error: {err}")
            sys.exit(1)

    return logger


def get_environment_variable_names():
    """Helper to return names of environment variables queried.

    Returns:
        tuple: name of environment variable to control log level,
                name of environment variable to control logging to file
    """
    __log_file_environment_variable_name = mwi_env.get_env_name_log_file()
    __log_level_environment_variable_name = mwi_env.get_env_name_logging_level()
    return __log_level_environment_variable_name, __log_file_environment_variable_name


def __get_default_log_level():
    """The default logging level used by this application.

    Returns:
        String: The default logging level
    """
    return "INFO"


def __is_not_valid_log_level(log_level):
    """Helper to check if the log level is valid.

    Returns:
        Boolean: Whether log level  exists
    """

    return log_level not in logging.getLevelNamesMapping().keys()


def log_startup_info(title=None, matlab_url=None):
    """Logs the startup information to the console and log file if specified."""
    logger = __get_mw_logger()
    print_as_table = False
    header_info = "Access MATLAB at:"

    if sys.stdout.isatty():
        # Width cannot be determined in non-interactive sessions
        console = Console()
        # Number of additional characters used by the table
        padding = 4
        print_as_table = len(matlab_url) + padding <= console.width

    if print_as_table:
        table = Table(
            caption=title,
            show_header=False,
            show_lines=True,
            show_edge=True,
            highlight=True,
            expand=True,
        )
        table.add_column(overflow="fold", style="bold green", justify="center")
        table.add_row(header_info)
        table.add_row(matlab_url)
        console.print(table)

    if os.getenv(mwi_env.get_env_name_log_file(), None) or not print_as_table:
        logger.critical(f"{header_info} {matlab_url}")


class _ColoredFormatter(logging.Formatter):
    """Custom formatter to add colors based on log level and modify time format."""

    def format(self, record):
        # Example: Add 'color' and 'end_color' attributes based on log level
        if record.levelno == logging.INFO:
            record.color = "\033[32m"  # Green
            record.end_color = "\033[0m"
        elif record.levelno == logging.DEBUG:
            record.color = "\033[94m"  # Blue
            record.end_color = "\033[0m"
        elif record.levelno == logging.WARNING:
            record.color = "\033[93m"  # Yellow
            record.end_color = "\033[0m"
        elif record.levelno == logging.ERROR:
            record.color = "\033[91m"  # Red
            record.end_color = "\033[0m"
        elif record.levelno == logging.CRITICAL:
            record.color = "\033[35m"  # Magenta
            record.end_color = "\033[0m"
        else:
            record.color = ""
            record.end_color = ""

        # Call the original format method
        return super().format(record)

    def formatTime(self, record, datefmt=None):
        # Default behavior of formatTime
        ct = self.converter(record.created)
        if datefmt:
            s = time.strftime(datefmt, ct)
        else:
            t = time.strftime("%Y-%m-%d %H:%M:%S", ct)
            s = "%s,%03d" % (t, record.msecs)

        # Replace the comma with a period
        return s.replace(",", ".")
