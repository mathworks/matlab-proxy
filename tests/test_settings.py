# Copyright (c) 2020-2023 The MathWorks, Inc.

import os
import time

import matlab_proxy
import matlab_proxy.settings as settings
from matlab_proxy.constants import VERSION_INFO_FILE_NAME
from pathlib import Path
import pytest
from matlab_proxy.util.mwi import environment_variables as mwi_env
from matlab_proxy.util.mwi.exceptions import MatlabInstallError

"""This file tests methods defined in settings.py file
"""


def version_info_file_content(matlab_version):
    """Returns contents of VersionInfo.xml file for a specific matlab_version

    Args:
        matlab_version (str): MATLAB Version

    Returns:
        str: Contents of VersionInfo.xml file for a specific matlab version
    """

    """
    Returns the contents of a valid VersionInfo.xml file
    """
    return f"""<!--  Version information for MathWorks R2020b Release  -->
                <MathWorks_version_info>
                <version>9.9.0.1524771</version>
                <release>{matlab_version}</release>
                <description>Update 2</description>
                <date>Nov 03 2020</date>
                <checksum>2207788044</checksum>
                </MathWorks_version_info>
            """


@pytest.fixture(name="fake_matlab_empty_root_path")
def fake_matlab_empty_root_path_fixture(tmp_path):
    empty_matlab_root = tmp_path / "R2020b"
    os.makedirs(empty_matlab_root, exist_ok=True)
    return empty_matlab_root


@pytest.fixture(name="fake_matlab_executable_path")
def fake_matlab_executable_path_fixture(fake_matlab_empty_root_path):
    matlab_executable_path = fake_matlab_empty_root_path / "bin" / "matlab"
    os.makedirs(matlab_executable_path, exist_ok=True)

    return matlab_executable_path


def create_file(file_path, file_content):
    with open(file_path, "w") as f:
        f.write(file_content)


@pytest.fixture(name="fake_matlab_valid_version_info_file_path")
def fake_matlab_valid_version_info_file_path_fixture(fake_matlab_empty_root_path):
    version_info_file_path = fake_matlab_empty_root_path / VERSION_INFO_FILE_NAME
    create_file(version_info_file_path, version_info_file_content("R2020b"))

    return version_info_file_path


@pytest.fixture(name="fake_matlab_root_path")
def fake_matlab_root_path_fixture(
    fake_matlab_executable_path, fake_matlab_valid_version_info_file_path
):
    """Pytest fixture to create a fake matlab installation path.

    Args:
        fake_matlab_executable_path (Pytest fixture): Pytest fixture which returns path to a fake matlab executable
        fake_matlab_valid_version_info_file_path (Pytest fixture): Pytest fixture which returns path of a VersionInfo.xml file for a fake matlab

    Returns:
        pathlib.Path: Path to a fake matlab root
    """

    return fake_matlab_executable_path.parent.parent


@pytest.fixture(name="mock_shutil_which_none")
def mock_shutil_which_none_fixture(mocker):
    """Pytest fixture to mock shutil.which() method to return None

    Args:
        mocker : Built in pytest fixture
    """
    mocker.patch("shutil.which", return_value=None)


def test_get_matlab_root_path_none(mock_shutil_which_none):
    """Test to check if settings.get_matlab_path() returns none when no matlab installation is present.

    mock_shutil_which_none fixture mocks shutil.which() to return None

    Args:
        mock_shutil_which_none : Pytest fixture to mock shutil.which() method to return None.
    """
    with pytest.raises(MatlabInstallError) as e:
        _ = settings.get_matlab_executable_and_root_path()


@pytest.fixture(name="mock_shutil_which")
def mock_shutil_which_fixture(mocker, fake_matlab_executable_path):
    """Pytest fixture to mock shutil.which() method to return a temporary fake matlab path

    Args:
        mocker : Built in pytest fixture
        fake_matlab_executable_path : Pytest fixture which returns path to fake matlab executable file
    """
    mocker.patch("shutil.which", return_value=fake_matlab_executable_path)


@pytest.fixture(name="non_existent_path")
def non_existent_path_fixture(tmp_path):
    # Build path to a non existent folder
    random_folder = tmp_path / f'{str(time.time()).replace(".", "")}'
    non_existent_path = Path(tmp_path) / random_folder

    return non_existent_path


def test_get_matlab_root_path(fake_matlab_root_path, mock_shutil_which):
    """Test to check if a valid matlab path is returned


    mock_shutil_which fixture mocks shutil.which() method to return a temporary path.

    Args:
        fake_matlab_executable_path : Pytest fixture which returns a path to fake matlab executable
        mock_shutil_which : Pytest fixture to mock shutil.which() method to return a fake matlab path
    """
    assert settings.get_matlab_executable_and_root_path()[1] == fake_matlab_root_path


def test_get_matlab_root_path_invalid_custom_matlab_root(
    monkeypatch, non_existent_path
):
    # Monkeypatch the env var
    monkeypatch.setenv(
        mwi_env.get_env_name_custom_matlab_root(), str(non_existent_path)
    )

    # Test for appropriate error
    with pytest.raises(MatlabInstallError) as e:
        _ = settings.get_matlab_executable_and_root_path()


def test_get_matlab_version_none():
    """Test to check settings.get_matlab_version() returns None when no valid matlab path is provided."""
    assert settings.get_matlab_version(None) is None


