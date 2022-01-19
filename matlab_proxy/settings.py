# Copyright 2020-2021 The MathWorks, Inc.

import matlab_proxy
import os
import shutil
import socket
import ssl
import sys
import tempfile
import uuid
import xml.etree.ElementTree as ET

from matlab_proxy import mwi_environment_variables as mwi_env
from matlab_proxy.util import mwi_custom_http_headers, mwi_validators
from matlab_proxy.util import mwi_logger
from pathlib import Path

logger = mwi_logger.get()


def get_matlab_path():
    which_matlab = shutil.which("matlab")
    if which_matlab is None:
        return None
    return Path(which_matlab).resolve().parent.parent


def get_matlab_version(matlab_path):
    """Get the MATLAB Release version in this image"""

    if matlab_path is None:
        return None

    tree = ET.parse(matlab_path / "VersionInfo.xml")
    root = tree.getroot()
    return root.find("release").text


def get_ws_env_settings():
    ws_env = (os.getenv("WS_ENV") or "").lower()
    ws_env_suffix = f"-{ws_env}" if "integ" in ws_env else ""

    return ws_env, ws_env_suffix


def get_dev_settings(config):
    devel_file = Path(__file__).resolve().parent / "./devel.py"
    test_temp_dir = get_test_temp_dir()
    ws_env, ws_env_suffix = get_ws_env_settings()
    return {
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
        "matlab_config_file": test_temp_dir / "proxy_app_config.json",
        "ws_env": ws_env,
        "mwa_api_endpoint": f"https://login{ws_env_suffix}.mathworks.com/authenticationws/service/v4",
        "mhlm_api_endpoint": f"https://licensing{ws_env_suffix}.mathworks.com/mls/service/v1/entitlement/list",
        "mwa_login": f"https://login{ws_env_suffix}.mathworks.com",
        "mwi_custom_http_headers": mwi_custom_http_headers.get(),
        "env_config": mwi_validators.validate_env_config(config),
        "ssl_context": None,
    }


def get(config=matlab_proxy.get_default_config_name(), dev=False):
    """Returns the settings specific to the environment in which the server is running in
    If the environment variable 'TEST' is set  to true, will make some changes to the dev settings.

    Args:
        config : Dictionary as specified by the default_configuration.py file. Used to customize the app.
        dev (bool, optional): development environment. Defaults to False.

    Returns:
        Dict: Containing data on how to start MATLAB among other information.
    """

    if dev:
        settings = get_dev_settings(config)

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
            settings["nlm_conn_str"] = "abc@nlm"

        return settings

    else:
        matlab_startup_file = str(
            Path(__file__).resolve().parent / "matlab" / "startup.m"
        )
        matlab_path = get_matlab_path()
        ws_env, ws_env_suffix = get_ws_env_settings()

        ssl_key_file, ssl_cert_file = mwi_validators.validate_ssl_key_and_cert_file(
            os.getenv(mwi_env.get_env_name_ssl_key_file(), None),
            os.getenv(mwi_env.get_env_name_ssl_cert_file(), None),
        )
        return {
            "matlab_path": matlab_path,
            "matlab_version": get_matlab_version(matlab_path),
            "matlab_cmd": [
                "matlab",
                "-nosplash",
                "-nodesktop",
                "-softwareopengl",
                "-r",
                f"try; run('{matlab_startup_file}'); catch; end;",
            ],
            "create_xvfb_cmd": create_xvfb_cmd,
            "base_url": mwi_validators.validate_base_url(
                os.getenv(mwi_env.get_env_name_base_url(), "")
            ),
            "app_port": mwi_validators.validate_app_port_is_free(
                os.getenv(mwi_env.get_env_name_app_port())
            ),
            "host_interface": os.environ.get(mwi_env.get_env_name_app_host()),
            "mwapikey": str(uuid.uuid4()),
            "matlab_protocol": "https",
            "nlm_conn_str": mwi_validators.validate_mlm_license_file(
                os.environ.get(mwi_env.get_env_name_network_license_manager())
            ),
            "matlab_config_file": Path.home() / ".matlab" / "proxy_app_config.json",
            "ws_env": ws_env,
            "mwa_api_endpoint": f"https://login{ws_env_suffix}.mathworks.com/authenticationws/service/v4",
            "mhlm_api_endpoint": f"https://licensing{ws_env_suffix}.mathworks.com/mls/service/v1/entitlement/list",
            "mwa_login": f"https://login{ws_env_suffix}.mathworks.com",
            "mwi_custom_http_headers": mwi_custom_http_headers.get(),
            "env_config": mwi_validators.validate_env_config(config),
            "ssl_context": get_ssl_context(
                ssl_cert_file=ssl_cert_file, ssl_key_file=ssl_key_file
            ),
        }


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


def get_matlab_tempdir():
    """The temp directory used by MATLAB based on tempdir.m"""

    for env_name in mwi_env.get_env_name_matlab_tempdir():
        matlab_tempdir = os.environ.get(env_name)
        if matlab_tempdir is not None:
            break

    # MATLAB defaults to '/tmp'
    if matlab_tempdir is None:
        matlab_tempdir = "/tmp"

    return matlab_tempdir


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
            logger.error("SSL certificates provided are invalid. Aborting...")
            traceback.print_exc()
            logger.info("==== Fatal error : ===")
            print(e)
            # printing stack trace
            logger.info("======================")
            sys.exit(1)
    else:
        ssl_context = None

    return ssl_context
