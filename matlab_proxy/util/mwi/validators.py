# Copyright (c) 2020-2022 The MathWorks, Inc.
"""This file contains validators for various runtime artefacts.
A validator is defined as a function which verifies the input and 
returns it unchanged if validation passes. 
Returning inputs allows validators to be used inline with the input.

Example: 
Original code: if( input ):
With validator: if (valid(input)):

Exceptions are thrown to signal failure.
"""
import errno
import os
import socket
import sys

import pkg_resources

import matlab_proxy

from . import environment_variables as mwi_env
from matlab_proxy.util import system
from . import logger as mwi_logger

logger = mwi_logger.get()


def validate_mlm_license_file(nlm_connections_str):
    """Validates and returns input if it passes validation.
    Throws exception when validation fails.
    The connection string should be in the form of port@hostname
    OR path to valid license file

    Args:
        nlm_conn_str (String): Contains the Network license manager connection string.

    Raises:
        NetworkLicensingError: A custom exception.

    Returns:
        String: Returns the same argument passed to this function if its valid.
    """

    """
     nlm_connections_str can either be a valid path to a file or a
     string with comma seperated values, each of the form port@hostname
    
    Some valid nlm_connections_str values are:
    1) port@hostname
    2) port@hostname,
    3) port1@hostname1,port2@hostname2
    4) port1@hostname1,port2@hostname2,
    5) port1@hostname1,port2@hostname2,port3@hostname3,
    """
    import re

    from .exceptions import NetworkLicensingError

    if nlm_connections_str is None:
        return None

    # Regular expression to match port@hostname,
    # where port is any number and hostname is alphanumeric
    # regex = Start of Line, Any number of 0-9 digits , @, any number of nonwhite space characters with "- _ ." allowed
    # "^[0-9]+[@](\w|\_|\-|\.)+$"
    # Server triad is of the form : port@host1 or port@host1,port@host2,port@host3
    nlm_connection_str_regex = "(^[0-9]+[@](\w|\_|\-|\.)+$)"
    error_message = (
        f"MLM_LICENSE_FILE validation failed for {nlm_connections_str}. "
        f"If set, the MLM_LICENSE_FILE environment variable must contain server names (each of the form port@hostname) separated by ':' on unix or ';' on windows(server triads however must be comma seperated)"
        f" OR path to a valid license file."
    )

    seperator = system.get_mlm_license_file_seperator()
    nlm_connection_strs = re.split(f"{seperator}|,", nlm_connections_str)

    logger.debug(
        "Validating individual parts of the environment variable MLM_LICENSE_FILE"
    )
    for nlm_connection_str in nlm_connection_strs:
        # Individual parts of the MLM_LICENSE_FILE can either be a valid path to a license file or a server name.

        if os.path.isfile(nlm_connection_str):
            logger.info(
                f"{nlm_connections_str} is a path to a file. MATLAB will attempt to use it."
            )

        else:
            match = re.search(nlm_connection_str_regex, nlm_connection_str)

            if match:
                logger.debug(f"Successfully validated {nlm_connection_str}")
            else:
                logger.error(f"Failed to validate:{nlm_connection_str}")
                logger.error(
                    "NLM_info is not of the form port@hostname or a valid path to a file"
                )
                raise NetworkLicensingError(error_message)

    return nlm_connections_str


def validate_app_port_is_free(port):
    """Validates and returns port if its free else will error out and exit.

    Args:
        port (str|int): Port number either as a string or an integer.

    Raises:
        e: socket.error

    Returns:
        Boolean: True if provided port is occupied else False.
    """
    # If port is None, at launch, site will use a randomnly allocated port.
    if port is None:
        logger.debug(
            f"Environment variable {mwi_env.get_env_name_app_port()} was not set. Will use a random port at launch."
        )
        return port

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("", int(port)))
        s.close()

        # Was able to allocate port. Validation passed.
        return port
    except socket.error as e:
        if e.errno == errno.EADDRINUSE:
            logger.error(
                f"The port {port} is not available. Please set another value for the environment variable {mwi_env.get_env_name_app_port()}"
            )
            sys.exit(1)
        else:
            raise e


