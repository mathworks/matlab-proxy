# Copyright 2024 The MathWorks, Inc.
import pytest

from matlab_proxy_manager.lib import api as api
from matlab_proxy_manager.storage.server import ServerProcess


@pytest.fixture
def mock_server_process(mocker):
    """Fixture to provide a mock ServerProcess."""
    mock = mocker.Mock(spec=ServerProcess)
    mock.id = "test_id"
    mock.as_dict.return_value = {"id": "test_id", "info": "mock_info"}
    return mock


# Test for _start_matlab_proxy with ValueError
@pytest.mark.asyncio
async def test_start_matlab_proxy_value_error():
    caller_id = "default"
    parent_id = "test_parent"
    is_isolated_matlab = True

    with pytest.raises(
        ValueError,
        match="Caller id cannot be default when isolated_matlab is set to true",
    ):
        await api._start_matlab_proxy(caller_id, parent_id, is_isolated_matlab)


# Test for _start_matlab_proxy with mock dependencies
@pytest.mark.asyncio
async def test_start_matlab_proxy_without_existing_server(mocker, mock_server_process):
    mock_delete_dangling_servers = mocker.patch(
        "matlab_proxy_manager.utils.helpers.delete_dangling_servers",
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
        "matlab_proxy_manager.lib.api._start_subprocess_and_check_for_readiness",
        return_value=mock_server_process,
    )

    caller_id = "test_caller"
    parent_id = "test_parent"
    is_isolated_matlab = False

    result = await api._start_matlab_proxy(caller_id, parent_id, is_isolated_matlab)

    mock_delete_dangling_servers.assert_awaited_once_with(None)
    mock_create_proxy_manager_dir.assert_called_once()
    mock_find_existing_server.assert_called_once()
    mock_start_subprocess.assert_awaited_once()
    mock_create_state_file.assert_called_once()

    assert result is not None
    assert result == mock_server_process.as_dict()


@pytest.mark.asyncio
async def test_start_matlab_proxy_with_existing_server(mocker, mock_server_process):
    mock_delete_dangling_servers = mocker.patch(
        "matlab_proxy_manager.utils.helpers.delete_dangling_servers",
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
        "matlab_proxy_manager.lib.api._start_subprocess_and_check_for_readiness",
        return_value=None,
    )

    caller_id = "test_caller"
    parent_id = "test_parent"
    is_isolated_matlab = False

    result = await api._start_matlab_proxy(caller_id, parent_id, is_isolated_matlab)

    mock_delete_dangling_servers.assert_awaited_once_with(None)
    mock_create_proxy_manager_dir.assert_called_once()
    mock_find_existing_server.assert_called_once()
    mock_start_subprocess.assert_not_called()
    mock_create_state_file.assert_called_once()

    assert result is not None
    assert result == mock_server_process.as_dict()


@pytest.mark.asyncio
async def test_start_matlab_proxy_returns_none_if_server_not_created(
    mocker, mock_server_process
):
    mock_delete_dangling_servers = mocker.patch(
        "matlab_proxy_manager.utils.helpers.delete_dangling_servers",
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
        "matlab_proxy_manager.lib.api._start_subprocess_and_check_for_readiness",
        return_value=None,
    )

    caller_id = "test_caller"
    parent_id = "test_parent"
    is_isolated_matlab = False

    result = await api._start_matlab_proxy(caller_id, parent_id, is_isolated_matlab)

    mock_delete_dangling_servers.assert_awaited_once_with(None)
    mock_create_proxy_manager_dir.assert_called_once()
    mock_find_existing_server.assert_called_once()
    mock_start_subprocess.assert_awaited_once()
    mock_create_state_file.assert_not_called()

    assert result is None


# Test for shutdown with missing arguments
@pytest.mark.asyncio
async def test_shutdown_missing_args(mocker, mock_server_process):
    mock_repo = mocker.patch(
        "matlab_proxy_manager.lib.api.FileRepository", autospec=True
    )
    mock_repo.return_value.get.return_value = ("path", mock_server_process)

    await api.shutdown(None, None, None)

    mock_repo.return_value.delete.assert_not_called()
    mock_server_process.shutdown.assert_not_called()


# Test for shutdown with valid arguments
@pytest.mark.asyncio
async def test_shutdown(mocker, mock_server_process, tmp_path):
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

    await api.shutdown(parent_pid, caller_id, mpm_auth_token)

    mock_repo.return_value.delete.assert_called_once_with(
        f"{parent_pid}_{caller_id}.info"
    )
    mock_server_process.shutdown.assert_called_once()
