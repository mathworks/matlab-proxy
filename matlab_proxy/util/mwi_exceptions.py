# Copyright 2020-2021 The MathWorks, Inc.


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


class InternalError(AppError):
    """A Class which inherits the AppError class.
    This class represents any Internal Error within the App

    Args:
        AppError (Class): Parent Class containing attributes to store
        messages, logs and stacktrace.
    """

    pass


class MatlabInstallError(AppError):
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


def log_error(logger, err):
    """Logs any error to stdout.

    Args:
        logger (logging): A instance of the logging.getLogger()
        err (Class): An instance of one of the  Error classes as defined above.
        Example: OnlineLicensingError, EntitlementError
    """
    logs_str = ("\n" + "\n".join(err.logs)) if err.logs is not None else ""
    logger.error(err.message + logs_str)
