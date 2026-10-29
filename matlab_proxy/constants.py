# Copyright 2023-2026 The MathWorks, Inc.
from enum import IntEnum
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

# Authentication cookies expire one day after they are issued or renewed.
SESSION_COOKIE_MAX_AGE_SECONDS: Final[int] = 24 * 60 * 60
SESSION_COOKIE_RENEWAL_WINDOW_SECONDS: Final[int] = 60 * 60

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
    "R2025b",
    "R2026a",
    "R2026b",
]

# This constant when set to True restricts the number of active sessions to one
IS_CONCURRENCY_CHECK_ENABLED: Final[bool] = True
MWI_AUTH_TOKEN_NAME_FOR_HTTP = "mwi-auth-token"

# Interval in seconds to wait before querying the status of MATLAB.
CHECK_MATLAB_STATUS_INTERVAL_SECONDS: Final[int] = 1


class ExitReason(IntEnum):
    """Exit reasons for matlab-proxy with distinct exit codes.

    Codes 100+ are application-defined to avoid collision with standard Unix exit codes.
    Code 0 is retained for normal signal-based shutdown.
    Code 1 is used for unexpected errors to distinguish from intentional application exits.
    """

    NORMAL_SHUTDOWN = 0
    UNEXPECTED_ERROR = 1
    IDLE_TIMEOUT = 100
