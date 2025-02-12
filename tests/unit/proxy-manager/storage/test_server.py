# Copyright 2024-2025 The MathWorks, Inc.
from pathlib import Path

import pytest
from matlab_proxy_manager.storage.server import ServerProcess


@pytest.fixture
def server_process():
    data = {
        "server_url": "http://localhost:8888",
        "mwi_base_url": "/matlab",
        "headers": {"Dummy_header": "Dummy_value"},
        "errors": None,
        "pid": 1234,
        "parent_pid": 5678,
        "absolute_url": "http://localhost:8888/matlab",
        "id": "server123",
        "type": "shared",
        "mpm_auth_token": "auth_token",
    }
    return ServerProcess(**data)


@pytest.fixture
def mock_server_process(mocker):
    return mocker.patch("matlab_proxy_manager.storage.server.ServerProcess")


def test_shutdown_success(mocker, server_process):
    mock_response = mocker.MagicMock()
    mock_response.json.return_value = {"status": "success"}
    mock_req_retry_session = mocker.patch(
        "matlab_proxy_manager.utils.helpers.requests_retry_session"
    )
    mock_req_retry_session.return_value.delete.return_value = mock_response

    shutdown_response = server_process.shutdown()

    # Check that the delete request was made with the correct URL and headers
    mock_req_retry_session.return_value.delete.assert_called_once_with(
        url="http://localhost:8888/matlab/shutdown_integration",
        headers={"Dummy_header": "Dummy_value"},
    )
    assert shutdown_response == {"status": "success"}


def test_shutdown_exception(mocker, server_process):
    mock_req_retry_session = mocker.patch(
        "matlab_proxy_manager.utils.helpers.requests_retry_session"
    )
    mock_req_retry_session.return_value.delete.side_effect = Exception(
        "Server unreachable"
    )
    mock_psutil_process = mocker.patch(
        "psutil.Process", return_value=mocker.MagicMock()
    )

    shutdown_response = server_process.shutdown()

    # Check that the delete request was made with the correct URL and headers
    mock_req_retry_session.return_value.delete.assert_called_once_with(
        url="http://localhost:8888/matlab/shutdown_integration",
        headers={"Dummy_header": "Dummy_value"},
    )
    assert shutdown_response is None
    mock_psutil_process.return_value.kill.assert_called()


def test_server_process_instantiation_from_string_correctly():
    valid_string = """{
        "2252_default": {
            "server_url": "http://127.0.0.1:62582",
            "mwi_base_url": "/matlab/default",
            "headers": {"MWI-MPM-LOG-LEVEL": "DEBUG"},
            "errors": null,
            "pid": 25356,
            "parent_pid": 2252,
            "absolute_url": "http://127.0.0.1:62582/matlab/default",
            "id": "2252_default",
            "type": "shared",
            "mpm_auth_token": "92581d537c8a11bca759680e000a950498b6afd2ed7b55694433292e433ee8f9"
        }
        }"""
    process = ServerProcess.instantiate_from_string(valid_string)
    assert isinstance(process, ServerProcess)


def test_server_process_instantiation_from_invalid_string():
    with pytest.raises(ValueError):
        invalid_string = """{
            "2252_default": {
                "bad_server_url": "http://127.0.0.1:62582",
                "mwi_base_url": "/matlab/default"
            }
            }"""
        process = ServerProcess.instantiate_from_string(invalid_string)
        assert isinstance(process, ServerProcess)


def test_server_process_to_json():
    data = {
        "server_url": "http://localhost:8888",
        "mwi_base_url": "/matlab",
        "headers": {"Some_header": "header_value"},
        "errors": None,
        "pid": 1234,
        "parent_pid": 5678,
        "absolute_url": "http://localhost:8888/matlab",
        "id": "server123",
        "type": "shared",
        "mpm_auth_token": "auth_token",
    }
    sp = ServerProcess(**data)
    json_data = sp.as_dict()
    assert json_data == data


