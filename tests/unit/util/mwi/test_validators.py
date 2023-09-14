# Copyright (c) 2020-2023 The MathWorks, Inc.
"""Tests for functions in matlab_proxy/util/mwi_validators.py
"""

import os
import random
import socket
import tempfile

import matlab_proxy
import pytest
from matlab_proxy.util import system
from matlab_proxy.util.mwi import environment_variables as mwi_env
from matlab_proxy.util.mwi import validators
from matlab_proxy.util.mwi.exceptions import NetworkLicensingError, FatalError


@pytest.mark.parametrize(
    "MLM_LICENSE_FILE",
    [
        ("/path/to/a/non-existent/file"),
        ("1234"),
        ("hostname"),
        ("1234hostname"),
    ],
    ids=[
        "Invalid path to a license file",
        "NLM string with just port number",
        "NLM string with just hostname",
        "NLM string with just port number and hostname",
    ],
)
def test_validate_mlm_license_file_invalid_value(MLM_LICENSE_FILE, monkeypatch):
    """Check if validator raises expected exception"""

    env_name = mwi_env.get_env_name_network_license_manager()

    monkeypatch.setenv(env_name, MLM_LICENSE_FILE)
    nlm_conn_str = os.getenv(env_name)

    with pytest.raises(NetworkLicensingError) as e_info:
        validators.validate_mlm_license_file(nlm_conn_str)
    assert MLM_LICENSE_FILE in str(e_info.value)


@pytest.fixture(name="temporary_license_file")
def temporary_license_file_fixture(tmp_path):
    """Pytest fixture which returns a valid path to temporary license file."""
    import time

    temp_license_file_path = tmp_path / f'{str(time.time()).replace(".", "")}.lic'
    temp_license_file_path.touch()

    return temp_license_file_path


def test_validate_mlm_license_file_valid_license_file_path(
    temporary_license_file, monkeypatch
):
    """Check if a valid license path has been supplied to MLM_LICENSE_FILE env var"""
    env_name = mwi_env.get_env_name_network_license_manager()
    monkeypatch.setenv(env_name, str(temporary_license_file))

    validated_file_path = validators.validate_mlm_license_file(os.getenv(env_name))
    assert str(temporary_license_file) == validated_file_path


@pytest.mark.parametrize(
    "MLM_LICENSE_FILE",
    [
        (["1234@1.2_any-alphanumeric"]),
        (["1234@1.2_any-alphanumeric", "1234@1.2_any-alphanumeric"]),
        (
            [
                "1234@1.2_any-alphanumeric",
                "1234@1.2_any-alphanumeric",
                "1234@1.2_any-alphanumeric",
            ]
        ),
        [
            "1234@1.2_any-alphanumeric,1234@1.2_any-alphanumeric,1234@1.2_any-alphanumeric"
        ],
        (
            [
                "1234@1.2_any-alphanumeric",
                "1234@1.2_any-alphanumeric,1234@1.2_any-alphanumeric,1234@1.2_any-alphanumeric",
            ]
        ),
        (
            [
                "1234@1.2_any-alphanumeric,1234@1.2_any-alphanumeric,1234@1.2_any-alphanumeric",
                "1234@1.2_any-alphanumeric",
            ]
        ),
        (
            [
                "1234@1.2_any-alphanumeric",
                "1234@1.2_any-alphanumeric,1234@1.2_any-alphanumeric,1234@1.2_any-alphanumeric",
                "1234@1.2_any-alphanumeric",
            ]
        ),
    ],
    ids=[
        "1 NLM server",
        "2 NLM servers",
        "3 NLM servers",
        "Just a server triad",
        "1 NLM server prefixed to a server triad",
        "1 NLM server suffixed to a server triad",
        "1 NLM server prefixed and another suffixed to a server triad",
    ],
)
def test_validate_mlm_license_file_for_valid_nlm_string(MLM_LICENSE_FILE, monkeypatch):
    """Check if port@hostname passes validation"""

    seperator = system.get_mlm_license_file_seperator()
    MLM_LICENSE_FILE = seperator.join(MLM_LICENSE_FILE)
    env_name = mwi_env.get_env_name_network_license_manager()
    monkeypatch.setenv(env_name, MLM_LICENSE_FILE)
    conn_str = validators.validate_mlm_license_file(os.getenv(env_name))
    assert conn_str == MLM_LICENSE_FILE


