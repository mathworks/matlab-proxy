# Copyright 2023-2025 The MathWorks, Inc.

import asyncio
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pytest
from matlab_proxy import settings

from matlab_proxy import settings
from matlab_proxy.app_state import AppState
from matlab_proxy.constants import MWI_AUTH_TOKEN_NAME_FOR_HTTP
from matlab_proxy.util.mwi.exceptions import (
    LicensingError,
    MatlabError,
    MatlabInstallError,
)
from matlab_proxy.constants import (
    CONNECTOR_SECUREPORT_FILENAME,
    USER_CODE_OUTPUT_FILE_NAME,
)

from tests.unit.util import MockResponse
from tests.unit.test_constants import CHECK_MATLAB_STATUS_INTERVAL, FIVE_MAX_TRIES


@pytest.fixture
def sample_settings_fixture(tmp_path):
    """A pytest fixture which returns a dict containing sample settings for the AppState class.

    Args:
        tmp_path : Builtin pytest fixture

    Returns:
        dict: A dictionary of sample settings
    """
    tmp_file = tmp_path / "parent_1" / "parent_2" / "tmp_file.json"
    return {
        "error": None,
        "warnings": [],
        "matlab_config_file": tmp_file,
        "is_xvfb_available": True,
        "is_windowmanager_available": True,
        "mwi_server_url": "dummy",
        "mwi_logs_root_dir": Path(settings.get_mwi_config_folder(dev=True)),
        "app_port": 12345,
        "mwapikey": "asdf",
        "has_custom_code_to_execute": False,
        "mwi_idle_timeout": 100,
        "mwi_is_token_auth_enabled": False,
        "integration_name": "MATLAB Desktop",
    }


@pytest.fixture
async def app_state_fixture(sample_settings_fixture):
    """A pytest fixture which returns an instance of AppState class with no errors.

    Args:
        sample_settings_fixture (dict): A dictionary of sample settings to be used by

    Returns:
        AppState: An object of the AppState class
    """
    app_state = AppState(settings=sample_settings_fixture)
    app_state.processes = {"matlab": None, "xvfb": None}
    app_state.licensing = {"type": "existing_license"}

    yield app_state

    await app_state.stop_server_tasks()


@pytest.fixture
def sample_token_headers_fixture():
    return {MWI_AUTH_TOKEN_NAME_FOR_HTTP: "asdf"}


@pytest.fixture
def app_state_with_token_auth_fixture(
    app_state_fixture, sample_token_headers_fixture, tmp_path
):
    """Pytest fixture which returns AppState instance with token authentication enabled.

    Args:
        app_state_fixture (AppState): Pytest fixture
        tmp_path (str): Built-in pytest fixture

    Returns:
        (AppState, dict): Instance of the AppState class with token authentication enabled and token headers
    """
    tmp_matlab_ready_file = Path(tmp_path) / "tmp_file.txt"
    tmp_matlab_ready_file.touch()
    ((mwi_auth_token_name, mwi_auth_token_hash),) = sample_token_headers_fixture.items()
    app_state_fixture.matlab_session_files["matlab_ready_file"] = tmp_matlab_ready_file
    app_state_fixture.settings["mwi_is_token_auth_enabled"] = True
    app_state_fixture.settings["mwi_auth_token_name_for_env"] = mwi_auth_token_name
    app_state_fixture.settings["mwi_auth_token_name_for_http"] = (
        MWI_AUTH_TOKEN_NAME_FOR_HTTP
    )
    app_state_fixture.settings["mwi_auth_token_hash"] = mwi_auth_token_hash
    app_state_fixture.settings["mwi_server_url"] = "http://localhost:8888"

    return app_state_fixture


