# Copyright 2025 The MathWorks, Inc.
"""This file provides functions to set a session name for the MATLAB Proxy instance."""

import os
from matlab_proxy.util.mwi import environment_variables as mwi_env
from matlab_proxy.util.mwi import logger as mwi_logger

logger = mwi_logger.get()


def _get_session_name():
    """Get the session name for the MATLAB Proxy instance.

    Returns:
        str: returns the user-defined session name if set, otherwise returns None.
    """
    return os.getenv(mwi_env.get_env_name_session_name(), None)


def get_browser_title(matlab_version) -> str:
    """Get the browser title for the MATLAB Proxy instance."""

    browser_title = "MATLAB " + (matlab_version or "")
    session_name = _get_session_name()
    if session_name:
        browser_title = session_name + " - " + browser_title
        logger.info("Session Name set to : %s", session_name)
    return browser_title
