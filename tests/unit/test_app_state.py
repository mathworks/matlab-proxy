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
    settings = {"error": None}
    app_state = AppState(settings=settings)
    return app_state


@pytest.fixture
def mocker_os_patching_fixture(mocker, platform):
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
    returncode: Optional[int]


@dataclass(frozen=True)
class Mock_matlab:
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
    app_state_fixture.licensing = licensing
    assert app_state_fixture.is_licensed() == expected


@pytest.mark.parametrize(
    "err, licensing, expected_err",
    [
        (MatlabError(message="dummy error"), None, MatlabError(message="dummy")),
        (LicensingError(message="license issue"), None, None),
    ],
    ids=["Any error except licensing error", "licensing error"],
)
def test_unset_licensing(err, licensing, expected_err):
    settings = {"error": err}
    app_state = AppState(settings=settings)
    app_state.unset_licensing()
    assert app_state.licensing == licensing
    assert type(app_state.error) is type(expected_err)


# config file is deleted when licensing info is not set i.e. set to None
def test_persist_licensing_when_licensing_info_is_not_set(tmp_path):
    tmp_file = tmp_path / "tmp_file.json"
    settings = {"matlab_config_file": tmp_file, "error": None}
    app_state = AppState(settings=settings)
    app_state.persist_licensing()
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
    tmp_file = tmp_path / "parent_1" / "parent_2" / "tmp_file.json"
    settings = {"matlab_config_file": tmp_file, "error": None}
    app_state = AppState(settings=settings)
    app_state.licensing = data
    app_state.persist_licensing()
    with open(tmp_file, "r") as file:
        got = file.read()
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
    assert app_state_fixture._are_required_processes_ready(matlab, xvfb) == expected


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
    assert await app_state._get_matlab_connector_status() == matlab_status


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
    assert await app_state_fixture.get_matlab_state() == expected


@pytest.mark.parametrize("platform", [("linux"), ("windows"), ("mac")])
async def test_track_embedded_connector(mocker_os_patching_fixture, app_state_fixture):
    # patching embedded_connector_start_time to EPOCH+1 seconds and state to be "down"
    mocker_os_patching_fixture.patch.object(
        app_state_fixture, "embedded_connector_start_time", new=float(1.0)
    )
    mocker_os_patching_fixture.patch.object(
        app_state_fixture, "embedded_connector_state", return_value="down"
    )

    # verify that stop_matlab() is called once
    spy = mocker_os_patching_fixture.spy(app_state_fixture, "stop_matlab")
    await app_state_fixture._AppState__track_embedded_connector_state()
    spy.assert_called_once()


@pytest.mark.parametrize(
    "env_var_name, filter_prefix, is_filtered",
    [("MWI_AUTH_TOKEN", "MWI_", None), ("MWIFOO_AUTH_TOKEN", "MWI_", "foo")],
    ids=["env_var_is_filtered", "env_var_is_not_filtered"],
)
def test_env_variables_filtration_for_xvfb_process(
    monkeypatch, env_var_name, filter_prefix, is_filtered
):
    env_var = env_var_name
    monkeypatch.setenv(env_var, "foo")

    filtered_env_vars: dict = AppState._AppState__filter_env_variables(
        os.environ, filter_prefix
    )
    assert filtered_env_vars.get(env_var) == is_filtered
