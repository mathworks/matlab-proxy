# Copyright 2020-2023 The MathWorks, Inc.

from pathlib import Path
import os
import shutil
import socket
import ssl
import tempfile
import uuid
import xml.etree.ElementTree as ET

import matlab_proxy
from matlab_proxy import constants
from matlab_proxy.util import mwi, system
from matlab_proxy.util.mwi import environment_variables as mwi_env
from matlab_proxy.util.mwi import token_auth
from matlab_proxy.util.mwi.exceptions import (
    FatalError,
    MatlabInstallError,
    UIVisibleFatalError,
)

logger = mwi.logger.get()


def get_process_startup_timeout():
    """Returns the timeout for a process launched by matlab-proxy as specified by MWI_PROCESS_START_TIMEOUT environment variable
    if valid, else returns the default value.

    Returns:
        int: timeout for a process launched by matlab-proxy
    """
    custom_startup_timeout = os.getenv(mwi_env.get_env_name_process_startup_timeout())

    if custom_startup_timeout:
        if custom_startup_timeout.isdigit():
            logger.info(
                f"Using custom process startup timeout {custom_startup_timeout} seconds"
            )
            return int(custom_startup_timeout)

        else:
            logger.warn(
                f"The value set for {mwi_env.get_env_name_process_startup_timeout()}:{custom_startup_timeout} is not a number. Using {constants.DEFAULT_PROCESS_START_TIMEOUT} as the default value"
            )
            return constants.DEFAULT_PROCESS_START_TIMEOUT

    logger.info(
        f"Using {constants.DEFAULT_PROCESS_START_TIMEOUT} seconds as the default timeout value"
    )

    return constants.DEFAULT_PROCESS_START_TIMEOUT


def get_matlab_executable_and_root_path():
    """Returns the path from the MWI_CUSTOM_MATLAB_ROOT environment variable if valid, else returns
    MATLAB root based on the matlab executable if found on the system path.

    Returns:
        pathlib.Path: pathlib.Path objects to MATLAB executable & MATLAB root.
    """

    # Use custom matlab root path if provided.
    custom_matlab_root_path = os.environ.get(mwi_env.get_env_name_custom_matlab_root())

    if custom_matlab_root_path:
        matlab_root_path = Path(custom_matlab_root_path)

        # Terminate process if invalid Custom Path was provided!
        mwi.validators.validate_matlab_root_path(
            matlab_root_path, is_custom_matlab_root=True
        )

        # Generate executable path from root path
        matlab_executable_path = matlab_root_path / "bin" / "matlab"
        if system.is_windows():
            matlab_executable_path = matlab_executable_path.with_suffix(".exe")

        logger.info(
            f"Using Custom MATLAB Executable: {matlab_executable_path} with Root: {matlab_root_path}"
        )
        return matlab_executable_path, matlab_root_path

    # Custom matlab root not specified, search for MATLAB on system path
    matlab_executable_path = shutil.which("matlab")

    if matlab_executable_path:
        matlab_root_path = Path(matlab_executable_path).resolve().parent.parent
        logger.info(f"Found MATLAB executable at: {matlab_executable_path}")
        matlab_root_path = mwi.validators.validate_matlab_root_path(
            matlab_root_path, is_custom_matlab_root=False
        )
        return matlab_executable_path, matlab_root_path

    # Control only gets here if custom matlab root was not set AND which matlab returned no results.
    # Note, error messages are formatted as multi-line strings and the front end displays them as is.
    error_message = "Unable to find MATLAB on the system PATH. Add MATLAB to the system PATH, and restart matlab-proxy."

    logger.info(error_message)
    raise MatlabInstallError(error_message)


def get_matlab_version(matlab_root_path):
    """Returns MATLAB version from VersionInfo.xml file present at matlab_root_path

    Args:
        matlab_root_path (pathlib.Path): pathlib.Path to MATLAB root.

    Returns:
        (str | None): Returns MATLAB version from VersionInfo.xml file.
    """
    if matlab_root_path is None:
        return None

    version_info_file_path = Path(matlab_root_path) / constants.VERSION_INFO_FILE_NAME
    if not version_info_file_path.exists():
        return None

    tree = ET.parse(version_info_file_path)
    root = tree.getroot()

    return root.find("release").text


def get_ws_env_settings():
    ws_env = (os.getenv("WS_ENV") or "").lower()
    ws_env_suffix = f"-{ws_env}" if "integ" in ws_env else ""

    return ws_env, ws_env_suffix