@pytest.fixture
async def mocker_os_patching_fixture(mocker, platform):
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
    mocker.patch("matlab_proxy.app_state.system.is_posix", return_value=False)

    if platform == "linux":
        mocker.patch("matlab_proxy.app_state.system.is_linux", return_value=True)
        mocker.patch("matlab_proxy.app_state.system.is_posix", return_value=True)

    elif platform == "windows":
        mocker.patch("matlab_proxy.app_state.system.is_windows", return_value=True)
        mocker.patch("matlab_proxy.app_state.system.is_posix", return_value=False)

    else:
        mocker.patch("matlab_proxy.app_state.system.is_mac", return_value=True)
        mocker.patch("matlab_proxy.app_state.system.is_posix", return_value=True)

    return mocker


@dataclass(frozen=True)
class Mock_xvfb:
    """An immutable dataclass representing a mocked Xvfb process"""

    returncode: Optional[int]
    pid: Optional[int]


@dataclass(frozen=True)
class Mock_matlab:
    """An immutable dataclass representing a mocked MATLAB process"""

    returncode: Optional[int]
    pid: Optional[int]

    def is_running(self) -> bool:
        return self.returncode is None

    def wait(self) -> int:
        return self.returncode


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
def test_unset_licensing(err, app_state_fixture, expected_err):
    """Test to check unset_liecnsing removes licensing from the AppState object

    Args:
        err (Exception): Custom exceptions defined in exceptions.py
        licensing (bool): Whether licensing info is removed
        expected_err (Exception): Expected exception
    """
    # Arrange
    app_state_fixture.error = err

    # Act
    app_state_fixture.unset_licensing()

    # Assert
    assert app_state_fixture.licensing == None
    assert type(app_state_fixture.error) is type(expected_err)


# config file is deleted when licensing info is not set i.e. set to None
def test_persist_licensing_when_licensing_info_is_not_set(app_state_fixture):
    """Test to check if data is not persisted to a file if licensing info is not present

    Args:
        tmp_path (Path): Built in pytest fixture
    """
    # Arrange
    # Nothing to arrange
    app_state_fixture.licensing = None

    # Act
    app_state_fixture.persist_config_data()

    # Assert
    assert os.path.exists(app_state_fixture.settings["matlab_config_file"]) is False


