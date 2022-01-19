# Copyright 2021 The MathWorks, Inc.
"""Tests for functions in matlab_proxy/util/mwi_validators.py
"""

import pytest, os, tempfile, socket, random
import matlab_proxy
from matlab_proxy.util import mwi_validators
from matlab_proxy import mwi_environment_variables as mwi_env
from matlab_proxy.util.mwi_exceptions import NetworkLicensingError


def test_validate_mlm_license_file_for_invalid_string(monkeypatch):
    """Check if validator raises expected exception"""
    # Delete the environment variables if they do exist
    env_name = mwi_env.get_env_name_network_license_manager()
    invalid_string = "/Invalid/String/"
    monkeypatch.setenv(env_name, invalid_string)
    nlm_conn_str = os.getenv(env_name)
    with pytest.raises(NetworkLicensingError) as e_info:
        conn_str = mwi_validators.validate_mlm_license_file(nlm_conn_str)
    assert invalid_string in str(e_info.value)


def test_validate_mlm_license_file_for_valid_server_syntax(monkeypatch):
    """Check if port@hostname passes validation"""
    env_name = mwi_env.get_env_name_network_license_manager()
    license_manager_address = "1234@1.2_any-alphanumeric"
    monkeypatch.setenv(env_name, license_manager_address)
    conn_str = mwi_validators.validate_mlm_license_file(os.getenv(env_name))
    assert conn_str == license_manager_address


def test_validate_mlm_license_file_for_valid_server_triad_syntax(monkeypatch):
    """Check if port@hostname passes validation"""
    env_name = mwi_env.get_env_name_network_license_manager()
    license_manager_address = (
        "1234@1.2_any-alphanumeric,1234@1.2_any-alphanumeric,1234@1.2_any-alphanumeric"
    )
    monkeypatch.setenv(env_name, license_manager_address)
    conn_str = mwi_validators.validate_mlm_license_file(os.getenv(env_name))
    assert conn_str == license_manager_address


def test_validate_mlm_license_file_None():
    """Test to check if validate_mlm_license_file() returns None when nlm_conn_str is None."""
    assert mwi_validators.validate_mlm_license_file(None) is None


def test_get_with_environment_variables(monkeypatch):
    """Check if path to license file passes validation"""
    env_name = mwi_env.get_env_name_network_license_manager()
    fd, path = tempfile.mkstemp()
    monkeypatch.setenv(env_name, path)
    try:
        conn_str = mwi_validators.validate_mlm_license_file(os.getenv(env_name))
        assert conn_str == str(path)
    finally:
        os.remove(path)


def test_validate_app_port_is_free_false():
    """Test to validate if supplied app port is free"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    port = s.getsockname()[1]
    with pytest.raises(SystemExit) as e:
        mwi_validators.validate_app_port_is_free(port)
    assert e.value.code == 1
    s.close()


def test_validate_app_port_is_free_true():
    """Test to validate if supplied app port is free"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    port = s.getsockname()[1]
    s.close()
    assert mwi_validators.validate_app_port_is_free(port) == port


def test_validate_app_port_None():
    """Tests if validated app port is None when MWI_APP_PORT env variable is not set.
    If validated app port is None implies a random free port will be used at launch.
    """
    assert mwi_validators.validate_app_port_is_free(None) is None


def test_validate_env_config_true():
    """Validate the default config which is used in this package."""
    config = mwi_validators.validate_env_config(matlab_proxy.get_default_config_name())
    assert isinstance(config, dict)


def test_validate_env_config_false():
    """Passing a non existent config should raise SystemExit exception"""

    with pytest.raises(SystemExit) as e:
        config = mwi_validators.validate_env_config(str(random.randint(10, 100)))

    assert e.value.code == 1


def test_get_configs():
    """Test to check if atleast 1 env config is discovered.
    When this package is installed, we will have a default config.
    """
    configs = mwi_validators.__get_configs()

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
    assert mwi_validators.validate_base_url(base_url) == validated_base_url


def test_validate_base_url_no_prefix_error():
    """Test to check base_url will throw error when a prefix / is not present in it.[summary]"""
    with pytest.raises(SystemExit) as e:
        mwi_validators.validate_base_url("matlab/")
    assert e.value.code == 1


def test_validate_mwi_ssl_key_and_cert_file(monkeypatch):
    """Check if port@hostname passes validation"""
    ssl_cert_file_env_name = mwi_env.get_env_name_ssl_cert_file()
    ssl_key_file_env_name = mwi_env.get_env_name_ssl_key_file()
    fd, path = tempfile.mkstemp()
    monkeypatch.setenv(ssl_cert_file_env_name, path)
    monkeypatch.setenv(ssl_key_file_env_name, path)
    try:
        # Verify that if KEY and CERT are provided
        key_file, cert_file = mwi_validators.validate_ssl_key_and_cert_file(
            os.getenv(ssl_key_file_env_name), os.getenv(ssl_cert_file_env_name)
        )
        assert key_file == str(path)
        assert cert_file == str(path)

        # Verify that KEY can be None
        key_file, cert_file = mwi_validators.validate_ssl_key_and_cert_file(
            None, os.getenv(ssl_cert_file_env_name)
        )
        assert key_file == None
        assert cert_file == str(path)

        # Verify that if KEY is provided, CERT must also be provided
        with pytest.raises(SystemExit) as e:
            mwi_validators.validate_ssl_key_and_cert_file(
                os.getenv(ssl_key_file_env_name), None
            )
        assert e.value.code == 1

        # Verify that KEY is valid file location
        with pytest.raises(SystemExit) as e:
            mwi_validators.validate_ssl_key_and_cert_file(
                "/file/does/not/exist", os.getenv(ssl_cert_file_env_name)
            )
        assert e.value.code == 1

        # Verify that KEY is valid file location
        with pytest.raises(SystemExit) as e:
            mwi_validators.validate_ssl_key_and_cert_file(
                os.getenv(ssl_key_file_env_name), "/file/does/not/exist"
            )
        assert e.value.code == 1
    finally:
        os.remove(path)
