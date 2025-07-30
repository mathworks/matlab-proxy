# Copyright 2023-2025 The MathWorks, Inc.
from typing import Final, List

"""This module defines project-level constants"""

CONNECTOR_SECUREPORT_FILENAME: Final[str] = "connector.securePort"
VERSION_INFO_FILE_NAME: Final[str] = "VersionInfo.xml"
MAX_HTTP_REQUEST_SIZE: Final[int] = 500_000_000  # 500MB
MAX_WEBSOCKET_MESSAGE_SIZE_IN_MB: Final[int] = 500_000_000  # 500MB
MATLAB_LOGS_FILE_NAME: Final[str] = "matlab_logs.txt"
USER_CODE_OUTPUT_FILE_NAME: Final[str] = "startup_code_output.txt"

# Max startup duration in seconds for processes launched by matlab-proxy
# This constant is meant for internal use within matlab-proxy
# Clients of this package should use settings.py::get_process_startup_timeout() function
DEFAULT_PROCESS_START_TIMEOUT: Final[int] = 600

SUPPORTED_MATLAB_VERSIONS: Final[List[str]] = [
    "R2020b",
    "R2021a",
    "R2021b",
    "R2022a",
    "R2022b",
    "R2023a",
    "R2023b",
    "R2024a",
    "R2024b",
    "R2025a",
]

# This constant when set to True restricts the number of active sessions to one
IS_CONCURRENCY_CHECK_ENABLED: Final[bool] = True
MWI_AUTH_TOKEN_NAME_FOR_HTTP = "mwi-auth-token"

# Interval in seconds to wait before querying the status of MATLAB.
CHECK_MATLAB_STATUS_INTERVAL_SECONDS: Final[int] = 1
