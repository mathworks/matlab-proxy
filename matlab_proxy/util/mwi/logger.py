# Copyright 2020-2024 The MathWorks, Inc.
"""Functions to access & control the logging behavior of the app"""

import logging
import os
import sys
from pathlib import Path

from . import environment_variables as mwi_env


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
    # query for user specified environment variables
    log_level = os.getenv(
        mwi_env.get_env_name_logging_level(), __get_default_log_level()
    ).upper()

    valid = __is_valid_log_level(log_level)

    if not valid:
        default_log_level = __get_default_log_level()
        logging.warn(
            f"Unknown log level '{log_level}' set. Defaulting to log level '{default_log_level}'..."
        )
        log_level = default_log_level

    log_file = os.getenv(mwi_env.get_env_name_log_file(), None)

    ## Set logging object
    logger = __get_mw_logger()
    try:
        if log_file:
            log_file = Path(log_file)
            # Need to create the file if it doesn't exist or else logging.FileHandler
            # would open it in 'write' mode instead of 'append' mode.
            log_file.touch(exist_ok=True)
            logger.info(f"Initializing logger with log file:{log_file}")
            file_handler = logging.FileHandler(filename=log_file, mode="a")
            formatter = logging.Formatter(
                fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            file_handler.setFormatter(formatter)
            file_handler.setLevel(log_level)
            logger.addHandler(file_handler)

    except PermissionError:
        print(f"PermissionError: Permission denied to create log file at: {log_file}")
        sys.exit(1)

    except Exception as err:
        print(f"Failed to use log file: {log_file} with error: {err}")
        sys.exit(1)

    # log_level is either set by environment or is the default value.
    logger.info(f"Initializing logger with log_level: {log_level}")
    logger.setLevel(log_level)

    # Allow other libraries used by this integration to
    # also print their logs at the specified level
    logging.basicConfig(level=log_level)

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


def __is_valid_log_level(log_level):
    """Helper to check if the log level is valid.

    Returns:
        Boolean: Whether log level  exists
    """

    return hasattr(logging, log_level)
