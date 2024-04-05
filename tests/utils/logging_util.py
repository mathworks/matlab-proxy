# Copyright 2024 The MathWorks, Inc.

import logging
from pathlib import Path
from os import getenv


def create_integ_test_logger(
    log_name,
    log_level=getenv("MWI_TEST_LOG_LEVEL", "WARNING"),
    log_file_path=getenv("MWI_INTEG_TESTS_LOG_FILE_PATH"),
):
    return create_test_logger(
        log_name, log_level, log_file_path, output_prefix="INTEG TEST"
    )


def create_unit_test_logger(
    log_name,
    log_level=getenv("MWI_TEST_LOG_LEVEL", "WARNING"),
    log_file_path=getenv("MWI_UNIT_TESTS_LOG_FILE_PATH"),
):
    return create_test_logger(
        log_name, log_level, log_file_path, output_prefix="UNIT TEST"
    )


def create_test_logger(
    log_name,
    log_level=getenv("MWI_TEST_LOG_LEVEL", "WARNING"),
    log_file_path=None,
    output_prefix="TEST",
):
    """
    Returns a logger with specified name and level

    Args:
        log_file_path (string): Log file path to which the logs should be written
        log_level (logger level attribute): Log level to be set for the logger
        log_name (string): Name of the logger to be used
    """

    # Create a logger with the name 'TEST'
    logger = logging.getLogger(output_prefix + " - " + log_name)

    # Create a formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Set the logging level (e.g., DEBUG, INFO, WARNING, ERROR, CRITICAL)
    logger.setLevel(log_level)

    if log_file_path:
        file_path = Path(log_file_path)

        # Create a file handler
        file_handler = logging.FileHandler(filename=file_path, mode="a")

        # Set a logging level for the file
        file_handler.setLevel(log_level)

        # Set the formatter for the console handler
        file_handler.setFormatter(formatter)

        # Add the console handler to the logger
        logger.addHandler(file_handler)

    # Create a console handler
    console_handler = logging.StreamHandler()

    # Set a logging level for the console handler
    console_handler.setLevel(log_level)

    # Set the formatter for the console handler
    console_handler.setFormatter(formatter)

    # Add the console handler to the logger
    logger.addHandler(console_handler)

    return logger