def get_mwi_config_folder(dev=False):
    if dev:
        return get_test_temp_dir()

    else:
        config_folder_path = Path.home() / ".matlab" / "MWI"
        # In multi-host environments, Path.home() can be the same for
        # multiple hosts and can cause issues when different hosts launch
        # matlab-proxy on the same port.
        # Using hostname to be part of the path of the config folder would avoid collisions.
        hostname = socket.gethostname()
        if hostname:
            config_folder_path = config_folder_path / "hosts" / hostname

        logger.debug(
            f"{'Hostname could not be determined. ' if not hostname else '' }Using the folder: {config_folder_path} for storing all matlab-proxy related session information"
        )

        return config_folder_path


def get_mwi_logs_root_dir(dev=False):
    return get_mwi_config_folder(dev) / "ports"


def get_dev_settings(config):
    devel_file = Path(__file__).resolve().parent / "./devel.py"
    mwi_config_folder = get_mwi_config_folder(dev=True)
    ws_env, ws_env_suffix = get_ws_env_settings()
    (
        mwi_auth_token,
        mwi_auth_token_hash,
    ) = token_auth.generate_mwi_auth_token_and_hash().values()
    return {
        "error": None,
        "matlab_path": Path(),
        "matlab_version": "R2020b",
        "matlab_cmd": [
            "python",
            "-u",
            str(devel_file),
            "matlab",
        ],
        "create_xvfb_cmd": create_xvfb_cmd,
        "base_url": os.environ.get(mwi_env.get_env_name_base_url(), ""),
        "app_port": os.environ.get(mwi_env.get_env_name_app_port(), 8000),
        "host_interface": os.environ.get(mwi_env.get_env_name_app_host(), "127.0.0.1"),
        "mwapikey": str(uuid.uuid4()),
        "matlab_protocol": "http",
        "matlab_display": ":1",
        "nlm_conn_str": os.environ.get(mwi_env.get_env_name_network_license_manager()),
        "matlab_config_file": mwi_config_folder / "proxy_app_config.json",
        "ws_env": ws_env,
        "mwa_api_endpoint": f"https://login{ws_env_suffix}.mathworks.com/authenticationws/service/v4",
        "mhlm_api_endpoint": f"https://licensing{ws_env_suffix}.mathworks.com/mls/service/v1/entitlement/list",
        "mwa_login": f"https://login{ws_env_suffix}.mathworks.com",
        "mwi_custom_http_headers": mwi.custom_http_headers.get(),
        "env_config": mwi.validators.validate_env_config(config),
        "ssl_context": None,
        "mwi_logs_root_dir": get_mwi_logs_root_dir(dev=True),
        "mw_context_tags": get_mw_context_tags(matlab_proxy.get_default_config_name()),
        "mwi_server_url": None,
        "mwi_is_token_auth_enabled": mwi_auth_token != None,
        "mwi_auth_status": False,
        "mwi_auth_token": mwi_auth_token,
        "mwi_auth_token_hash": mwi_auth_token_hash,
        "mwi_auth_token_name": mwi_env.get_env_name_mwi_auth_token().lower(),
        "mwi_use_existing_license": mwi.validators.validate_use_existing_licensing(
            os.getenv(mwi_env.get_env_name_mwi_use_existing_license(), "")
        ),
    }


def get(config_name=matlab_proxy.get_default_config_name(), dev=False):
    """Returns the settings specific to the environment in which the server is running in
    If the environment variable 'TEST' is set  to true, will make some changes to the dev settings.

    Args:
        config : Dictionary as specified by the default_configuration.py file. Used to customize the app.
        dev (bool, optional): development environment. Defaults to False.

    Returns:
        Dict: Containing data on how to start MATLAB among other information.

    Raises:
        Initialization of settings is not exception safe.
        Exceptions of Type UIVisibleFatalError are not propagated upwards, and are instead set in the error data member.
        This will allow for the app to error out gracefully in the front end as well.

        All other exceptions will propagate upwards and result in the app to shutdown.
    """

    if dev:
        settings = get_dev_settings(config_name)

        # If running tests using Pytest, it will set environment variable TEST to true before running tests.
        # Will make test env specific changes before returning the settings.
        if mwi_env.is_testing_mode_enabled():
            # Set ready_delay value to 0 for faster fake MATLAB startup.
            ready_delay = ["--ready-delay", "0"]
            matlab_cmd = settings["matlab_cmd"]
            matlab_cmd[4:4] = ready_delay
            settings["matlab_cmd"] = matlab_cmd

            # Randomly picks an available port and updates the value of settings['app_port'] .
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(("", 0))
            settings["app_port"] = s.getsockname()[1]
            s.close()

            # Set NLM Connection string. Server will start using this connection string for licensing
            settings["nlm_conn_str"] = "123@nlm"

    else:
        settings = {"error": None}

        # Initializing server settings separately allows us to return
        # a minimal set of settings required to launch the server even if
        # there is an exception thrown when creating the matlab specific settings.
        settings.update(get_server_settings(config_name))

        try:
            # Update settings with matlab specific values.
            settings.update(get_matlab_settings())
        except UIVisibleFatalError as error:
            logger.error(f"Exception raised during initialization: {error}")
            settings["error"] = error
            # Exceptions of this kind must propagate to the UI.
            # Returning settings that have been created without exceptions
            pass

    return settings


