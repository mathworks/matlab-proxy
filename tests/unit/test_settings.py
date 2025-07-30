# Copyright 2020-2025 The MathWorks, Inc.

import os
import tempfile
import time
from pathlib import Path

import pytest

import matlab_proxy
import matlab_proxy.settings as settings
from matlab_proxy.constants import DEFAULT_PROCESS_START_TIMEOUT, VERSION_INFO_FILE_NAME
from matlab_proxy.util.cookie_jar import HttpOnlyCookieJar
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
    random_folder = tmp_path / f"{str(time.time()).replace('.', '')}"
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


@pytest.mark.parametrize(
    "timeout_value",
    [
        (130, 130),
        ("asdf", DEFAULT_PROCESS_START_TIMEOUT),
        (120.5, DEFAULT_PROCESS_START_TIMEOUT),
        (None, DEFAULT_PROCESS_START_TIMEOUT),
    ],
    ids=["Valid number", "Invalid number", "Valid decimal number", "No value supplied"],
)
def test_get_process_timeout(timeout_value, monkeypatch):
    """Parameterized test to check settings.test_get_process_timeout returns the correct timeout value when MWI_PROCESS_STARTUP_TIMEOUT is set.

    Args:
        timeout (str): Timeout for processes launched by matlab-proxy
        monkeypatch (Builtin pytest fixture): Pytest fixture to monkeypatch environment variables.
    """
    # Arrange
    supplied_timeout, expected_timeout = timeout_value[0], timeout_value[1]

    # pytest would throw warnings if None is supplied to monkeypatch
    if supplied_timeout:
        monkeypatch.setenv(
            mwi_env.get_env_name_process_startup_timeout(), str(supplied_timeout)
        )

    # Act
    actual_timeout = settings.get_process_startup_timeout()

    # Assert
    assert expected_timeout == actual_timeout


def test_get_mwi_config_folder_dev():
    ## Arrange
    expected_config_dir = Path(tempfile.gettempdir()) / "MWI" / "tests"

    # Act
    actual_config_dir = settings.get_mwi_config_folder(dev=True)

    # Assert
    assert expected_config_dir == actual_config_dir


@pytest.mark.parametrize(
    "hostname, home, expected_mwi_config_dir",
    [
        (
            "bob",
            Path("/home/bob"),
            Path("/home/bob") / ".matlab" / "MWI" / "hosts" / "bob",
        ),
        (
            "bob",
            Path("/home/CommonProject"),
            Path("/home/CommonProject") / ".matlab" / "MWI" / "hosts" / "bob",
        ),
        (
            None,
            Path("/home/CommonProject"),
            Path("/home/CommonProject") / ".matlab" / "MWI",
        ),
    ],
    ids=[
        "Single host machine with unique $HOME per host",
        "Multi-host machine with common $HOME for multiple hosts",
        "default directory when hostname is missing",
    ],
)
def test_get_mwi_config_folder(mocker, hostname, home, expected_mwi_config_dir):
    # Arrange
    mocker.patch("matlab_proxy.settings.Path.home", return_value=home)
    mocker.patch("matlab_proxy.settings.socket.gethostname", return_value=hostname)

    # Act
    actual_config_dir = settings.get_mwi_config_folder()

    # Assert
    assert expected_mwi_config_dir == actual_config_dir


def test_get_ssl_context_with_SSL_disabled(monkeypatch, tmpdir):
    monkeypatch.setenv(mwi_env.get_env_name_enable_ssl(), "False")
    mwi_certs_dir = Path(tmpdir)
    ssl_context = settings._validate_ssl_files_and_get_ssl_context(mwi_certs_dir)
    assert ssl_context is None


def test_get_ssl_context_with_SSL_enabled_auto_generated_certs(
    monkeypatch, mocker, tmpdir
):
    monkeypatch.setenv(mwi_env.get_env_name_enable_ssl(), "True")
    mocker.patch(
        "matlab_proxy.settings.generate_new_self_signed_certs",
        return_value=("cert_path", "key_path"),
    )
    mock_ssl_context = mocker.patch("ssl.create_default_context")
    mock_context = mocker.Mock()
    mock_ssl_context.return_value = mock_context
    mock_context.load_cert_chain.side_effect = None
    mwi_certs_dir = Path(tmpdir)

    ssl_context = settings._validate_ssl_files_and_get_ssl_context(mwi_certs_dir)
    assert ssl_context is not None


def test_get_ssl_context_with_invalid_self_signed_certs_returns_none(mocker, tmpdir):
    mocker.patch(
        "matlab_proxy.settings.generate_new_self_signed_certs",
        return_value=("cert_path", "key_path"),
    )
    mock_ssl_context = mocker.patch("ssl.create_default_context")
    mock_context = mocker.Mock()
    mock_ssl_context.return_value = mock_context
    exception_msg = "Invalid certificate!"
    mock_context.load_cert_chain.side_effect = Exception(exception_msg)
    mwi_certs_dir = Path(tmpdir)

    assert settings._validate_ssl_files_and_get_ssl_context(mwi_certs_dir) is None


