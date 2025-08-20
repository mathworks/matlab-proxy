# Copyright 2024-2025 The MathWorks, Inc.
import pytest

from matlab_proxy_manager.lib import api as mpm_api
from matlab_proxy_manager.storage.server import ServerProcess
from matlab_proxy_manager.utils import exceptions


@pytest.fixture
def mock_server_process(mocker):
    """Fixture to provide a mock ServerProcess."""
    mock = mocker.Mock(spec=ServerProcess)
    mock.id = "test_id"
    mock.as_dict.return_value = {"id": "test_id", "info": "mock_info"}
    return mock


async def test_start_matlab_proxy_value_error():
    """
    Test case for starting a MATLAB proxy with a ValueError.

    This test verifies that the _start_matlab_proxy function raises a ValueError
    when the caller_id is "default" and is_shared_matlab is set to False. It
    checks if the correct error message is raised.
    """
    caller_id = "default"
    parent_id = "test_parent"
    is_shared_matlab = False

    with pytest.raises(
        ValueError,
        match="Caller id cannot be default when matlab proxy is not shareable",
    ):
        await mpm_api._start_matlab_proxy(
            caller_id=caller_id, ctx=parent_id, is_shared_matlab=is_shared_matlab
        )


async def test_start_matlab_proxy_without_existing_server(mocker):
    """
    Test case for starting a MATLAB proxy without an existing server.

    This test mocks various dependencies and verifies the behavior of the
    _start_matlab_proxy function when no existing server is found. It checks
    if the function correctly creates a new server process and returns its
    information.
    """
    mock_delete_dangling_servers = mocker.patch(
        "matlab_proxy_manager.utils.helpers._are_orphaned_servers_deleted",
        return_value=True,
    )
    mock_create_state_file = mocker.patch(
        "matlab_proxy_manager.utils.helpers.create_state_file", return_value=None
    )
    mock_create_proxy_manager_dir = mocker.patch(
        "matlab_proxy_manager.utils.helpers.create_and_get_proxy_manager_data_dir",
        return_value=None,
    )
    mock_find_existing_server = mocker.patch(
        "matlab_proxy_manager.storage.server.ServerProcess.find_existing_server",
        return_value=None,
    )
    mock_start_subprocess = mocker.patch(
        "matlab_proxy_manager.lib.api._start_subprocess",
        return_value=(1, "url"),
    )
    mock_check_readiness = mocker.patch(
        "matlab_proxy_manager.lib.api._check_for_process_readiness", return_value=None
    )

    parent_id = "test_parent"

    result = await mpm_api.start_matlab_proxy_for_jsp(
        parent_id=parent_id, is_shared_matlab=True, mpm_auth_token=""
    )

    mock_delete_dangling_servers.assert_called_once_with(parent_id)
    mock_create_proxy_manager_dir.assert_called_once()
    mock_find_existing_server.assert_called_once()
    mock_start_subprocess.assert_awaited_once()
    mock_create_state_file.assert_called_once()
    mock_check_readiness.assert_called_once()

    assert result is not None
    assert result.get("pid") == "1"
    assert result.get("server_url") == "url"


async def test_start_matlab_proxy_with_existing_server(mocker, mock_server_process):
    """
    Test case for starting a MATLAB proxy with an existing server.

    This test mocks various dependencies and verifies the behavior of the
    _start_matlab_proxy function when an existing server is found. It checks
    if the function correctly returns the existing server's information
    without starting a new subprocess.
    """
    mock_delete_dangling_servers = mocker.patch(
        "matlab_proxy_manager.utils.helpers._are_orphaned_servers_deleted",
        return_value=None,
    )
    mock_create_state_file = mocker.patch(
        "matlab_proxy_manager.utils.helpers.create_state_file", return_value=None
    )
    mock_create_proxy_manager_dir = mocker.patch(
        "matlab_proxy_manager.utils.helpers.create_and_get_proxy_manager_data_dir",
        return_value=None,
    )
    mock_find_existing_server = mocker.patch(
        "matlab_proxy_manager.storage.server.ServerProcess.find_existing_server",
        return_value=mock_server_process,
    )
    mock_start_subprocess = mocker.patch(
        "matlab_proxy_manager.lib.api._start_subprocess",
        return_value=(1, "url"),
    )

    parent_id = "test_parent"

    result = await mpm_api.start_matlab_proxy_for_jsp(
        parent_id=parent_id, is_shared_matlab=True, mpm_auth_token=""
    )

    mock_delete_dangling_servers.assert_called_once_with(parent_id)
    mock_create_proxy_manager_dir.assert_called_once()
    mock_find_existing_server.assert_called_once()
    mock_start_subprocess.assert_not_called()
    mock_create_state_file.assert_called_once()

    assert result is not None
    assert result == mock_server_process.as_dict()


async def test_start_matlab_proxy_returns_error_if_server_not_created(
    mocker, mock_server_process
):
    """
    Test case for starting a MATLAB proxy when server creation fails.

    This test mocks various dependencies and verifies the behavior of the
    _start_matlab_proxy function when no existing server is found and
    a new server cannot be created. It checks if the function correctly
    returns None and calls the expected methods.
    """
    mock_delete_dangling_servers = mocker.patch(
        "matlab_proxy_manager.utils.helpers._are_orphaned_servers_deleted",
        return_value=None,
    )
    mock_create_state_file = mocker.patch(
        "matlab_proxy_manager.utils.helpers.create_state_file", return_value=None
    )
    mock_create_proxy_manager_dir = mocker.patch(
        "matlab_proxy_manager.utils.helpers.create_and_get_proxy_manager_data_dir",
        return_value=None,
    )
    mock_find_existing_server = mocker.patch(
        "matlab_proxy_manager.storage.server.ServerProcess.find_existing_server",
        return_value=None,
    )
    mock_start_subprocess = mocker.patch(
        "matlab_proxy_manager.lib.api._start_subprocess"
    )
    mock_start_subprocess.side_effect = exceptions.ProcessStartError(
        extra_info="Server creation failed"
    )

    caller_id = "test_caller"
    parent_id = "test_parent"
    is_shared_matlab = True

    server_process = await mpm_api._start_matlab_proxy(
        caller_id=caller_id, ctx=parent_id, is_shared_matlab=is_shared_matlab
    )

    mock_delete_dangling_servers.assert_called_once_with(parent_id)
    mock_create_proxy_manager_dir.assert_called_once()
    mock_find_existing_server.assert_called_once()
    mock_start_subprocess.assert_awaited_once()
    mock_create_state_file.assert_not_called()

    assert isinstance(server_process, dict)
    assert len(server_process.get("errors")) == 1
    assert "Server creation failed" in server_process.get("errors")[0]


