# Copyright 2024 The MathWorks, Inc.
from aiohttp import web

from matlab_proxy_manager.web.watcher import FileWatcher, start_watcher


# Test for FileWatcher.on_created
def test_on_created_calls_update_server_state(mocker):
    app = web.Application()
    file_watcher = FileWatcher(app, "/fake/data/dir")

    # Mock update_server_state to focus on testing on_created
    mock_update_server_state = mocker.patch.object(file_watcher, "update_server_state")

    # Simulate a file creation event
    event = mocker.MagicMock()
    file_watcher.on_created(event)

    # Assert update_server_state was called
    mock_update_server_state.assert_called_once()


# Test for FileWatcher.update_server_state
def test_update_server_state(mocker):
    app = web.Application()
    file_watcher = FileWatcher(app, "/fake/data/dir")

    # Mock FileRepository and its get_all method
    mock_storage = mocker.patch("matlab_proxy_manager.web.watcher.FileRepository")
    mock_storage_instance = mock_storage.return_value
    mock_storage_instance.get_all.return_value = {
        "server1": mocker.MagicMock(id="server1", as_dict=lambda: {"id": "server1"}),
        "server2": mocker.MagicMock(id="server2", as_dict=lambda: {"id": "server2"}),
    }

    # Call update_server_state
    file_watcher.update_server_state()

    # Assert that app["servers"] is updated correctly
    assert app["servers"] == {
        "server1": {"id": "server1"},
        "server2": {"id": "server2"},
    }


# Test for start_watcher
def test_start_watcher(mocker):
    app = web.Application()

    # Mock helpers.create_and_get_proxy_manager_data_dir
    mock_create_and_get_proxy_manager_data_dir = mocker.patch(
        "matlab_proxy_manager.utils.helpers.create_and_get_proxy_manager_data_dir",
        return_value="/fake/data/dir",
    )

    # Mock Observer and its methods
    mock_observer = mocker.patch("matlab_proxy_manager.web.watcher.Observer")
    mock_observer_instance = mock_observer.return_value

    # Call start_watcher
    observer = start_watcher(app)

    # Assert that the observer is configured correctly
    mock_observer_instance.schedule.assert_called_once()
    mock_observer_instance.start.assert_called_once()

    # Assert the correct directory is being watched
    assert observer == mock_observer_instance
    mock_create_and_get_proxy_manager_data_dir.assert_called_once()