def test_get_ssl_context_with_valid_custom_ssl_files(monkeypatch, mocker, tmpdir):
    # Sets up the SUT
    monkeypatch.setenv(mwi_env.get_env_name_enable_ssl(), "True")
    monkeypatch.setenv(mwi_env.get_env_name_ssl_cert_file(), "test/cert.pem")
    monkeypatch.setenv(mwi_env.get_env_name_ssl_key_file(), "test/key.pem")
    mocker.patch(
        "matlab_proxy.settings.mwi.validators.validate_ssl_key_and_cert_file",
        return_value=("test/cert.pem", "test/key.pem"),
    )
    new_cert_fx = mocker.patch("matlab_proxy.settings.generate_new_self_signed_certs")
    mock_ssl_context = mocker.patch("ssl.create_default_context")
    mock_context = mocker.Mock()
    mock_ssl_context.return_value = mock_context
    mock_context.load_cert_chain.side_effect = None
    mwi_certs_dir = Path(tmpdir)

    ssl_context = settings._validate_ssl_files_and_get_ssl_context(mwi_certs_dir)
    # Checks that self-signed certificate generation is not happening when user supplies valid ssl files
    new_cert_fx.assert_not_called()
    assert ssl_context is not None


def test_get_ssl_context_with_invalid_custom_ssl_files_raises_exception(
    monkeypatch, mocker, tmpdir
):
    # Sets up the SUT
    monkeypatch.setenv(mwi_env.get_env_name_enable_ssl(), "True")
    monkeypatch.setenv(mwi_env.get_env_name_ssl_cert_file(), "test/cert.pem")
    monkeypatch.setenv(mwi_env.get_env_name_ssl_key_file(), "test/key.pem")
    mocker.patch(
        "matlab_proxy.settings.mwi.validators.validate_ssl_key_and_cert_file",
        return_value=("test/cert.pem", "test/key.pem"),
    )
    mock_ssl_context = mocker.patch("ssl.create_default_context")
    mock_context = mocker.Mock()
    mock_ssl_context.return_value = mock_context
    exception_msg = "Invalid certificate!"
    mock_context.load_cert_chain.side_effect = Exception(exception_msg)
    mwi_certs_dir = Path(tmpdir)

    with pytest.raises(Exception, match=exception_msg):
        settings._validate_ssl_files_and_get_ssl_context(mwi_certs_dir)


@pytest.mark.parametrize(
    "expected_value_for_has_custom_code, custom_code, has_custom_code_exception_matlab_cmd",
    [(False, "", False), (True, "run(disp('MATLAB'))", True)],
    ids=["No custom code to execute", "Has custom code to execute"],
)
def test_get_matlab_settings_custom_code(
    monkeypatch,
    expected_value_for_has_custom_code,
    custom_code,
    has_custom_code_exception_matlab_cmd,
):
    # Arrange
    monkeypatch.setenv(mwi_env.get_env_name_custom_matlab_code(), custom_code)

    # Act
    has_custom_code, code_to_execute = settings._get_matlab_code_to_execute()
    exception_present_in_matlab_cmd = "MATLABCustomStartupCodeError" in code_to_execute

    # Assert
    assert has_custom_code == expected_value_for_has_custom_code
    assert exception_present_in_matlab_cmd == has_custom_code_exception_matlab_cmd


def test_get_nlm_conn_str(monkeypatch):
    # Arrange
    test_nlm_str = "123@license_server_address"
    monkeypatch.setenv(mwi_env.get_env_name_network_license_manager(), test_nlm_str)

    # Act
    nlm_conn_str = settings._get_nlm_conn_str()

    # Assert
    assert nlm_conn_str == test_nlm_str


@pytest.mark.parametrize("ws_env_suffix", ["", "-dev", "-test"])
def test_get_mw_licensing_urls(ws_env_suffix):
    # Act
    urls = settings._get_mw_licensing_urls(ws_env_suffix)

    # Assert
    assert all(ws_env_suffix in url for url in urls.values())


@pytest.mark.parametrize("nlm_conn_str", [None, "1234@testserver"])
def test_get_matlab_cmd_posix(nlm_conn_str, mocker):
    # Arrange
    matlab_executable_path = "/path/to/matlab"
    code_to_execute = "disp('Test')"
    mocker.patch("matlab_proxy.settings.system.is_windows", return_value=False)

    # Act
    cmd = settings._get_matlab_cmd(
        matlab_executable_path, code_to_execute, nlm_conn_str
    )

    # Assert
    assert cmd[0] == matlab_executable_path
    assert "-noDisplayDesktop" not in cmd

    if nlm_conn_str:
        assert "-licmode" in cmd
        assert "file" in cmd
    else:
        assert "-licmode" not in cmd


def test_get_matlab_cmd_windows(mocker):
    # Arrange
    matlab_executable_path = "C:\\path\\to\\matlab.exe"
    code_to_execute = "disp('Test')"
    mocker.patch("matlab_proxy.settings.system.is_windows", return_value=True)

    # Act
    cmd = settings._get_matlab_cmd(matlab_executable_path, code_to_execute, None)

    # Assert
    assert "-noDisplayDesktop" in cmd
    assert "-wait" in cmd
    assert "-log" in cmd
    assert ".exe" in cmd[0]  # Assert .exe suffix in matlab_executable_path


