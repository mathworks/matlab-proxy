# Copyright 2020-2025 The MathWorks, Inc.
"""This file lists and exposes the environment variables which are used by the integration."""

import os


def _is_env_set_to_true(env_name: str) -> bool:
    """Helper function that returns True if the environment variable specified is set to True.

    Args:
        env_name (str): Name of the environment variable to check the state for.

    Returns:
        bool: True if the value of the environment variable is a case insensitive match to the string "True"
    """
    return os.environ.get(env_name, "false").lower() == "true"


def _is_env_set_to_false(env_name: str) -> bool:
    """Helper function that returns True if the environment variable specified is set to False.

    Args:
        env_name (str): Name of the environment variable to check the state for.

    Returns:
        bool: True if the value of the environment variable is a case insensitive match to the string "False"
    """
    return os.environ.get(env_name, "").lower() == "false"


def get_env_name_network_license_manager():
    """Specifies the path to valid license file or address of a network license server"""
    return "MLM_LICENSE_FILE"


def get_env_name_mhlm_context():
    """Specifies the context from which MHLM was initiated. Used by DDUX in MATLAB."""
    return "MHLM_CONTEXT"


def get_env_name_logging_level():
    """Specifies the logging level used by app's loggers"""
    return "MWI_LOG_LEVEL"


def get_env_name_enable_web_logging():
    """Enable the logging of asyncio web traffic by setting to true"""
    return "MWI_ENABLE_WEB_LOGGING"


def get_env_name_log_file():
    """Specifies a file into which logging content is directed"""
    return "MWI_LOG_FILE"


def get_env_name_base_url():
    """Specifies the base url on which the website should run.
    Eg: www.127.0.0.1:8888/base_url/index.html

    Note: The website runs on a URL of the form:
        www.<SERVER ADDRESS>:<PORT NUMBER>/<BASE_URL>/index.html

    Note: If you are updating this value, remember to update the startup.m file
            that is used to notify the connector of the base url.
    """
    return "MWI_BASE_URL"


def get_env_name_app_port():
    """Specifies the port on which the website is running on the server.
    Eg: www.127.0.0.1:PORT/index.html

    Note: The website runs on a URL of the form:
        www.<SERVER ADDRESS>:<PORT NUMBER>/<BASE_URL>/index.html
    """
    return "MWI_APP_PORT"


def get_env_name_custom_http_headers():
    """Specifies HTTP headers as JSON content, to be injected into responses sent to the browser"""
    return "MWI_CUSTOM_HTTP_HEADERS"


def get_env_name_app_host():
    """Specifies the host on which the TCP site (aiohttp server) is being run."""
    return "MWI_APP_HOST"


def get_env_name_testing():
    """Set to true when we are running tests in development mode."""
    return "MWI_TEST"


def get_env_name_development():
    """Set to true when we are in development mode."""
    return "MWI_DEV"


def get_env_name_matlab_tempdir():
    """The environment variables used to control the temp directory used by MATLAB on POSIX systems"""
    # Order matters, MATLAB checks TMPDIR first and then TMP
    return ["TMPDIR", "TMP"]


def is_development_mode_enabled():
    """Returns true if the app is in development mode."""
    return _is_env_set_to_true(get_env_name_development())


def is_testing_mode_enabled():
    """Returns true if the app is in testing mode."""
    return is_development_mode_enabled() and _is_env_set_to_true(get_env_name_testing())


def is_web_logging_enabled():
    """Returns true if the web logging is required to be enabled"""
    return _is_env_set_to_true(get_env_name_enable_web_logging())


def get_env_name_enable_ssl():
    """Returns the environment variable used for enabling/disabling SSL/TLS communication."""
    return "MWI_ENABLE_SSL"


def get_env_name_ssl_cert_file():
    """Specifies the certificate to be used by webserver."""
    return "MWI_SSL_CERT_FILE"


def get_env_name_ssl_key_file():
    """Specifies the key used by webserver to sign the ssl certificate."""
    return "MWI_SSL_KEY_FILE"


def get_env_name_enable_mwi_auth_token():
    """Specifies whether the server should provide Token-Based Authentication"""
    return "MWI_ENABLE_TOKEN_AUTH"


def get_env_name_mwi_auth_token():
    """User specified token for use with Token-Based Authentication"""
    return "MWI_AUTH_TOKEN"


def get_env_name_matlab_log_dir():
    """Returns the key used for MATLAB log dir env variable"""
    return "MATLAB_LOG_DIR"


def get_env_name_mwi_use_existing_license():
    """Returns the environment variable name used to instruct matlab-proxy to use an existing license. Usually used by already activated MATLAB installations."""
    return "MWI_USE_EXISTING_LICENSE"


def get_env_name_custom_matlab_root():
    """User specified path to MATLAB root"""
    return "MWI_CUSTOM_MATLAB_ROOT"


def get_env_name_process_startup_timeout():
    """User specified timeout in seconds for processes launched by matlab-proxy"""
    return "MWI_PROCESS_START_TIMEOUT"


def get_env_name_custom_matlab_code():
    """User specified MATLAB code that will be executed by matlab-proxy upon its start"""
    return "MWI_MATLAB_STARTUP_SCRIPT"


def get_env_name_shutdown_on_idle_timeout():
    """User specified timeout in minutes for shutdown on idle of matlab-proxy"""
    return "MWI_SHUTDOWN_ON_IDLE_TIMEOUT"


class Experimental:
    """This class houses functions which are undocumented APIs and Environment variables.
    Note: Never add any state to this class. Its only intended for use as an abstraction layer
    for functions which are not ready for prime time.
    """

    @staticmethod
    def get_env_name_enable_simulink():
        """Returns the environment variable name used to enable simulink support"""
        ##NOTE: Simulink Online is unavailable for general use as of R2023b.
        return "MWI_ENABLE_SIMULINK"

    @staticmethod
    def is_simulink_enabled():
        """Returns true if the simulink online is enabled."""
        return _is_env_set_to_true(Experimental.get_env_name_enable_simulink())

    @staticmethod
    def get_env_name_profile_matlab_startup():
        """Returns the environment variable name used to enable MPA support"""
        return "MWI_PROFILE_MATLAB_STARTUP"

    @staticmethod
    def is_matlab_startup_profiling_enabled():
        """Returns true if the startup profiling is enabled."""
        return _is_env_set_to_true(Experimental.get_env_name_profile_matlab_startup())

    @staticmethod
    def get_env_name_use_cookie_cache():
        """Returns the environment variable name used to enable cookie jar support for matlab-proxy"""
        return "MWI_USE_COOKIE_CACHE"

    @staticmethod
    def should_use_cookie_cache():
        """Returns true if the cookie jar support is enabled."""
        return _is_env_set_to_true(Experimental.get_env_name_use_cookie_cache())
