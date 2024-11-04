# Copyright 2024 The MathWorks, Inc.
import json
import pytest
from matlab_proxy_manager.storage.file_repository import FileRepository
from matlab_proxy_manager.storage.server import ServerProcess


@pytest.fixture
def mock_server_process(mocker):
    """Fixture to provide a mock ServerProcess."""
    mock = mocker.Mock(spec=ServerProcess)
    mock.id = "test_id"
    mock.as_dict.return_value = {"id": "test_id", "info": "mock_info"}
    return mock


def test_get_all(tmp_path, mocker):
    # Create a temporary directory structure
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # Create a mock info file
    info_file = data_dir / "mock_server.info"
    info_file.write_text("mock_server_data", encoding="utf-8")

    # Mock ServerProcess instantiation
    mock_instantiate = mocker.patch(
        "matlab_proxy_manager.storage.server.ServerProcess.instantiate_from_string"
    )
    mock_server = mocker.MagicMock(spec=ServerProcess)
    mock_instantiate.return_value = mock_server

    # Initialize FileRepository
    storage = FileRepository(data_dir)

    # Run the test
    servers = storage.get_all()

    # Assertions
    assert len(servers) == 1
    assert servers[str(info_file)] == mock_server
    mock_instantiate.assert_called_once_with("mock_server_data")


def test_get(tmp_path, mocker):
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # Create a mock info file
    info_file = data_dir / "mock_server.info"
    info_file.write_text("mock_server_data", encoding="utf-8")

    # Mock ServerProcess instantiation
    mock_instantiate = mocker.patch(
        "matlab_proxy_manager.storage.server.ServerProcess.instantiate_from_string"
    )
    mock_server = mocker.MagicMock(spec=ServerProcess)
    mock_instantiate.return_value = mock_server

    # Initialize FileRepository
    storage = FileRepository(data_dir)

    # Run the test
    file_path, server = storage.get("mock_server")

    # Assertions
    assert file_path == str(info_file)
    assert server == mock_server
    mock_instantiate.assert_called_once_with("mock_server_data")


def test_add(tmp_path, mock_server_process):
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # Initialize FileRepository
    storage = FileRepository(data_dir)

    # Run the test
    storage.add(mock_server_process, "mock_server")

    # Verify file creation
    server_dir = data_dir / mock_server_process.id
    server_file = server_dir / "mock_server.info"
    assert server_file.exists()

    # Verify file content
    with open(server_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data[mock_server_process.id] == mock_server_process.as_dict()


def test_delete(tmp_path, mocker):
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # Create a mock info file
    server_dir = data_dir / "parent_dir"
    server_dir.mkdir()
    info_file = server_dir / "mock_server.info"
    info_file.write_text("mock_server_data", encoding="utf-8")

    # Initialize FileRepository
    storage = FileRepository(data_dir)

    # Run the test
    mock_rmdir = mocker.patch("os.rmdir")
    storage.delete("mock_server.info")

    # Verify file deletion
    assert not info_file.exists()
    mock_rmdir.assert_called_once_with(str(server_dir))


def test_find_file_and_get_parent_exists(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # Create a mock info file
    server_dir = data_dir / "parent_dir"
    server_dir.mkdir()
    info_file = server_dir / "mock_server.info"
    info_file.touch()

    # Run the test
    full_path, parent_dir = FileRepository._find_file_and_get_parent(
        data_dir, "mock_server.info"
    )

    # Assertions for the case where the file exists
    assert full_path == str(info_file)
    assert parent_dir == str(server_dir)


def test_find_file_and_get_parent_not_exists(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # Create a mock info file
    server_dir = data_dir / "parent_dir"
    server_dir.mkdir()
    info_file = server_dir / "mock_server.info"
    info_file.touch()

    # Run the test
    full_path, parent_dir = FileRepository._find_file_and_get_parent(
        data_dir, "non_existing.info"
    )

    # Assertions for the case where the file does not exist
    assert full_path is None
    assert parent_dir is None