def test_get_matlab_cmd_with_startup_profiling(mocker):
    # Arrange
    mocker.patch("matlab_proxy.settings.system.is_windows", return_value=False)
    mocker.patch(
        "matlab_proxy.settings.mwi_env.Experimental.is_matlab_startup_profiling_enabled",
        return_value=True,
    )

    matlab_executable_path = "/path/to/matlab"
    code_to_execute = "disp('Test')"

    # Act
    cmd = settings._get_matlab_cmd(matlab_executable_path, code_to_execute, None)

    # Assert
    assert "-timing" in cmd


def test_get_matlab_settings_no_matlab_on_path(mocker):
    # Arrange
    mocker.patch("matlab_proxy.settings.shutil.which", return_value=None)

    # Act
    matlab_settings = settings.get_matlab_settings()

    # Assert
    assert isinstance(matlab_settings["error"], MatlabInstallError)


def test_get_matlab_settings_matlab_softlink(mocker, tmp_path):
    # Arrange
    matlab_root_path = Path(tmp_path)
    matlab_exec_path = matlab_root_path / "bin" / "matlab"
    mocker.patch("matlab_proxy.settings.shutil.which", return_value=matlab_exec_path)
    mocker.patch(
        "matlab_proxy.settings.mwi.validators.validate_matlab_root_path",
        return_value=matlab_root_path,
    )

    # Act
    matlab_settings = settings.get_matlab_settings()

    # Assert
    assert str(matlab_exec_path) in str(matlab_settings["matlab_cmd"][0])
    assert matlab_settings["matlab_path"] == matlab_root_path
    assert (
        matlab_settings["matlab_version"] is None
    )  # There's no VersionInfo.xml file in the mock setup


def test_get_matlab_settings_matlab_wrapper(mocker, tmp_path):
    # Arrange
    matlab_exec_path = Path(tmp_path) / "matlab"
    mocker.patch("matlab_proxy.settings.shutil.which", return_value=matlab_exec_path)

    # Act
    matlab_settings = settings.get_matlab_settings()

    # Assert
    assert str(matlab_exec_path) in str(matlab_settings["matlab_cmd"][0])
    assert (
        matlab_settings["matlab_path"] is None
    )  # Matlab root could not be determined because wrapper script is being used
    assert matlab_settings["matlab_version"] is None
    assert (
        matlab_settings["error"] is None
    )  # Error has to be None when matlab executable is on PATH but root path could not be determined


def test_get_matlab_settings_valid_custom_matlab_root(mocker, monkeypatch, tmp_path):
    # Arrange
    matlab_root_path = Path(tmp_path)
    matlab_exec_path = matlab_root_path / "bin" / "matlab"
    matlab_version = "R2024b"
    monkeypatch.setenv(mwi_env.get_env_name_custom_matlab_root(), str(matlab_root_path))
    mocker.patch(
        "matlab_proxy.settings.mwi.validators.validate_matlab_root_path",
        return_value=matlab_root_path,
    )
    mocker.patch(
        "matlab_proxy.settings.get_matlab_version", return_value=matlab_version
    )

    # Act
    matlab_settings = settings.get_matlab_settings()

    # Assert
    assert str(matlab_exec_path) in str(matlab_settings["matlab_cmd"][0])
    assert matlab_settings["matlab_path"] == matlab_root_path
    assert matlab_settings["matlab_version"] == matlab_version
    assert matlab_settings["error"] is None


def test_get_matlab_settings_invalid_custom_matlab_root(mocker, monkeypatch, tmp_path):
    # Arrange
    matlab_root_path = Path(tmp_path)
    monkeypatch.setenv(mwi_env.get_env_name_custom_matlab_root(), str(matlab_root_path))

    # Act
    matlab_settings = settings.get_matlab_settings()

    # Assert
    # When custom MATLAB root is supplied, it must be the actual MATLAB root ie.
    # VersionInfo.xml file must to be there
    # matlab executable inside the bin folder must be there
    # If not, MATLAB related settings should be None and custom MATLAB root error should be present
    assert matlab_settings["matlab_cmd"] is None
    assert matlab_settings["matlab_path"] is None
    assert matlab_settings["matlab_version"] is None
    assert (
        isinstance(matlab_settings["error"], MatlabInstallError)
        and mwi_env.get_env_name_custom_matlab_root()
        in matlab_settings["error"].message
    )


def test_get_cookie_jar(monkeypatch):
    """Test to check if Cookie Jar is returned as a part of server settings"""
    monkeypatch.setenv(mwi_env.Experimental.get_env_name_use_cookie_cache(), "false")
    assert (
        settings.get_server_settings(matlab_proxy.get_default_config_name())[
            "cookie_jar"
        ]
        is None
    )

    monkeypatch.setenv(mwi_env.Experimental.get_env_name_use_cookie_cache(), "true")
    assert isinstance(
        settings.get_server_settings(matlab_proxy.get_default_config_name())[
            "cookie_jar"
        ],
        HttpOnlyCookieJar,
    )
