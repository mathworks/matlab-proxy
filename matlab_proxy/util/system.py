# Copyright 2022 The MathWorks, Inc.
import os
import platform
import signal

"""Contains methods and helpers which return OS specific information 
"""


def is_posix():
    """Returns true for posix systems

    Returns:
        bool: True if OS is a posix system.
    """
    return os.name == "posix"


def get_os():
    """Returns the current operating system

    Returns:
        str: the current operating system
    """
    return platform.system()


def is_windows():
    """Returns True if current operating system is Windows.

    Returns:
        bool: True if current operating system is Windows else False
    """
    return True if platform.system() == "Windows" else False


def is_linux():
    """Returns True if current operating system is Linux.

    Returns:
        bool: True if current operating system is Linux else False
    """
    return True if platform.system() == "Linux" else False


def is_mac():
    """Returns True if current operating system is MacOS.

    Returns:
        bool: True if current operating system is MacOS else False
    """
    return True if platform.system() == "Darwin" else False


def get_supported_termination_signals():
    """Returns OS specific interrupt signals

    Returns:
        list: containing supported interrupt signals.
    """
    return (
        [signal.SIGHUP, signal.SIGINT, signal.SIGQUIT, signal.SIGTERM]
        if is_posix()
        else [signal.SIGINT, signal.SIGTERM]
    )


def get_mlm_license_file_seperator():
    """Returns OS specific seperator for MLM_LICENSE_FILE environment variable

    Returns:
        str: OS specific seperator for MLM_LICENSE_FILE
    """
    return ":" if is_posix() else ";"