def test_validate_mlm_license_file_None():
    """Test to check if validate_mlm_license_file() returns None when nlm_conn_str is None."""
    assert validators.validate_mlm_license_file(None) is None


def test_get_with_environment_variables(monkeypatch):
    """Check if path to license file passes validation"""
    env_name = mwi_env.get_env_name_network_license_manager()
    fd, path = tempfile.mkstemp()
    monkeypatch.setenv(env_name, path)
    try:
        conn_str = validators.validate_mlm_license_file(os.getenv(env_name))
        assert conn_str == str(path)
    finally:
        os.close(fd)
        os.remove(path)


def test_validate_app_port_is_free_false():
    """Test to validate if supplied app port is free"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    port = s.getsockname()[1]
    with pytest.raises(FatalError) as e:
        validators.validate_app_port_is_free(port)
    s.close()


def test_validate_app_port_is_free_true():
    """Test to validate if supplied app port is free"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    port = s.getsockname()[1]
    s.close()
    assert validators.validate_app_port_is_free(port) == port


def test_validate_app_port_None():
    """Tests if validated app port is None when MWI_APP_PORT env variable is not set.
    If validated app port is None implies a random free port will be used at launch.
    """
    assert validators.validate_app_port_is_free(None) is None


def test_validate_env_config_true():
    """Validate the default config which is used in this package."""
    config = validators.validate_env_config(matlab_proxy.get_default_config_name())
    assert isinstance(config, dict)


def test_validate_env_config_false():
    """Passing a non existent config should raise FatalError exception"""

    with pytest.raises(FatalError) as e:
        config = validators.validate_env_config(str(random.randint(10, 100)))


def test_get_configs():
    """Test to check if atleast 1 env config is discovered.
    When this package is installed, we will have a default config.
    """
    configs = validators.__get_configs()

    assert len(configs.keys()) >= 1


@pytest.mark.parametrize(
    "base_url, validated_base_url",
    [
        ("", ""),
        ("/bla", "/bla"),
        ("/bla/", "/bla"),
    ],
    ids=[
        "Launch integration at root",
        "Launch at custom path",
        "Launch at custom with suffix: /",
    ],
)
def test_validate_base_url(base_url, validated_base_url):
    """Tests multiple base_urls which will beparsed and validated successfully.

    Args:
        base_url (str): base_url
        validated_base_url (str): validated base_url
    """
    assert validators.validate_base_url(base_url) == validated_base_url


def test_validate_base_url_no_prefix_error():
    """Test to check base_url will throw error when a prefix / is not present in it.[summary]"""
    with pytest.raises(FatalError) as e:
        validators.validate_base_url("matlab/")


def test_validate_mwi_ssl_key_and_cert_file(monkeypatch):
    """Check if port@hostname passes validation"""
    ssl_cert_file_env_name = mwi_env.get_env_name_ssl_cert_file()
    ssl_key_file_env_name = mwi_env.get_env_name_ssl_key_file()
    fd, path = tempfile.mkstemp()

    monkeypatch.setenv(ssl_cert_file_env_name, path)
    monkeypatch.setenv(ssl_key_file_env_name, path)
    try:
        # Verify that if KEY and CERT are provided
        key_file, cert_file = validators.validate_ssl_key_and_cert_file(
            os.getenv(ssl_key_file_env_name), os.getenv(ssl_cert_file_env_name)
        )
        assert key_file == str(path)
        assert cert_file == str(path)

        # Verify that KEY can be None
        key_file, cert_file = validators.validate_ssl_key_and_cert_file(
            None, os.getenv(ssl_cert_file_env_name)
        )
        assert key_file == None
        assert cert_file == str(path)

        # Verify that if KEY is provided, CERT must also be provided
        with pytest.raises(FatalError) as e:
            validators.validate_ssl_key_and_cert_file(
                os.getenv(ssl_key_file_env_name), None
            )

        # Verify that KEY is valid file location
        with pytest.raises(FatalError) as e:
            validators.validate_ssl_key_and_cert_file(
                "/file/does/not/exist", os.getenv(ssl_cert_file_env_name)
            )

        # Verify that KEY is valid file location
        with pytest.raises(FatalError) as e:
            validators.validate_ssl_key_and_cert_file(
                os.getenv(ssl_key_file_env_name), "/file/does/not/exist"
            )
    finally:
        # Need to close the file descriptor in Windows
        # Or else PermissionError is raised.
        os.close(fd)
        os.remove(path)
