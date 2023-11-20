# Copyright 2023 The MathWorks, Inc.

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pytest

from matlab_proxy.app_state import AppState
from matlab_proxy.util.mwi.exceptions import LicensingError, MatlabError


@pytest.fixture
def app_state_fixture():
    """A pytest fixture which returns an instance of AppState class with no errors.

    Returns:
        AppState: An object of the AppState class
    """
    settings = {"error": None}
    app_state = AppState(settings=settings)
    return app_state


@pytest.fixture
def mocker_os_patching_fixture(mocker, platform):
    """A pytest fixture which patches the is_* functions in system.py module

    Args:
        mocker : Built in pytest fixture
        platform (str): A string representing "windows", "linux" or "mac"

    Returns:
        mocker: Built in pytest fixture with patched calls to system.py module.
    """
    mocker.patch("matlab_proxy.app_state.system.is_linux", return_value=False)
    mocker.patch("matlab_proxy.app_state.system.is_windows", return_value=False)
    mocker.patch("matlab_proxy.app_state.system.is_mac", return_value=False)
    if platform == "linux":
        mocker.patch("matlab_proxy.app_state.system.is_linux", return_value=True)
    elif platform == "windows":
        mocker.patch("matlab_proxy.app_state.system.is_windows", return_value=True)
    else:
        mocker.patch("matlab_proxy.app_state.system.is_mac", return_value=True)
    return mocker


@dataclass(frozen=True)
class Mock_xvfb:
    """An immutable dataclass representing a mocked Xvfb process"""

    returncode: Optional[int]


@dataclass(frozen=True)
class Mock_matlab:
    """An immutable dataclass representing a mocked MATLAB process"""

    returncode: Optional[int]


@pytest.mark.parametrize(
    "licensing, expected",
    [
        (None, False),
        ({"type": "nlm", "conn_str": "123@host"}, True),
        ({"type": "nlm"}, False),
        ({"type": "mhlm", "identity_token": "random_token"}, False),
        (
            {
                "type": "mhlm",
                "identity_token": "random_token",
                "source_id": "dummy_id",
                "expiry": "Jan 1, 1970",
                "entitlement_id": "123456",
            },
            True,
        ),
        ({"type": "existing_license"}, True),
        ({"type": "invalid_type"}, False),
    ],
    ids=[
        "None licensing",
        "happy path-nlm",
        "incomplete nlm data",
        "incomplete mhlm data",
        "happy path-mhlm",
        "happy path-existing license",
        "invalid license",
    ],
)
def test_is_licensed(app_state_fixture, licensing, expected):
    """Test to check is_licensed()

    Args:
        app_state_fixture (AppState): Object of AppState class with defaults set
        licensing (dict): Represents licensing information
        expected (bool): Expected return value.
    """
    # Arrange
    # Nothing to arrange

    # Act
    app_state_fixture.licensing = licensing

    # Assert
    assert app_state_fixture.is_licensed() == expected


@pytest.mark.parametrize(
    "err, expected_err",
    [
        (MatlabError(message="dummy error"), MatlabError(message="dummy")),
        (LicensingError(message="license issue"), None),
    ],
    ids=["Any error except licensing error", "licensing error"],
)
def test_unset_licensing(err, expected_err):
    """Test to check unset_liecnsing removes licensing from the AppState object

    Args:
        err (Exception): Custom exceptions defined in exceptions.py
        licensing (bool): Whether licensing info is removed
        expected_err (Exception): Expected exception
    """
    # Arrange
    settings = {"error": err}
    app_state = AppState(settings=settings)

    # Act
    app_state.unset_licensing()

    # Assert
    assert app_state.licensing == None
    assert type(app_state.error) is type(expected_err)


