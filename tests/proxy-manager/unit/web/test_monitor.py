# Copyright 2024 The MathWorks, Inc.
import asyncio

import pytest
from pytest_mock import MockerFixture

from matlab_proxy_manager.web.monitor import OrphanedProcessMonitor


@pytest.mark.asyncio
async def test_parent_process_exists(mocker: MockerFixture):
    mock_does_process_exist = mocker.patch(
        "matlab_proxy_manager.utils.helpers.does_process_exist", return_value=True
    )
    app = {"parent_pid": 1234}
    monitor = OrphanedProcessMonitor(app, delay=0)

    # Run the start method for a limited time so that does_process_exist gets time to get called
    task = asyncio.create_task(monitor.start())
    await asyncio.sleep(0.1)
    task.cancel()

    # Assert that the helper was called
    mock_does_process_exist.assert_called_with(app["parent_pid"])


@pytest.mark.asyncio
async def test_parent_process_does_not_exist_triggers_shutdown(mocker: MockerFixture):
    mock_does_process_exist = mocker.patch(
        "matlab_proxy_manager.utils.helpers.does_process_exist", return_value=False
    )

    app = {"parent_pid": 1234}
    monitor = OrphanedProcessMonitor(app)

    mock_shutdown = mocker.patch.object(
        monitor, "shutdown", return_value=asyncio.Future()
    )
    mock_shutdown.return_value.set_result(None)

    # Run the start method which should trigger shutdown
    await monitor.start()

    # Assert that the process check was made and shutdown was triggered
    mock_does_process_exist.assert_called_with(app["parent_pid"])
    mock_shutdown.assert_awaited_once()


@pytest.mark.asyncio
async def test_exception_handling_in_start(mocker: MockerFixture):
    mock_does_process_exist = mocker.patch(
        "matlab_proxy_manager.utils.helpers.does_process_exist",
        side_effect=Exception("Test Exception"),
    )
    app = {"parent_pid": 1234}
    monitor = OrphanedProcessMonitor(app, delay=0)

    mock_shutdown = mocker.patch.object(
        monitor, "shutdown", return_value=asyncio.Future()
    )
    mock_shutdown.return_value.set_result(None)
    task = asyncio.create_task(monitor.start())
    await asyncio.sleep(0.1)  # Let it run a bit
    task.cancel()  # Cancel the task to stop the loop

    # Assert that the exception was handled and the loop continued
    mock_does_process_exist.assert_called_with(app["parent_pid"])
    mock_shutdown.assert_not_awaited()


@pytest.mark.asyncio
async def test_exception_handling_in_shutdown(mocker: MockerFixture):
    mocker.patch(
        "matlab_proxy_manager.web.app.SHUTDOWN_EVENT", return_value=asyncio.Event()
    )
    mock_shutdown_event_set = mocker.patch(
        "matlab_proxy_manager.web.app.SHUTDOWN_EVENT.set",
        side_effect=Exception("Test Exception"),
    )
    app = {"parent_pid": 1234}
    monitor = OrphanedProcessMonitor(app)

    # Call shutdown directly to test exception handling
    await monitor.shutdown()

    # Assert that the exception was handled
    mock_shutdown_event_set.assert_called_once()
