# Copyright 2020-2025 The MathWorks, Inc.
"""This file tests methods present in matlab_proxy/util/mwi_logger.py"""

import logging
import os
import pytest
from matlab_proxy.util.mwi import logger as mwi_logger


@pytest.fixture
def reset_logger_handlers():
    """Fixture to reset logger handlers after each test."""
    yield
    logger = mwi_logger.get()
    logger.handlers.clear()


def test_get():
    """This test checks if the get method returns a logger with expected name"""
    logger = mwi_logger.get()
    # Okay to use hidden API for testing only.
    assert logger.name == mwi_logger.__get_mw_logger_name()


def test_get_mw_logger_name():
    """Test to lock down the name of the logger used."""
    # Okay to use hidden API for testing only.
    assert "MATLABProxyApp" == mwi_logger.__get_mw_logger_name()


def test_get_with_no_environment_variables(monkeypatch, reset_logger_handlers):
    """This test checks if the get method returns a logger with default settings if no environment variable is set"""
    # Delete the environment variables if they do exist
    env_names_list = mwi_logger.get_environment_variable_names()
    monkeypatch.delenv(env_names_list[0], raising=False)
    monkeypatch.delenv(env_names_list[1], raising=False)

    logger = mwi_logger.get(init=True)
    assert logger.isEnabledFor(logging.INFO) == True
    assert len(logger.handlers) == 1


def test_get_with_environment_variables(monkeypatch, tmp_path, reset_logger_handlers):
    """This test checks if the get method returns a logger with the specified settings"""
    env_names_list = mwi_logger.get_environment_variable_names()
    monkeypatch.setenv(env_names_list[0], "CRITICAL")
    monkeypatch.setenv(env_names_list[1], str(tmp_path / "testing123.log"))

    logger = mwi_logger.get(init=True)

    # Verify that environment variable controlling level is respected
    assert logger.isEnabledFor(logging.CRITICAL) == True

    # Verify that environment variable setting the file is respected
    assert len(logger.handlers) == 2
    assert os.path.basename(logger.handlers[1].baseFilename) == "testing123.log"


@pytest.mark.parametrize(
    "log_level, expected_level",
    [
        ("DEBUG", logging.DEBUG),
        ("INFO", logging.INFO),
        ("WARNING", logging.WARNING),
        ("debug", logging.DEBUG),
        ("info", logging.INFO),
        ("warning", logging.WARNING),
    ],
)
def test_set_logging_configuration_known_logging_levels(
    monkeypatch, log_level, expected_level, reset_logger_handlers
):
    """This test checks if the logger is set with correct level for known log levels"""
    env_names_list = mwi_logger.get_environment_variable_names()
    monkeypatch.setenv(env_names_list[0], log_level)
    logger = mwi_logger.get(init=True)
    assert (
        logger.isEnabledFor(expected_level) == True
    ), f"Error in initialising the logger with {log_level}"


@pytest.mark.parametrize("log_level", ["ABC", "abc"])
def test_set_logging_configuration_unknown_logging_levels(
    monkeypatch, log_level, reset_logger_handlers
):
    """This test checks if the logger is set with INFO level for unknown log levels"""
    env_names_list = mwi_logger.get_environment_variable_names()
    monkeypatch.setenv(env_names_list[0], log_level)
    logger = mwi_logger.get(init=True)
    assert (
        logger.isEnabledFor(logging.INFO) == True
    ), "Error in initialising the default logger"
