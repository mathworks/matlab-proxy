# Copyright (c) 2023 The MathWorks, Inc.

"""This module defines project-level constants"""

CONNECTOR_SECUREPORT_FILENAME = "connector.securePort"
VERSION_INFO_FILE_NAME = "VersionInfo.xml"
MAX_HTTP_REQUEST_SIZE = 500_000_000  # 500MB

# Max startup duration in seconds for processes launched by matlab-proxy
# This constant is meant for internal use within matlab-proxy
# Clients of this package should use settings.py::get_process_startup_timeout() function
DEFAULT_PROCESS_START_TIMEOUT = 120