async def test_matlab_proxy_is_cleaned_up_if_server_was_not_ready(mocker):
    """
    Test case for cleaning up MATLAB proxy when server is not ready.

    This test mocks various dependencies and verifies the behavior of the
    _start_matlab_proxy function when no existing server is found and
    a new server is created but not ready. It checks if the function correctly
    returns None, calls the expected methods, and cleans up the server.
    """
    mock_find_existing_server = mocker.patch(
        "matlab_proxy_manager.storage.server.ServerProcess.find_existing_server",
        return_value=None,
    )
    mock_shutdown = mocker.patch(
        "matlab_proxy_manager.storage.server.ServerProcess.shutdown",
        return_value=None,
    )
    mock_delete_dangling_servers = mocker.patch(
        "matlab_proxy_manager.utils.helpers._are_orphaned_servers_deleted",
        return_value=None,
    )
    mock_create_state_file = mocker.patch(
        "matlab_proxy_manager.utils.helpers.create_state_file", return_value=None
    )
    mock_create_proxy_manager_dir = mocker.patch(
        "matlab_proxy_manager.utils.helpers.create_and_get_proxy_manager_data_dir",
        return_value=None,
    )
    mock_is_server_ready = mocker.patch(
        "matlab_proxy_manager.utils.helpers.is_server_ready", return_value=False
    )
    mock_prep_cmd_and_env = mocker.patch(
        "matlab_proxy_manager.lib.api._prepare_cmd_and_env_for_matlab_proxy",
        return_value=([], {}),
    )
    mock_start_subprocess = mocker.patch(
        "matlab_proxy_manager.lib.api._start_subprocess",
        return_value=(1, "dummy"),
    )

    caller_id = "test_caller"
    parent_id = "test_parent"
    is_shared_matlab = True

    server_process = await mpm_api._start_matlab_proxy(
        caller_id=caller_id, ctx=parent_id, is_shared_matlab=is_shared_matlab
    )

    mock_delete_dangling_servers.assert_called_once_with(parent_id)
    mock_create_proxy_manager_dir.assert_called_once()
    mock_find_existing_server.assert_called_once()
    mock_create_state_file.assert_not_called()
    mock_prep_cmd_and_env.assert_called_once()
    mock_start_subprocess.assert_awaited_once()
    mock_is_server_ready.assert_called_once()
    mock_shutdown.assert_called_once()

    assert isinstance(server_process, dict)
    assert len(server_process.get("errors")) == 1
    assert "MATLAB Proxy Server unavailable" in server_process.get("errors")[0]


# Test for shutdown with missing arguments
async def test_shutdown_missing_args(mocker, mock_server_process):
    """
    Test the shutdown function with missing arguments.

    This test mocks the necessary dependencies and verifies that the shutdown
    function behaves correctly when called with None values for all arguments.

    Args:
        mocker: pytest-mock fixture for mocking dependencies
        mock_server_process: mock object for the server process

    The test checks if:
    1. The delete method is not called on the repository
    2. The shutdown method is not called on the server process
    """
    mock_repo = mocker.patch(
        "matlab_proxy_manager.lib.api.FileRepository", autospec=True
    )
    mock_repo.return_value.get.return_value = ("path", mock_server_process)

    await mpm_api.shutdown(None, None, None)

    mock_repo.return_value.delete.assert_not_called()
    mock_server_process.shutdown.assert_not_called()


# Test for shutdown with valid arguments
async def test_shutdown(mocker, mock_server_process, tmp_path):
    """
    Test the shutdown function of the API.

    This test mocks the necessary dependencies and verifies that the shutdown
    function correctly deletes the server process information and calls the
    shutdown method on the server process.

    Args:
        mocker: pytest-mock fixture for mocking dependencies
        mock_server_process: mock object for the server process
        tmp_path: pytest fixture for creating a temporary directory

    The test checks if:
    1. The correct file is deleted from the repository
    2. The shutdown method is called on the server process
    """
    mock_repo = mocker.patch(
        "matlab_proxy_manager.lib.api.FileRepository", autospec=True
    )
    mock_helpers = mocker.patch("matlab_proxy_manager.lib.api.helpers", autospec=True)
    mock_server_process.mpm_auth_token = "valid_token"
    mock_helpers.create_and_get_proxy_manager_data_dir.return_value = tmp_path
    mock_helpers.is_only_reference.return_value = True
    mock_repo.return_value.get.return_value = ("path", mock_server_process)

    parent_pid = "parent_pid"
    caller_id = "caller_id"
    mpm_auth_token = "valid_token"

    await mpm_api.shutdown(parent_pid, caller_id, mpm_auth_token)

    mock_repo.return_value.delete.assert_called_once_with(
        f"{parent_pid}_{caller_id}.info"
    )
    mock_server_process.shutdown.assert_called_once()