def validate_base_url(base_url):
    """Validates base_url set in the env variable MWI_BASE_URL.

    If MWI_BASE_URL is empty, will use base_url="/"
    If MWI_BASE_URL doesnt have a prefix '/' will error out.
    If MWI_BASE_URL has a suffix '/', will remove it.

    Args:
        base_url (str | None): The base_url at which the integration will be launched.

    Returns:
        [str]: Validated base_url
    """
    validated_base_url = ""
    if base_url == "":
        validated_base_url = ""

    else:
        if not base_url.startswith("/"):
            logger.error(
                f'The value of environment variable {mwi_env.get_env_name_base_url()} must start with "/" '
            )
            sys.exit(1)

        validated_base_url = base_url[:-1] if base_url.endswith("/") else base_url

    return validated_base_url


def validate_env_config(config):
    """Validates config passed with available "matlab_proxy_configs" entry point in the same
    python environment. Computes DDUX value for MATLAB use.

    Args:
        config (str): Name of the configuration to use.

    Returns:
        Dict: Containing data specific to the environment in which MATLAB proxy is being used in.
    """
    available_configs = __get_configs()
    config = config.lower()

    # Check if supplied config is present in the available configs
    if config in available_configs:
        # Check if all keys are present in the supplied config
        default_config_keys = available_configs[
            matlab_proxy.get_default_config_name()
        ].keys()
        env_config = available_configs[config]

        for key in default_config_keys:
            if not key in env_config:
                logger.error(f"{key} missing in the provided {config} configuration")
                sys.exit(1)

        logger.debug(f"Successfully validated provided {config} configuration")
        return env_config

    else:
        logger.error(
            f"{config} is not a valid config. Available configs are : {list(available_configs.keys())}"
        )
        sys.exit(1)


def __get_configs():
    """Iterates over the 'entry_points' of the installed packages in the current python
    environment and loads the 'matlab_proxy_configs' entry point values into the 'configs' Dict.

    Returns:
        Dict: Contains all the values present in 'matlab_web_desktop_configs' entry_point from all the packages
        installed in the current environment.
    """
    configs = {}
    for entry_point in pkg_resources.iter_entry_points(
        matlab_proxy.get_entrypoint_name()
    ):
        configs[entry_point.name.lower()] = entry_point.load()

    return configs


def validate_ssl_cert_file(a_ssl_cert_file):
    """Ensures that its a valid readable file"""

    # Empty strings are valid inputs
    if a_ssl_cert_file:
        # String is not empty, check to see if the file exists
        if not os.path.isfile(a_ssl_cert_file):
            logger.error(f"MWI_SSL_CERT_FILE is not a valid file: {a_ssl_cert_file}")
            sys.exit(1)

    # string is either empty, or is a valid file on disk
    return a_ssl_cert_file


def validate_ssl_key_and_cert_file(a_ssl_key_file, a_ssl_cert_file):
    """Ensures that its a valid readable file"""

    if a_ssl_cert_file is None and a_ssl_key_file is None:
        # Both values are None, this is acceptable.
        return a_ssl_key_file, a_ssl_cert_file

    # Implies atleast one value is not None.

    # Cert file is either empty or valid file.
    cert_file = validate_ssl_cert_file(a_ssl_cert_file=a_ssl_cert_file)

    if cert_file is None and a_ssl_key_file is not None:
        logger.error(f"MWI_SSL_CERT_FILE must be provided to use the MWI_SSL_KEY_FILE")
        sys.exit(1)

    if a_ssl_key_file is None and cert_file is not None:
        logger.info(
            f"MWI_SSL_KEY_FILE is not provided, ensure that your MWI_SSL_CERT_FILE : '{cert_file}' contains a private key"
        )

    if a_ssl_key_file:
        if not os.path.isfile(a_ssl_key_file):
            logger.error(f"MWI_SSL_KEY_FILE is not a valid file: {a_ssl_key_file}")
            sys.exit(1)

    logger.info(
        f"SSL Keys provided were: MWI_SSL_CERT_FILE: {a_ssl_cert_file} & MWI_SSL_KEY_FILE: {a_ssl_key_file}"
    )
    return a_ssl_key_file, a_ssl_cert_file