def get_server_settings(config_name):
    """Get the settings required to launch the MATLAB-PROXY web server.

    Args:
    config : Dictionary as specified by the default_configuration.py file. Used to customize the app.
    dev (bool, optional): development environment. Defaults to False.

    Raises:
    This function is not exception safe, and all exceptions will result in the termination of the app.
    If you need to add exceptions which need to be presented in the UI, add them to get_matlab_settings
    """
    (
        mwi_auth_token,
        mwi_auth_token_hash,
    ) = token_auth.generate_mwi_auth_token_and_hash().values()
    mwi_config_folder = get_mwi_config_folder()
    ssl_key_file, ssl_cert_file = mwi.validators.validate_ssl_key_and_cert_file(
        os.getenv(mwi_env.get_env_name_ssl_key_file(), None),
        os.getenv(mwi_env.get_env_name_ssl_cert_file(), None),
    )

    # log file validation check is already done in logger.py
    mwi_log_file = os.getenv(mwi_env.get_env_name_log_file(), None)

    return {
        "create_xvfb_cmd": create_xvfb_cmd,
        "base_url": mwi.validators.validate_base_url(
            os.getenv(mwi_env.get_env_name_base_url(), "")
        ),
        # Set default to host interface to 0.0.0.0
        "host_interface": os.environ.get(mwi_env.get_env_name_app_host(), "0.0.0.0"),
        # not_exception_safe, can_terminate_process by throwing FatalError
        "app_port": mwi.validators.validate_app_port_is_free(
            os.getenv(mwi_env.get_env_name_app_port())
        ),
        "env_config": mwi.validators.validate_env_config(config_name),
        "mwapikey": str(uuid.uuid4()),
        "matlab_protocol": "https",
        "matlab_config_file": mwi_config_folder / "proxy_app_config.json",
        "mwi_custom_http_headers": mwi.custom_http_headers.get(),
        # This directory will be used to store connector.securePort(matlab_ready_file) and its corresponding files. This will be
        # a central place to store logs of all the running instances of MATLAB launched by matlab-proxy
        "mwi_logs_root_dir": get_mwi_logs_root_dir(),
        "mwi_log_file": mwi_log_file,
        "mw_context_tags": get_mw_context_tags(config_name),
        # The url where the matlab-proxy server is accessible at
        "mwi_server_url": None,
        "mwi_is_token_auth_enabled": mwi_auth_token != None,
        "mwi_auth_status": False,
        "mwi_auth_token": mwi_auth_token,
        "mwi_auth_token_hash": mwi_auth_token_hash,
        "mwi_auth_token_name": mwi_env.get_env_name_mwi_auth_token().lower(),
        "mwi_use_existing_license": mwi.validators.validate_use_existing_licensing(
            os.getenv(mwi_env.get_env_name_mwi_use_existing_license(), "")
        ),
        "ssl_context": get_ssl_context(
            ssl_cert_file=ssl_cert_file, ssl_key_file=ssl_key_file
        ),
    }


