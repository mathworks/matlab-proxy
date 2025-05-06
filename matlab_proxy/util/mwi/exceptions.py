# Copyright 2020-2025 The MathWorks, Inc.


class AppError(Exception):
    """A Generic Parent class which inherits the Exception class.
    This class will be inherited by other classes representing specific exceptions.

    The Parameterized constructor stores the message, logs and stacktrace.

    Args:
        Exception : Python's inbuilt Exception Class.
    """

    def __init__(self, message, logs=None, stacktrace=None):
        self.message = message
        self.logs = logs
        self.stacktrace = stacktrace


class FatalError(AppError):
    """An error which indicates that matlab-proxy web server cannot be brought up.
    Args:
        AppError (Class): Parent Class containing attributes to store
        messages, logs and stacktrace.
    """

    pass


class UIVisibleFatalError(AppError):
    """A Class with inherits from the AppError class.
    This class is used to represent Fatal Errors which need to be propagated to the front end.

    Args:
        AppError (Class): Parent Class containing attributes to store
        messages, logs and stacktrace.
    """

    pass


class MatlabInstallError(UIVisibleFatalError):
    """A Class which inherits the AppError class.

    This class represents errors with MATLAB Installation.

    Args:
        AppError (Class): Parent Class containing attributes to store
        messages, logs and stacktrace.
    """

    pass


class LicensingError(AppError):
    """A Class which inherits the AppError class.

    This class represents any Licensing Errors (MHLM and NLM Licensing)

    Args:
        AppError (Class): Parent Class containing attributes to store
        messages, logs and stacktrace.
    """

    pass


class OnlineLicensingError(LicensingError):
    """A Class which inherits the Licensing class.

    This class represents any errors specific to MHLM Licensing.

    Args:
        LicensingError (Class): Parent Class representing Licensing Errors.
    """

    pass


class EntitlementError(OnlineLicensingError):
    """A Class which inherits the OnlineLicensingError class.

    This class represents errors with Entitilments in MHLM Licensing.

    Args:
        OnlineLicensingError  (Class): Parent Class representing errors specific to MHLM Licensing.
    """

    pass


class NetworkLicensingError(LicensingError):
    """A Class which inherits the Licensing class.

    This class represents errors specific to Network License Manager.

    Args:
        LicensingError (Class): Parent Class representing Licensing Errors.
    """

    pass


class NoAvailableNetworkLicensingError(NetworkLicensingError):
    """A Class which inherits the NetworkLicensingError class.

    This class represents errors specific to non-availability of Network License Manager.

    Args:
        NetworkLicensingError (Class): Parent Class representing errors specific to Network Licensing.
    """

    pass


class MatlabError(AppError):
    """A Class which inherits the AppError class.

    This class represents errors raised by MATLAB.

    Args:
        AppError (Class): Parent Class containing attributes to store
        messages, logs and stacktrace.
    """

    pass


class XvfbError(AppError):
    """A Class which inherits the AppError class.

    This class represents any errors raised by Xvfb process.

    Args:
        AppError (Class): Parent Class containing attributes to store
        messages, logs and stacktrace.
    """

    pass


class WindowManagerError(AppError):
    """A Class which inherits the AppError class.

    This class represents any errors raised when instantiating a Window Manager within the Xvfb DISPLAY.

    Args:
        AppError (Class): Parent Class containing attributes to store
        messages, logs and stacktrace.
    """

    pass


class EmbeddedConnectorError(MatlabError):
    """A Class which inherits the MatlabError class.

    This class represents errors raised when proxy fails to communicate with the Embedded Connector.

    Args:
        AppError (Class): Parent Class containing attributes to store
        messages, logs and stacktrace.
    """

    pass


class InvalidTokenError(AppError):
    """A Class which inherits the AppError class.

    This class represents token authentication errors.

    Args:
        AppError (Class): Parent Class containing attributes to store
        messages, logs and stacktrace.
    """

    pass


class LockAcquisitionError(Exception):
    """Exception raised when a lock is not properly acquired before modifying a variable.

    This error is thrown in scenarios where:
    1) A lock must be acquired before modifying a shared resource, but it wasn't.
    2) The lock for a shared resource was acquired by one function, but another function attempts to modify the resource without holding the lock.


    Args:
        Exception : Python's inbuilt Exception Class.
    """

    pass


def log_error(logger, err: Exception):
    """Logs any error to stdout.

    Args:
        logger (logging): A instance of the logging.getLogger()
        err (Class): An instance of one of the  Error classes as defined above.
        Example: OnlineLicensingError, EntitlementError
    """
    if isinstance(err, AppError):
        logs_str = ("\n" + "\n".join(err.logs)) if err.logs is not None else ""
        logger.error(
            err.message if err.message else "An Exception was raised:\n" + logs_str
        )
    else:
        logger.error(err)