@pytest.mark.parametrize(
    "pid_exists, server_ready, expected_result",
    [
        (True, True, True),
        (False, True, False),
        (True, False, False),
        (False, False, False),
    ],
    ids=[
        "Both PID exists and server is ready",
        "PID does not exist",
        "Server is not ready",
        "Neither PID exists nor server is ready",
    ],
)
def test_is_server_alive(
    mocker, server_process, pid_exists, server_ready, expected_result
):
    mocker.patch("psutil.pid_exists", return_value=pid_exists)
    mocker.patch(
        "matlab_proxy_manager.utils.helpers.is_server_ready", return_value=server_ready
    )

    result = server_process.is_server_alive()

    assert result == expected_result


def test_is_server_alive_no_pid(server_process):
    server_process.pid = None
    result = server_process.is_server_alive()

    assert result is False


def test_find_existing_server_directory_does_not_exist(mocker):
    data_dir = "/fake/data/dir"
    key = "fake_key"
    mocker.patch.object(Path, "is_dir", return_value=False)

    result = ServerProcess.find_existing_server(data_dir, key)

    assert result is None


def test_find_existing_server_directory_exists_no_files(mocker):
    data_dir = "/fake/data/dir"
    key = "fake_key"

    mocker.patch.object(Path, "is_dir", return_value=True)
    mocker.patch.object(Path, "iterdir", return_value=[])

    result = ServerProcess.find_existing_server(data_dir, key)

    assert result is None


def test_find_existing_server_file_empty(mocker):
    data_dir = "/fake/data/dir"
    key = "fake_key"

    mocker.patch.object(Path, "is_dir", return_value=True)
    mocker.patch.object(Path, "iterdir", return_value=[Path("file1")])
    mock_open = mocker.patch("builtins.open", mocker.mock_open(read_data=""))

    result = ServerProcess.find_existing_server(data_dir, key)

    assert result is None

    # Ensure the file was opened and closed correctly
    mock_open.assert_called_once_with(Path("file1"), "r", encoding="utf-8")


def test_find_existing_server_instantiation_fails(mocker, mock_server_process):
    data_dir = "/fake/data/dir"
    key = "fake_key"

    mocker.patch.object(Path, "is_dir", return_value=True)
    mocker.patch.object(Path, "iterdir", return_value=[Path("file1")])
    mock_open = mocker.patch("builtins.open", mocker.mock_open(read_data="data"))
    mock_server_process.instantiate_from_string.return_value = None

    result = ServerProcess.find_existing_server(data_dir, key)

    assert result is None
    mock_open.assert_called_once_with(Path("file1"), "r", encoding="utf-8")


def test_find_existing_server_successful_instantiation(mocker, mock_server_process):
    data_dir = "/fake/data/dir"
    key = "fake_key"

    mocker.patch.object(Path, "is_dir", return_value=True)
    mocker.patch.object(Path, "iterdir", return_value=[Path("file1")])
    mock_open = mocker.patch("builtins.open", mocker.mock_open(read_data="data"))
    mock_server_process.instantiate_from_string.return_value = "ServerProcessInstance"

    result = ServerProcess.find_existing_server(data_dir, key)

    # Check the result
    assert result == "ServerProcessInstance"
    mock_open.assert_called_once_with(Path("file1"), "r", encoding="utf-8")


def test_find_existing_server_exception(mocker):
    data_dir = "/fake/data/dir"
    key = "fake_key"

    mocker.patch.object(Path, "is_dir", return_value=True)
    mocker.patch.object(Path, "iterdir", return_value=[Path("file1")])

    # Mock open to raise an OSError using pytest-mock
    mock_open = mocker.patch("builtins.open", mocker.mock_open(read_data="data"))
    mock_open.side_effect = OSError("File error")

    result = ServerProcess.find_existing_server(data_dir, key)

    assert result is None
    mock_open.assert_called_once_with(Path("file1"), "r", encoding="utf-8")
