# Copyright 2023 The MathWorks, Inc.
from typing import Final

"""This module defines project-level constants"""

CONNECTOR_SECUREPORT_FILENAME: Final[str] = "connector.securePort"
VERSION_INFO_FILE_NAME: Final[str] = "VersionInfo.xml"
MAX_HTTP_REQUEST_SIZE: Final[int] = 500_000_000  # 500MB
MATLAB_LOGS_FILE_NAME: Final[str] = "matlab_logs.txt"

# Max startup duration in seconds for processes launched by matlab-proxy
# This constant is meant for internal use within matlab-proxy
# Clients of this package should use settings.py::get_process_startup_timeout() function
DEFAULT_PROCESS_START_TIMEOUT: Final[int] = 600