def test_get_matlab_version(fake_matlab_root_path, mock_shutil_which):
    """Test if a matlab version is returned when from a Version.xml file.

    mock_shutil_which fixture will mock the settings.get_matlab_path() to return a fake matlab path
    which containing a valid VersionInfo.xml file. settings.get_matlab_version() will extract the matlab version
    from this file

    Args:
        mock_shutil_which : Pytest fixture to mock shutil.which() method.
    """
    (
        matlab_executable_path,
        matlab_root_path,
    ) = settings.get_matlab_executable_and_root_path()
    settings.get_matlab_version(matlab_root_path) is not None


def test_get_matlab_version_invalid_custom_matlab_root(monkeypatch, non_existent_path):
    # Monkeypatch the env var
    monkeypatch.setenv(
        mwi_env.get_env_name_custom_matlab_root(), str(non_existent_path)
    )

    assert settings.get_matlab_version(None) is None


def test_get_matlab_version_valid_custom_matlab_root(non_existent_path, monkeypatch):
    """Test matlab version when a custom matlab root path is supplied

    Args:
        tmp_path : Built-in pytest fixture
        monkeypatch : Built-in pytest fixture        m
    """
    custom_matlab_root_path = non_existent_path
    os.makedirs(custom_matlab_root_path, exist_ok=True)
    matlab_version = "R2020b"

    # Create a valid VersionInfo.xml file at custom matlab root
    version_info_file_path = custom_matlab_root_path / VERSION_INFO_FILE_NAME
    create_file(version_info_file_path, version_info_file_content(matlab_version))

    # Monkeypatch the env var
    monkeypatch.setenv(
        mwi_env.get_env_name_custom_matlab_root(), str(custom_matlab_root_path)
    )

    actual_matlab_version = settings.get_matlab_version(custom_matlab_root_path)

    assert actual_matlab_version == matlab_version


@pytest.mark.parametrize(
    "matlab_version", ["R2020b", "R2021a"], ids=["R2020b", "R2021a"]
)
def test_settings_get_matlab_cmd_for_different_matlab_versions(
    matlab_version, non_existent_path, monkeypatch
):
    """Test to check settings.get returns the correct matlab_cmd when MWI_CUSTOM_MATLAB_ROOT is set.

    Args:
        matlab_version (str): Matlab version
        non_existent_path (Pytest fixture): Pytest fixture which returns a temporary non-existent path
        monkeypatch (Builtin pytest fixture): Pytest fixture to monkeypatch environment variables.
    """

    # Create custom matlab root for specific matlab_version
    custom_matlab_root_path = non_existent_path / matlab_version
    os.makedirs(custom_matlab_root_path, exist_ok=True)

    # Create a valid VersionInfo.xml file at custom matlab root
    version_info_file_path = custom_matlab_root_path / VERSION_INFO_FILE_NAME
    create_file(version_info_file_path, version_info_file_content(matlab_version))

    monkeypatch.setenv(
        mwi_env.get_env_name_custom_matlab_root(), str(custom_matlab_root_path)
    )

    # Assert matlab_version is in path to matlab_cmd
    sett = settings.get(dev=False)
    assert matlab_version in str(sett["matlab_cmd"][0])


def test_get_dev_true():
    """Test to check settings returned by settings.get() method in dev mode."""
    dev_mode_settings = settings.get(dev=True)

    assert dev_mode_settings["matlab_cmd"][0] != "matlab"
    assert dev_mode_settings["matlab_protocol"] == "http"


@pytest.fixture(name="patch_env_variables")
def patch_env_variables_fixture(monkeypatch):
    """Pytest fixture to Monkeypatch MWI_APP_PORT, BASE_URL, APP_HOST AND MLM_LICENSE_FILE env variables


    Args:
        monkeypatch : Built-in pytest fixture
    """
    monkeypatch.setenv(mwi_env.get_env_name_base_url(), "/matlab")
    monkeypatch.setenv(mwi_env.get_env_name_app_port(), "8900")
    monkeypatch.setenv(mwi_env.get_env_name_app_host(), "localhost")
    monkeypatch.setenv(mwi_env.get_env_name_network_license_manager(), "123@nlm")


def test_get_dev_false(patch_env_variables, mock_shutil_which, fake_matlab_root_path):
    """Test settings.get() method in Non Dev mode.

    In Non dev mode, settings.get() expects MWI_APP_PORT, MWI_BASE_URL, APP_HOST AND MLM_LICENSE_FILE env variables
    to be present. patch_env_variables monkeypatches them.

    Args:
        patch_env_variables : Pytest fixture which monkeypatches some env variables.
    """
    _settings = settings.get(dev=False)
    assert "matlab" in str(_settings["matlab_cmd"][0])
    assert os.path.isdir(_settings["matlab_path"])
    assert _settings["matlab_protocol"] == "https"


def test_get_mw_context_tags(monkeypatch):
    """Tests get_mw_context_tags() function to return appropriate MW_CONTEXT_TAGS"""

    # Monkeypatch env var MW_CONTEXT_TAGS to check for if condition
    dockerhub_mw_context_tags = "MATLAB:DOCKERHUB:V1"
    monkeypatch.setenv("MW_CONTEXT_TAGS", dockerhub_mw_context_tags)

    extension_name = matlab_proxy.get_default_config_name()

    matlab_proxy_base_context_tags = matlab_proxy.get_mwi_ddux_value(extension_name)
    expected_result = f"{dockerhub_mw_context_tags},{matlab_proxy_base_context_tags}"

    actual_result = settings.get_mw_context_tags(extension_name)

    assert expected_result == actual_result
