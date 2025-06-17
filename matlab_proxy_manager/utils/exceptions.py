# Copyright 2025 The MathWorks, Inc.


class MATLABProxyError(Exception):
    """Base class for all MATLAB Proxy Manager exceptions."""

    pass


class ProcessStartError(MATLABProxyError):
    """Exception thrown when MATLAB proxy process fails to start."""

    def __init__(
        self, message="Failed to create matlab-proxy subprocess.", extra_info=None
    ):
        self.message = message
        self.extra_info = extra_info
        super().__init__(message)

    def __str__(self):
        return (
            f"{self.message} Additional info: {self.extra_info}"
            if self.extra_info
            else self.message
        )


class ServerReadinessError(MATLABProxyError):
    """Exception thrown when MATLAB proxy server fails to become ready"""

    def __init__(
        self,
        message="MATLAB Proxy Server unavailable: matlab-proxy-app failed to start or has timed out.",
        extra_info=None,
    ):
        self.message = message
        self.extra_info = extra_info
        super().__init__(message)

    def __str__(self):
        return (
            f"{self.message} Additional info: {self.extra_info}"
            if self.extra_info
            else self.message
        )