# config file is deleted when licensing info is not set i.e. set to None
def test_persist_licensing_when_licensing_info_is_not_set(tmp_path):
    """Test to check if data is not persisted to a file if licensing info is not present

    Args:
        tmp_path (Path): Built in pytest fixture
    """
    # Arrange
    tmp_file = tmp_path / "tmp_file.json"
    settings = {"matlab_config_file": tmp_file, "error": None}
    app_state = AppState(settings=settings)

    # Act
    app_state.persist_licensing()

    # Assert
    assert os.path.exists(tmp_file) is False


@pytest.mark.parametrize(
    "data",
    [
        ({"type": "nlm", "conn_str": "123@host"}),
        (
            {
                "type": "mhlm",
                "identity_token": "random_token",
                "source_id": "dummy_id",
                "expiry": "Jan 1, 1970",
                "entitlement_id": "123456",
            }
        ),
        ({"type": "existing_license"}),
    ],
    ids=["nlm type", "mhlm type", "existing license type"],
)
def test_persist_licensing(data: dict, tmp_path):
    """Test to check if persist_licensing() writes data to the file system

    Args:
        data (dict): Represents matlab-proxy licensing data
        tmp_path : Built-in pytest fixture.
    """
    # Arrange
    tmp_file = tmp_path / "parent_1" / "parent_2" / "tmp_file.json"
    settings = {"matlab_config_file": tmp_file, "error": None}
    app_state = AppState(settings=settings)
    app_state.licensing = data

    # Act
    app_state.persist_licensing()
    with open(tmp_file, "r") as file:
        got = file.read()

    # Assert
    assert json.loads(got) == data


validate_required_processes_test_data = [
    (None, None, "linux", False),  # xvfb is None == True
    (None, Mock_xvfb(None), "linux", False),  # matlab is None == True
    (
        Mock_matlab(None),
        Mock_xvfb(None),
        "linux",
        True,
    ),  # All branches are skipped and nothing returned
    (
        Mock_matlab(None),
        Mock_xvfb(123),
        "linux",
        False,
    ),  # xvfb.returncode is not None == True
    (
        Mock_matlab(123),
        Mock_xvfb(None),
        "linux",
        False,
    ),  # matlab.returncode is not None == True
]


@pytest.mark.parametrize(
    "matlab, xvfb, platform, expected",
    validate_required_processes_test_data,
    ids=[
        "processes_not_running",
        "matlab_not_running",
        "All_required_processes_running",
        "All_processes_running_with_xvfb_returning_non_zero_code",
        "All_processes_running_with_matlab_returning_non_zero_code",
    ],
)
def test_are_required_processes_ready(
    app_state_fixture, mocker_os_patching_fixture, matlab, xvfb, expected
):
    """Test to check if required processes are ready

    Args:
        app_state_fixture (AppState): Object of AppState class with defaults set
        mocker_os_patching_fixture (mocker): Custom pytest fixture for mocking
        matlab (Mock_matlab): Represents a mocked MATLAB process
        xvfb (Mock_xvfb): Represents a mocked Xvfb process
        expected (bool): Expected return value based on process return code
    """
    # Arrange
    # Nothing to arrange

    # Act
    actual = app_state_fixture._are_required_processes_ready(matlab, xvfb)

    # Assert
    assert actual == expected


get_matlab_status_based_on_connector_status_test_data = [
    ("up", True, "up"),
    ("down", True, "starting"),
    ("up", False, "starting"),
]


