# Copyright 2020-2025 The MathWorks, Inc.
"""This file lists and exposes the environment variables which are used by proxy manager."""

import os


def _is_env_set_to_true(env_name: str) -> bool:
    """Helper function that returns True if the environment variable specified is set to True.

    Args:
        env_name (str): Name of the environment variable to check the state for.

    Returns:
        bool: True if the environment variable's value matches(case-insensitive) the string "True"
    """
    return os.environ.get(env_name, "").lower() == "true"


def get_env_name_logging_level():
    """Specifies the logging level used by app's loggers"""
    return "MWI_MPM_LOG_LEVEL"


def get_env_name_enable_web_logging():
    """Enable the logging of asyncio web traffic by setting to true"""
    return "MWI_MPM_ENABLE_WEB_LOGGING"


def get_env_name_mwi_mpm_auth_token():
    """Authentication environment variable for authenticating with proxy manager"""
    return "MWI_MPM_AUTH_TOKEN"


def get_env_name_mwi_mpm_port():
    """Used to specify the port on which to start proxy manager"""
    return "MWI_MPM_PORT"


def get_env_name_mwi_mpm_parent_pid():
    """Used to specify the parent pid for the proxy manager process"""
    return "MWI_MPM_PARENT_PID"


def get_env_name_base_url_prefix():
    """Used to specify the base url prefix for setting base url on matlab (e.g. Jupyter base url)"""
    return "MWI_MPM_BASE_URL_PREFIX"


def is_web_logging_enabled():
    """Returns true if the web logging is required to be enabled"""
    return _is_env_set_to_true(get_env_name_enable_web_logging())