@pytest.mark.parametrize(
    "licensing_data",
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
def test_persist_config_data(licensing_data: dict, tmp_path):
    """Test to check if persist_licensing() writes data to the file system

    Args:
        data (dict): Represents matlab-proxy licensing data
        tmp_path : Built-in pytest fixture.
    """
    # Arrange
    tmp_file = tmp_path / "parent_1" / "parent_2" / "tmp_file.json"
    settings = {
        "matlab_config_file": tmp_file,
        "error": None,
        "matlab_version": None,
        "warnings": [],
        "mwi_idle_timeout": None,
    }
    app_state = AppState(settings=settings)
    app_state.licensing = licensing_data

    cached_data = {"licensing": licensing_data, "matlab": {"version": None}}

    # Act
    app_state.persist_config_data()
    with open(tmp_file, "r") as file:
        got = file.read()

    # Assert
    assert json.loads(got) == cached_data


validate_required_processes_test_data = [
    (None, None, "linux", False),  # xvfb is None == True
    (None, Mock_xvfb(None, 1), "linux", False),  # matlab is None == True
    (
        Mock_matlab(None, 1),
        Mock_xvfb(None, 1),
        "linux",
        True,
    ),  # All branches are skipped and nothing returned
    (
        Mock_matlab(None, 1),
        Mock_xvfb(123, 2),
        "linux",
        False,
    ),  # xvfb.returncode is not None == True
    (
        Mock_matlab(123, 1),
        Mock_xvfb(None, 2),
        "linux",
        False,
    ),  # matlab.returncode is not None == True
    (
        Mock_matlab(None, 1),
        None,
        "linux",
        True,
    ),  # Xvfb not found on path
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
        "xvfb_is_optional_matlab_starts_without_it",
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
    app_state_fixture.processes = {"matlab": matlab, "xvfb": xvfb}
    if not xvfb:
        app_state_fixture.settings["is_xvfb_available"] = False

    # Act
    actual = app_state_fixture._are_required_processes_ready()

    # Assert
    assert actual == expected


# The test: test_track_embedded_connector has been split into:
# 1) test_track_embedded_connector_posix: Test to check if stop_matlab is called on posix systems.
# 2) test_track_embedded_connector : Test to check if stop_matlab is not called in windows.

# In windows, errors are shown as UI windows and calling stop_matlab() if MATLAB had not started in
# PROCESS_TIMEOUT seconds would remove the window thereby leaving the user without knowing why MATLAB
# failed to start.


@pytest.mark.parametrize("platform", [("linux"), ("mac")])
async def test_track_embedded_connector_posix(
    mocker_os_patching_fixture, app_state_fixture
):
    """Test to check track_embedded_connector task for posix platforms.

    Checks if stop_matlab() has been called when the embedded connector doesn't respond
    even after PROCESS_TIMEOUT seconds of starting MATLAB.

    Args:
        mocker_os_patching_fixture (mocker): Custom pytest fixture for mocking
        app_state_fixture (AppState): Object of AppState class with defaults set
    """

    # Arrange
    # Patching embedded_connector_start_time to EPOCH+1 seconds and state to be "down".

    # For this test, the embedded_connector_start_time can be patched to ant value 600(default PROCESS_TIMEOUT) seconds
    # before the current time.

    # To always ensure that the time difference between the embedded_connector_start_time
    # and the current time is greater than PROCESS_TIMEOUT, the embedded_connector_start_time is patched to
    # EPOCH + 1 seconds so that the time_diff = current_time -  embedded_connector_start_time is greater
    # than PROCESS_TIMEOUT always evaluates to True.

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


@pytest.mark.parametrize("platform", ["windows"])
async def test_track_embedded_connector(mocker_os_patching_fixture, app_state_fixture):
    """Test to check track_embedded_connector task on windows.

    In windows, since errors are shown in native UI windows , calling stop_matlab() would remove them,
    thereby not knowing the error with which MATLAB failed to start.

    Hence, this test checks that stop_matlab() is not called.

    Args:
        mocker_os_patching_fixture (mocker): Custom pytest fixture for mocking
        app_state_fixture (AppState): Object of AppState class with defaults set
    """
    # Arrange
    # Patching embedded_connector_start_time to EPOCH+1 seconds and state to be "down".

    # For this test, the embedded_connector_start_time can be patched to any value 600(default PROCESS_TIMEOUT) seconds
    # before the current time.

    # To always ensure that the time difference between the embedded_connector_start_time
    # and the current time is greater than PROCESS_TIMEOUT, the embedded_connector_start_time is patched to
    # EPOCH + 1 seconds so that the time_diff = current_time -  embedded_connector_start_time is greater
    # than PROCESS_TIMEOUT always evaluates to True.

    mocker_os_patching_fixture.patch.object(
        app_state_fixture, "embedded_connector_start_time", new=float(1.0)
    )
    mocker_os_patching_fixture.patch.object(
        app_state_fixture, "embedded_connector_state", return_value="down"
    )

    spy = mocker_os_patching_fixture.spy(app_state_fixture, "stop_matlab")

    # Act

    # Unlike the posix test (test_track_embedded_connector_posix) where the task track_embedded_connector_state()
    # would exit automatically after stopping MATLAB, in windows, the task will never exit(until the user checks the error
    # manually and clicks on "Stop MATLAB").

    # So, the task is manually stopped by raising a timeout error(set to 3 seconds). This is a generous amount of
    # time for the error to be set as a MatlabError in CI systems.
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(
            app_state_fixture._AppState__track_embedded_connector_state(),
            timeout=3,  # timeout of 3 seconds to account for CI systems. This is to wait for the error to be set as MatlabError.
        )

    # Assert
    spy.assert_not_called()  # In windows, MATLAB process should not be stopped so that the UI error window is not closed.
    assert isinstance(app_state_fixture.error, MatlabError)


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


@pytest.mark.parametrize(
    "platform, expected_output",
    [("linux", "stdout"), ("windows", "file"), ("mac", "stdout")],
)
async def test_setup_env_for_matlab(
    mocker_os_patching_fixture, platform, expected_output, app_state_fixture, tmp_path
):
    """Test to check MW_DIAGNOSTIC_DEST is set appropriately for posix and non-posix systems

    Args:
        mocker_os_patching_fixture (mocker): Custom pytest fixture for mocking
        platform (str): string describing a platform
        app_state_fixture (AppState): Object of AppState class with defaults set
        tmp_path (Path): Built-in pytest fixture for temporary paths
    """

    # Arrange
    app_state_fixture.licensing = {"type": "existing_license"}
    app_state_fixture.settings = {"mwapikey": None, "matlab_display": ":1"}
    app_state_fixture.mwi_logs_dir = tmp_path
    mocker_os_patching_fixture.patch(
        "matlab_proxy.app_state.logger.isEnabledFor", return_value=True
    )

    # Act
    matlab_env = await app_state_fixture._AppState__setup_env_for_matlab()

    # Assert
    assert expected_output in matlab_env["MW_DIAGNOSTIC_DEST"]


async def test_requests_sent_by_matlab_proxy_have_headers(
    app_state_with_token_auth_fixture,
    sample_token_headers_fixture,
    mocker,
):
    """Test to check if token headers are included in requests sent by matlab-proxy when authentication is enabled.
    Test checks if the headers are included in the request to stop matlab and get connector status.

    Args:
        app_state_fixture_with_token_auth (AppState): Instance of AppState class with token authentication enabled
        sample_token_headers_fixture (dict): Dict which represents the token headers
        mocker : Built-in pytest fixture
    """
    # Arrange
    mock_resp = MockResponse(
        ok=True, payload={"messages": {"EvalResponse": [{"isError": None}]}}
    )
    mocked_req = mocker.patch("aiohttp.ClientSession.request", return_value=mock_resp)

    # Patching to make _are_required_processes_ready() to return True
    mocker.patch.object(
        AppState,
        "_are_required_processes_ready",
        return_value=True,
    )
    # Patching to make get_matlab_state() to return up
    mocker.patch.object(
        AppState,
        "get_matlab_state",
        return_value="up",
    )
    # Wait for _update_matlab_connector_status to run
    await asyncio.sleep(CHECK_MATLAB_STATUS_INTERVAL)

    # Act
    await app_state_with_token_auth_fixture._AppState__send_stop_request_to_matlab()

    # Assert

    # 1 request from _update_matlab_connector_status() and another from
    # /stop_matlab request
    connector_status_request_headers = list(mocked_req.call_args_list)[0].kwargs[
        "headers"
    ]
    send_stop_matlab_request_headers = list(mocked_req.call_args_list)[1].kwargs[
        "headers"
    ]
    assert sample_token_headers_fixture == connector_status_request_headers
    assert sample_token_headers_fixture == send_stop_matlab_request_headers


async def test_start_matlab_without_xvfb(app_state_fixture, mocker):
    """Test to check if Matlab process starts without throwing errors when Xvfb is not present

    Args:
        app_state_fixture (AppState): Object of AppState class with defaults set
        mocker : Built-in pytest fixture
    """
    # Arrange
    app_state_fixture.settings["is_xvfb_available"] = False
    mock_matlab = Mock_matlab(None, 1)

    # Starting asyncio tasks related to matlab is not required here as only Xvfb check is required.
    mocker.patch.object(
        AppState, "_AppState__start_matlab_process", return_value=mock_matlab
    )
    mocker.patch.object(
        AppState, "_AppState__matlab_stderr_reader_posix", return_value=None
    )
    mocker.patch.object(
        AppState, "_AppState__track_embedded_connector_state", return_value=None
    )
    mocker.patch.object(AppState, "_AppState__update_matlab_port", return_value=None)

    # Act
    await app_state_fixture.start_matlab()

    # Assert
    # Check if Xvfb has not started
    assert app_state_fixture.processes["xvfb"] is None
    # Check if Matlab started
    assert app_state_fixture.processes["matlab"] is mock_matlab


async def test_start_matlab_without_xvfb_and_matlab(app_state_fixture):
    """Test to check if MATLAB doesn't start and sets the error variable to MatlabInstallError when
    there is not MATLAB on system PATH

    Args:
        app_state_fixture (AppState): Object of AppState class with defaults set
    """
    # Arrange
    app_state_fixture.settings["is_xvfb_available"] = False
    app_state_fixture.settings["matlab_cmd"] = None

    # Act
    await app_state_fixture.start_matlab()

    # Assert
    # Check if Xvfb has not started
    assert app_state_fixture.processes["xvfb"] is None
    # Check if Matlab has not started
    assert app_state_fixture.processes["matlab"] is None
    # Check if MatlabInstallError is set as the error
    assert isinstance(app_state_fixture.error, MatlabInstallError)


@pytest.mark.parametrize(
    "is_desktop, client_id, is_client_id_present, expected_is_active_client",
    [
        (False, None, False, None),
        (False, "mock_id", False, None),
        (True, None, True, True),
        (True, "mock_id", False, True),
    ],
    ids=[
        "request_from_non-desktop_client",
        "request_from_non-desktop_client_having_mock_id",
        "request_from_desktop_client",
        "request_from_desktop_client_having_mock_id",
    ],
)
async def test_get_session_status(
    app_state_fixture,
    is_desktop,
    client_id,
    is_client_id_present,
    expected_is_active_client,
):
    """Test to check if correnct session response is returned based on various conditions.

    Args:
        app_state_fixture (AppState): Object of AppState class with defaults set
        is_desktop (bool): A flag indicating whether the client is a desktop client.
        client_id (str or None): The client ID. If None, a new client ID may be generated.
        is_client_id_present (bool): Indicates whether the expected value of client_id is string or not.
        expected_is_active_client (bool): Indicates the expected value of is_active_client

    """
    # The value of transfer_session is a Don't Care condition as initially the value of client_id is always None.
    output_client_id, output_is_active_client = app_state_fixture.get_session_status(
        is_desktop, client_id, transfer_session=False
    )
    assert isinstance(output_client_id, str) == is_client_id_present, (
        "Expected client_id to be a string got None"
        if is_client_id_present
        else "Expected client_id to be None got a string value"
    )
    assert (
        output_is_active_client == expected_is_active_client
    ), f"Expected is_active_client to be {expected_is_active_client} got {output_is_active_client}"
    # For clean up of task_detect_client_status
    app_state_fixture.active_client = None


async def test_get_session_status_can_transfer_session(app_state_fixture):
    """Test to check whether transer session changes client id to the new id

    Args:
        app_state_fixture (AppState): Object of AppState class with defaults set
    """
    app_state_fixture.active_client = "mock_id"
    app_state_fixture.get_session_status(
        is_desktop=True, client_id="new_id", transfer_session=True
    )
    assert app_state_fixture.active_client == "new_id"
    # For clean up of task_detect_client_status
    app_state_fixture.active_client = None


async def test_detect_active_client_status_can_reset_active_client(app_state_fixture):
    """Test to check whether the value of active client is being reset due to the client inactivity.

    Args:
        app_state_fixture (AppState): Object of AppState class with defaults set
    """
    app_state_fixture.active_client = "mock_id"
    await app_state_fixture.detect_active_client_status(
        sleep_time=0, max_inactive_count=0
    )
    assert (
        app_state_fixture.active_client == None
    ), f"Expected the active_client to be None"


@pytest.mark.parametrize(
    "session_file_count, has_custom_code_to_execute", [(2, True), (1, False)]
)
def test_create_logs_dir_for_MATLAB(
    app_state_fixture, session_file_count, has_custom_code_to_execute
):
    """Test to check create_logs_dir_for_MATLAB()

    Args:
        app_state_fixture (AppState): Object of AppState class with defaults set
    """
    # Arrange
    app_state_fixture.settings["has_custom_code_to_execute"] = (
        has_custom_code_to_execute
    )

    # Act
    app_state_fixture.create_logs_dir_for_MATLAB()

    # Assert
    for _, session_file_path in app_state_fixture.matlab_session_files.items():
        # Check session files are present in mwi logs directory
        assert app_state_fixture.mwi_logs_dir == Path(session_file_path).parent

    assert len(app_state_fixture.matlab_session_files) == session_file_count


async def test_check_idle_timer_started(app_state_fixture):
    """Test to check if the IDLE timer starts automatically

    Args:
        app_state_fixture (AppState): Object of AppState class with defaults set
    """
    # Arrange
    # Nothing to arrange

    # Act
    # constructor is called automatically

    # Assert
    assert app_state_fixture.is_idle_timeout_enabled is True
    assert "decrement_idle_timer" in app_state_fixture.server_tasks
    assert app_state_fixture.idle_timeout_lock is not None


async def test_reset_timer(app_state_fixture):
    """Test to check if the IDLE timer is reset to its initial value

    Args:
        app_state_fixture (AppState): Object of AppState class with defaults set
    """
    # Arrange
    # Sleep for 1 second for the decrement_timer task to decrease IDLE timer by
    # more than 1 second. This is for decreasing flakiness of this test on different platforms.
    await asyncio.sleep(CHECK_MATLAB_STATUS_INTERVAL + CHECK_MATLAB_STATUS_INTERVAL)

    # Act
    await app_state_fixture.reset_timer()

    # Assert
    assert (
        app_state_fixture.get_remaining_idle_timeout()
        == app_state_fixture.settings["mwi_idle_timeout"]
    )


async def test_decrement_timer(app_state_fixture):
    """Test to check if the IDLE timer value decrements automatically

    Args:
        app_state_fixture (AppState): Object of AppState class with defaults set
    """
    # Arrange
    # Nothing to arrange
    # decrement_timer task is started automatically by the constructor

    # Sleep for 1 second for the decrement_timer task to decrease IDLE timer by
    # more than 1 second. This is for decreasing flakiness of this test on different platforms.
    await asyncio.sleep(CHECK_MATLAB_STATUS_INTERVAL + CHECK_MATLAB_STATUS_INTERVAL)

    # Act
    # Nothing to act

    # Assert
    assert (
        app_state_fixture.get_remaining_idle_timeout()
        < app_state_fixture.settings["mwi_idle_timeout"]
    )


async def test_decrement_timer_runs_out(sample_settings_fixture, mocker):
    """Test to check if the IDLE timer eventually runs out.

    Args:
        app_state_fixture (AppState): Object of AppState class with defaults set
    """
    # Arrange
    # Set the IDLE timeout to a low value
    idle_timeout = 1
    sample_settings_fixture["mwi_idle_timeout"] = idle_timeout
    app_state = AppState(settings=sample_settings_fixture)
    app_state.processes = {"matlab": None, "xvfb": None}
    app_state.licensing = {"type": "existing_license"}

    # mock util.get_event_loop() to return a new event_loop for the test to assert
    mock_loop = asyncio.new_event_loop()
    mocker.patch("matlab_proxy.app_state.util.get_event_loop", return_value=mock_loop)

    # Act
    # Wait for a little more time than idle_timeout to decrease flakiness of this test on different platforms.
    # MATLAB state changes from down -> starting -> up -> down (idle timer runs out)
    await asyncio.sleep(idle_timeout * FIVE_MAX_TRIES)

    # Assert
    assert not mock_loop.is_running()
    assert app_state.get_matlab_state() == "down"

    # Cleanup
    mock_loop.stop()
    await app_state.stop_server_tasks()


@pytest.mark.parametrize(
    "connector_status, matlab_status",
    [("down", "starting"), ("up", "up")],
    ids=["connector_down", "connector_up"],
)
async def test_update_matlab_state_based_on_connector_state(
    app_state_fixture, connector_status, matlab_status
):
    """Test to check if MATLAB state is updated correctly based on connector state

    Args:
        app_state_fixture (AppState): Object of AppState class with defaults set
        connector_status (str): Represents connector status
        matlab_status (str): Represents expected MATLAB status
    """
    # Arrange
    app_state_fixture.embedded_connector_state = connector_status

    # Act
    await app_state_fixture._AppState__update_matlab_state_based_on_connector_state()

    # Assert
    assert app_state_fixture.get_matlab_state() == matlab_status


@pytest.mark.parametrize(
    "matlab_status, matlab_busy_status",
    [("starting", None), ("up", "busy"), ("up", "idle")],
    ids=["No response from busy status endpoint", "MATLAB is busy", "MATLAB is idle"],
)
async def test_update_matlab_state_using_busy_endpoint(
    mocker, app_state_fixture, matlab_status, matlab_busy_status
):
    """Test to check if MATLAB and its busy status updates correctly when the
    busy status endpoint is used.

    Args:
        mocker (mocker): Built-in pytest fixture
        app_state_fixture (AppState): Object of AppState class with defaults set
        matlab_status (str): Represents MATLAB status
        matlab_busy_status (str): Represents MATLAB busy status
    """
    # Arrange
    mocker.patch(
        "matlab_proxy.app_state.mwi.embedded_connector.request.get_busy_state",
        return_value=matlab_busy_status,
    )

    # Act
    await app_state_fixture._AppState__update_matlab_state_using_busy_status_endpoint()

    # Assert
    assert app_state_fixture.get_matlab_state() == matlab_status
    assert app_state_fixture.matlab_busy_state == matlab_busy_status


@pytest.mark.parametrize(
    "connector_status, matlab_status, matlab_busy_status",
    [("down", "starting", None), ("up", "up", "busy")],
    ids=["connector_down", "connector_up"],
)
async def test_update_matlab_state_using_ping_endpoint(
    mocker, app_state_fixture, connector_status, matlab_status, matlab_busy_status
):
    """Test to check if MATLAB and its busy status updates correctly when the
    ping endpoint is used.

    Args:
        mocker (mocker): Built-in pytest fixture
        app_state_fixture (AppState): Object of AppState class with defaults set
        connector_status (str): Represents Connector status
        matlab_status (str): Represents MATLAB status
        matlab_busy_status (str): Represents MATLAB busy status
    """
    # Arrange
    mocker.patch(
        "matlab_proxy.app_state.mwi.embedded_connector.request.get_state",
        return_value=connector_status,
    )

    # Act
    await app_state_fixture._AppState__update_matlab_state_using_ping_endpoint()

    # Assert
    assert app_state_fixture.get_matlab_state() == matlab_status
    assert app_state_fixture.matlab_busy_state == matlab_busy_status


async def test_update_matlab_state_based_on_endpoint_to_use_required_processes_not_ready(
    mocker, app_state_fixture
):
    """Test to check if MATLAB state is 'down' when the required processes are not ready

    Args:
        mocker (mocker): Built-in pytest fixture
        app_state_fixture (AppState): Object of AppState class with defaults set
    """
    # Arrange
    mocker.patch(
        "matlab_proxy.app_state.mwi.embedded_connector.request.get_state",
        return_value="up",
    )

    await app_state_fixture._AppState__update_matlab_state_based_on_endpoint_to_use(
        app_state_fixture._AppState__update_matlab_state_using_ping_endpoint
    )

    assert app_state_fixture.get_matlab_state() == "down"


async def test_update_matlab_state_based_on_endpoint_to_use_happy_path(
    mocker, tmp_path, app_state_fixture
):
    """Test to check if MATLAB state is 'starting' when the required processes
    are up but the ready file is not created yet.

    Args:
        mocker (mocker): Built-in pytest fixture
        tmp_path (Path): Built-in pytest fixture
        app_state_fixture (AppState): Object of AppState class with defaults set
    """
    # Arrange
    mocker.patch.object(
        AppState,
        "_are_required_processes_ready",
        return_value=True,
    )
    tmp_file = tmp_path / Path("dummy")
    tmp_file.touch()
    app_state_fixture.matlab_session_files["matlab_ready_file"] = tmp_file

    # Act
    await app_state_fixture._AppState__update_matlab_state_based_on_endpoint_to_use(
        app_state_fixture._AppState__update_matlab_state_using_ping_endpoint
    )

    # Assert
    await assert_matlab_state(app_state_fixture, "starting", FIVE_MAX_TRIES)


async def assert_matlab_state(app_state_fixture, expected_matlab_status, count):
    """Tries to assert the MATLAB state to expected_matlab_status for count times.
    Will raise Assertion error after.

    The count is needed to decrease flakiness of this tests when run on different platforms.

    Args:
        app_state_fixture (AppState): Instance of AppState class.
        expected_matlab_status (str): Expected MATLAB status
        count (int): Max tries for assertion before AssertionError is raised.

    Raises:
        AssertionError: Raised when assertion fails after 'count' tries
    """
    i = 0
    while i < count:
        try:
            assert app_state_fixture.get_matlab_state() == expected_matlab_status
            return

        except:
            await asyncio.sleep(CHECK_MATLAB_STATUS_INTERVAL)

        i += 1

    raise AssertionError(
        f"MATLAB status failed to change to '{expected_matlab_status}'"
    )


@pytest.mark.parametrize(
    "matlab_ready_file, expected_matlab_status",
    [
        (None, "down"),
        (Path("dummy"), "starting"),
    ],
    ids=[
        "no_matlab_ready_file_formed",
        "no_matlab_ready_file_created",
    ],
)
async def test_check_matlab_connector_status_auto_updates_based_on_matlab_ready_file(
    mocker, app_state_fixture, matlab_ready_file, expected_matlab_status
):
    """Test to check if the status of MATLAB is updated automatically

    Args:
        mocker (mocker): Built-in pytest fixture
        app_state_fixture (AppState): Object of AppState class with defaults set
        matlab_ready_file (Path): Path to the ready file
        expected_matlab_status (str): Expected MATLAB status
    """
    # Arrange
    mocker.patch.object(
        AppState,
        "_are_required_processes_ready",
        return_value=True,
    )
    app_state_fixture.matlab_session_files["matlab_ready_file"] = matlab_ready_file

    # Act
    # Nothing to act upon as the _update_matlab_state() is started automatically in the constructor.
    # Have to wait here for the atleast the same interval as the __update_matlab_state_based_on_endpoint_to_use()
    # for the MATLAB status to update from 'down'

    # Assert
    # MATLAB state should be 'down' first
    assert app_state_fixture.get_matlab_state() == "down"
    await asyncio.sleep(CHECK_MATLAB_STATUS_INTERVAL)

    await assert_matlab_state(app_state_fixture, expected_matlab_status, FIVE_MAX_TRIES)


async def test_update_matlab_state_switches_to_busy_endpoint(
    mocker, tmp_path, app_state_fixture
):
    """Test to check if the endpoint to determine MATLAB state changes from the ping
    endpoint to busy status endpoint after the first successful ping request.

    Args:
        mocker (mocker): Built-in pytest fixture
        tmp_path (Path): Built-in pytest fixture
        app_state_fixture (AppState): Object of AppState class with defaults set
    """
    # Arrange
    # Setup mocks for the first ping request to be successful
    mocker.patch.object(
        AppState,
        "_are_required_processes_ready",
        return_value=True,
    )
    mocker.patch(
        "matlab_proxy.app_state.mwi.embedded_connector.request.get_state",
        return_value="up",
    )
    tmp_file = tmp_path / Path("dummy")
    tmp_file.touch()
    app_state_fixture.matlab_session_files["matlab_ready_file"] = tmp_file
    mocked_busy_status_endpoint_function = mocker.patch.object(
        app_state_fixture, "_AppState__update_matlab_state_using_busy_status_endpoint"
    )

    # Act
    # Nothing to act upon as the _update_matlab_state() is started automatically in the constructor.
    # Have to wait here for the atleast the same interval as the __update_matlab_state_based_on_endpoint_to_use()
    # for the MATLAB status to update from 'down'

    # Wait for the ping endpoint request. Waiting for more time than what
    # is needed to decrease flakiness of this test on different platforms.
    await asyncio.sleep(1 * FIVE_MAX_TRIES)

    # Assert
    assert mocked_busy_status_endpoint_function.call_count > 1