@pytest.mark.parametrize(
    "connector_status, ready_file_present, matlab_status",
    get_matlab_status_based_on_connector_status_test_data,
    ids=["connector_up", "connector_down", "connector_up_ready_file_not_present"],
)
async def test_get_matlab_status_based_on_connector_status(
    mocker, connector_status, ready_file_present, matlab_status
):
    """Test to check matlab status based on connector status

    Args:
        mocker : Built in pytest fixture.
        connector_status (str): Status of Embedded Connector.
        ready_file_present (bool): Represents if the ready file has been created or not.
        matlab_status (str): Represents the status of MATLAB process.
    """
    # Arrange
    mocker.patch(
        "matlab_proxy.app_state.mwi.embedded_connector.request.get_state",
        return_value=connector_status,
    )
    mocker.patch.object(Path, "exists", return_value=ready_file_present)
    settings = {
        "error": None,
        "mwi_server_url": "dummy",
        "mwi_is_token_auth_enabled": False,
    }
    app_state = AppState(settings=settings)
    app_state.matlab_session_files["matlab_ready_file"] = Path("dummy")

    # Act
    actual_matlab_status = await app_state._get_matlab_connector_status()

    # Assert
    assert actual_matlab_status == matlab_status


@pytest.mark.parametrize(
    "valid_processes, connector_status, expected",
    [
        (True, "up", "up"),
        (False, "up", "down"),
        (True, "down", "down"),
    ],
    ids=[
        "valid_processes_connector_up",
        "invalid_processes_connector_up",
        "valid_processes_connector_down",
    ],
)
async def test_get_matlab_state(
    app_state_fixture, mocker, valid_processes, connector_status, expected
):
    """Test to check get_matlab_state returns the correct MATLAB state based on the connector status

    Args:
        app_state_fixture (AppState): Object of AppState class with defaults set
        mocker : Built in pytest fixture
        valid_processes (bool): Represents if the processes are valid or not
        connector_status (str): Status of Embedded Connector.
        expected (str): Expected status of MATLAB process.
    """
    # Arrange
    mocker.patch.object(
        AppState,
        "_are_required_processes_ready",
        return_value=valid_processes,
    )
    mocker.patch.object(
        AppState,
        "_get_matlab_connector_status",
        return_value=connector_status,
    )

    # Act
    actual_state = await app_state_fixture.get_matlab_state()

    # Assert
    assert actual_state == expected


@pytest.mark.parametrize("platform", [("linux"), ("windows"), ("mac")])
async def test_track_embedded_connector(mocker_os_patching_fixture, app_state_fixture):
    """Test to check track_embedded_connector task

    Args:
        mocker_os_patching_fixture (mocker): Custom pytest fixture for mocking
        app_state_fixture (AppState): Object of AppState class with defaults set
    """

    # Arrange
    # patching embedded_connector_start_time to EPOCH+1 seconds and state to be "down"
    mocker_os_patching_fixture.patch.object(
        app_state_fixture, "embedded_connector_start_time", new=float(1.0)
    )
    mocker_os_patching_fixture.patch.object(
        app_state_fixture, "embedded_connector_state", return_value="down"
    )

    # verify that stop_matlab() is called once
    spy = mocker_os_patching_fixture.spy(app_state_fixture, "stop_matlab")

    # Act
    await app_state_fixture._AppState__track_embedded_connector_state()

    # Assert
    spy.assert_called_once()


@pytest.mark.parametrize(
    "env_var_name, filter_prefix, is_filtered",
    [("MWI_AUTH_TOKEN", "MWI_", None), ("MWIFOO_AUTH_TOKEN", "MWI_", "foo")],
    ids=["env_var_is_filtered", "env_var_is_not_filtered"],
)
def test_env_variables_filtration_for_xvfb_process(
    monkeypatch, env_var_name, filter_prefix, is_filtered
):
    """Test to check if __filter_env_variables filters environment variables with a certain prefix correctly.

    Args:
        monkeypatch (Object): Built-in pytest fixture for monkeypatching
        env_var_name (str): Name of the environment variable
        filter_prefix (str): Prefix to check for filtering
        is_filtered (bool): To check if the env variable with specified prefix is filtered.
    """
    # Arrange
    env_var = env_var_name
    monkeypatch.setenv(env_var, "foo")

    # Act
    filtered_env_vars: dict = AppState._AppState__filter_env_variables(
        os.environ, filter_prefix
    )

    # Assert
    assert filtered_env_vars.get(env_var) == is_filtered