def get_matlab_settings():
    """Returns the settings required to start MATLAB.

    Returns:
        Dict: Containing data on how to start MATLAB among other information.
    Raises:
    This function is not exception safe, and all exceptions will result in the termination of the app.
    Unless they are of type UIVisibleFatalError
    """

    matlab_executable_path, matlab_root_path = get_matlab_executable_and_root_path()

    ws_env, ws_env_suffix = get_ws_env_settings()

    # MATLAB Proxy gives precedence to the licensing information conveyed
    # by the user. If MLM_LICENSE_FILE is set, it should be prioritised over
    # other ways of licensing. But existence of license_info.xml in matlab/licenses
    # folder may cause hinderance in this workflow. So specifying -licmode as 'file'
    # overrides license_info.xml and enforces MLM_LICENSE_FILE to be the topmost priority

    # NLM Connection String provided by MLM_LICENSE_FILE environment variable
    nlm_conn_str = mwi.validators.validate_mlm_license_file(
        os.environ.get(mwi_env.get_env_name_network_license_manager())
    )
    matlab_lic_mode = ["-licmode", "file"] if nlm_conn_str else ""
    # flag to hide MATLAB Window
    flag_to_hide_desktop = (
        ["-noDisplayDesktop", "-wait", "-log"]
        if system.is_windows()
        else ["-nodesktop"]
    )
    matlab_startup_file = str(Path(__file__).resolve().parent / "matlab" / "startup.m")

    matlab_version = get_matlab_version(matlab_root_path)

    # If the matlab on system PATH is a wrapper script, then it would not be possible to determine MATLAB root (inturn not being able to determine MATLAB version)
    # unless MWI_CUSTOM_MATLAB_ROOT is set. Raising only a warning as the matlab version is only required for communicating with MHLM.
    if not matlab_version:
        logger.warn(
            f"Could not determine MATLAB version from MATLAB root path: {matlab_root_path}"
        )
        logger.warn(
            f"Set {mwi_env.get_env_name_custom_matlab_root()} to a valid MATLAB root path"
        )

    return {
        "matlab_path": matlab_root_path,
        "matlab_version": matlab_version,
        "matlab_cmd": [
            matlab_executable_path,
            "-nosplash",
            *flag_to_hide_desktop,
            "-softwareopengl",
            *matlab_lic_mode,
            "-r",
            f"try; run('{matlab_startup_file}'); catch ME; disp(ME.message); end;",
        ],
        "ws_env": ws_env,
        "mwa_api_endpoint": f"https://login{ws_env_suffix}.mathworks.com/authenticationws/service/v4",
        "mhlm_api_endpoint": f"https://licensing{ws_env_suffix}.mathworks.com/mls/service/v1/entitlement/list",
        "mwa_login": f"https://login{ws_env_suffix}.mathworks.com",
        "nlm_conn_str": nlm_conn_str,
    }


def get_mw_context_tags(extension_name):
    """Returns a string which combines existing MW_CONTEXT_TAGS value and context tags
    specific to where matlab-proxy is being launched from.

    Returns:
        str: Which combines existing MW_CONTEXT_TAGS with one from matlab-proxy.
    """
    existing_mw_context_tags = os.getenv("MW_CONTEXT_TAGS", "")

    if existing_mw_context_tags:
        logger.debug(f'Existing MW_CONTEXT_TAGS:"{existing_mw_context_tags}"')
        existing_mw_context_tags += ","

    mwi_context_tags = matlab_proxy.get_mwi_ddux_value(extension_name)
    logger.debug(f'DDUX value for matlab-proxy "{mwi_context_tags}"')

    combined_context_tags = existing_mw_context_tags + mwi_context_tags
    logger.debug(
        f'Combined DDUX value to be used for MATLAB process: "{combined_context_tags}"'
    )

    return combined_context_tags


def create_xvfb_cmd():
    """Creates the Xvfb command with a write descriptor.

    Returns:
        List: Containing 2 lists.

    The second List contains a read and a write descriptor.
    The first List is the command to launch Xvfb process with the same write descriptor(from the first list) embedded in the command.
    """
    # Using os.pipe() can lead to race conditions (ie.usage of same set of file descriptors between 2 processes)
    # when called in quick succession and also when running tests.
    # Using os.pipe2() with the flag os.O_NONBLOCK will avoid race conditions.
    dpipe = os.pipe2(os.O_NONBLOCK)

    # Allow child process to use the file descriptor created by parent.
    os.set_inheritable(dpipe[1], True)

    xvfb_cmd = [
        "Xvfb",
        "-displayfd",
        # Write descriptor
        str(dpipe[1]),
        "-screen",
        "0",
        "1600x1200x24",
        "-dpi",
        "100",
        # "-ac",
        "-extension",
        "RANDR",
        # "+render",
        # "-noreset",
    ]

    return xvfb_cmd, dpipe


def get_test_temp_dir():
    """The temp directory to be used by tests"""
    test_temp_dir = Path(tempfile.gettempdir()) / "MWI" / "tests"
    test_temp_dir.mkdir(parents=True, exist_ok=True)

    return test_temp_dir


def get_ssl_context(ssl_cert_file, ssl_key_file):
    """Creates an SSL CONTEXT for use with the TCP Site"""

    # The certfile string must be the path to a single file in PEM format containing the
    # certificate as well as any number of CA certificates needed to establish the certificate’s authenticity.
    # The keyfile string, if present, must point to a file containing the private key in.
    # Otherwise the private key will be taken from certfile as well.
    import traceback

    if ssl_cert_file != None:
        try:
            ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ssl_context.load_cert_chain(ssl_cert_file, ssl_key_file)
            logger.debug(f"Using SSL certification!")
        except Exception as e:
            # Something was wrong with the certificates provided
            error_message = "SSL certificates provided are invalid. Aborting..."
            logger.error(error_message)
            traceback.print_exc()
            logger.info("==== Fatal error : ===")
            print(e)
            # printing stack trace
            logger.info("======================")
            raise FatalError(error_message)
    else:
        ssl_context = None

    return ssl_context
