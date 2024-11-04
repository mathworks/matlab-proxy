# Copyright 2024 The MathWorks, Inc.
import asyncio

from pytest_mock import MockerFixture

from matlab_proxy_manager.web.monitor import OrphanedProcessMonitor


async def test_parent_process_exists(mocker: MockerFixture):
    """
    Test that the OrphanedProcessMonitor continues running when the parent process exists.

    This test mocks the does_process_exist function to return True, simulating
    an existing parent process. It then verifies that the start method
    of OrphanedProcessMonitor continues running without triggering a shutdown.

    The test asserts that:
    1. The does_process_exist function is called with the correct parent PID.
    2. The monitor continues running for a short period without interruption.
    """
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


async def test_parent_process_does_not_exist_triggers_shutdown(mocker: MockerFixture):
    """
    Test that the OrphanedProcessMonitor triggers shutdown when the parent process does not exist.

    This test mocks the does_process_exist function to return False, simulating
    a non-existent parent process. It then verifies that the start method
    of OrphanedProcessMonitor calls the shutdown method when this condition is detected.

    The test asserts that:
    1. The does_process_exist function is called with the correct parent PID.
    2. The shutdown method of the monitor is called once.
    """
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


async def test_exception_handling_in_start(mocker: MockerFixture):
    """
    Test exception handling in the start method of OrphanedProcessMonitor.

    This test ensures that exceptions raised during the process existence check
    are properly handled without interrupting the monitoring loop.

    The test mocks the does_process_exist function to raise an exception,
    then verifies that the start method continues running without triggering
    a shutdown, demonstrating resilience to transient errors.
    """
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


async def test_exception_handling_in_shutdown(mocker: MockerFixture):
    """
    Test exception handling in the shutdown method of OrphanedProcessMonitor.

    This test ensures that exceptions raised during the shutdown process
    are properly handled without interrupting the shutdown procedure.

    The test mocks the shutdown_event and forces it to raise an exception
    when set. It then verifies that the shutdown method completes and
    that the event's set method was called despite the exception.
    """
    mock_event = mocker.Mock(spec=asyncio.Event())
    mock_event.set.side_effect = Exception("Test Exception")

    app = {"parent_pid": 1234, "shutdown_event": mock_event}
    monitor = OrphanedProcessMonitor(app)

    # Call shutdown directly to test exception handling
    await monitor.shutdown()

    # Assert that the exception was handled
    mock_event.set.assert_called_once()
