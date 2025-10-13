# Copyright 2020-2025 The MathWorks, Inc.

import asyncio
import pytest
import psutil

import inspect

from matlab_proxy import util
from matlab_proxy.util import get_child_processes, system, add_signal_handlers
from matlab_proxy.util import system
from matlab_proxy.util.mwi.exceptions import (
    UIVisibleFatalError,
)


def test_get_supported_termination_signals():
    """Test to check for supported OS signals."""
    assert len(system.get_supported_termination_signals()) >= 1


def test_add_signal_handlers():
    """Test to check if signal handlers are being added to asyncio event_loop"""

    test_loop = asyncio.new_event_loop()
    test_loop = add_signal_handlers(test_loop)
    try:
        # In posix systems, event loop is modified with new signal handlers
        if system.is_posix():
            assert test_loop._signal_handlers is not None
            # Check that the signal handlers dictionary is not empty
            assert len(test_loop._signal_handlers) > 0

        else:
            import signal

            # In a windows system, the signal handlers are added to the 'signal' package.
            for interrupt_signal in system.get_supported_termination_signals():
                assert signal.getsignal(interrupt_signal) is not None

    finally:
        test_loop.close()


def test_get_child_processes_no_children_initially(mocker):
    import time

    # Create mock processes
    mock_parent_process_psutil = mocker.MagicMock(spec=psutil.Process)
    mock_child_processes = [mocker.MagicMock(spec=psutil.Process) for _ in range(2)]

    # Mock the Process class from psutil
    mocker.patch("psutil.Process", return_value=mock_parent_process_psutil)
    mock_parent_process_psutil.is_running.return_value = True

    # Function that changes the behavior of .children() after a delay
    def children_side_effect(*args, **kwargs):
        # Wait for a specific time to simulate delay in the child process being present
        time.sleep(0.4)
        return mock_child_processes

    mock_parent_process_psutil.children.side_effect = children_side_effect

    # Create a mock for asyncio.subprocess.Process with a dummy pid
    parent_process = mocker.MagicMock(spec=asyncio.subprocess.Process)
    parent_process.pid = 12345

    # Call the function with the mocked parent process
    child_processes = get_child_processes(parent_process)

    # Assert that the return value is our list of mock child processes
    assert child_processes == mock_child_processes

    # Assert that is_running and children methods were called on the mock
    mock_parent_process_psutil.children.assert_called_with(recursive=False)


def test_get_child_processes_no_children(mocker):
    # Create a mock for asyncio.subprocess.Process with a dummy pid
    parent_process = mocker.MagicMock(spec=asyncio.subprocess.Process)
    parent_process.pid = 12345

    # Mock the Process class from psutil
    mock_parent_process_psutil = mocker.MagicMock(spec=psutil.Process)
    mocker.patch("psutil.Process", return_value=mock_parent_process_psutil)
    mock_parent_process_psutil.is_running.return_value = True
    mock_parent_process_psutil.children.return_value = []

    # Call the function with the mocked parent process
    with pytest.raises(UIVisibleFatalError):
        get_child_processes(parent_process)


def test_get_child_processes_with_children(mocker):
    # Create mock processes
    mock_parent_process_psutil = mocker.MagicMock(spec=psutil.Process)
    mock_child_process = mocker.MagicMock(spec=psutil.Process)

    # Mock the Process class from psutil
    mocker.patch("psutil.Process", return_value=mock_parent_process_psutil)
    mock_parent_process_psutil.is_running.return_value = True

    # Mock a list of child processes that psutil would return
    mock_parent_process_psutil.children.return_value = [mock_child_process]

    # Create a mock for asyncio.subprocess.Process with a dummy pid
    parent_process = mocker.MagicMock(spec=asyncio.subprocess.Process)
    parent_process.pid = 12345

    # Call the function with the mocked parent process
    child_processes = get_child_processes(parent_process)

    # Assert that the returned value is a list containing the mock child process
    assert child_processes == [mock_child_process]


def test_get_child_processes_parent_not_running(mocker):
    # Mock the Process class from psutil
    mock_parent_process_psutil = mocker.MagicMock(spec=psutil.Process)
    mocker.patch("psutil.Process", return_value=mock_parent_process_psutil)
    mock_parent_process_psutil.is_running.return_value = False

    # Create a mock for asyncio.subprocess.Process with a dummy pid
    parent_process = mocker.MagicMock(spec=asyncio.subprocess.Process)
    parent_process.pid = 12345

    # Calling the function with a non-running parent process should raise an AssertionError
    with pytest.raises(
        AssertionError,
        match="Can't check for child processes as the parent process is no longer running.",
    ):
        get_child_processes(parent_process)


def test_get_caller_name():
    """Test to check if caller name is not empty"""
    # Arrange

    # Act
    caller_name = util.get_caller_name()

    # Assert
    assert caller_name is not None


@pytest.fixture
def tracking_lock():
    """Pytest fixture which returns an instance of TrackingLock for testing purposes."""
    return util.TrackingLock("test_purpose")


async def test_TrackingLock(tracking_lock):
    """Test to check various methods of TrackingLock class

    Args:
        tracking_lock (TrackingLock): Pytest fixture
    """
    name_of_current_fn = inspect.currentframe().f_code.co_name

    await tracking_lock.acquire()
    assert tracking_lock.acquired_by == name_of_current_fn
    assert tracking_lock.locked()

    await tracking_lock.release()
    tracking_lock.acquired_by is None
    assert not tracking_lock.locked()

    assert tracking_lock.purpose is not None


async def test_validate_lock_for_caller_when_not_locked(tracking_lock):
    """Test to check if validate_lock_for_caller returns False when the lock is not acquired

    Args:
        tracking_lock (TrackingLock): Pytest fixture
    """
    assert not tracking_lock.validate_lock_for_caller("some_caller")


async def test_validate_lock_for_caller_happy_path(tracking_lock):
    """Test to check if validate_lock_for_caller returns True when the lock was acquired by the
    same function as the caller.

    Args:
        tracking_lock (TrackingLock): Pytest fixture
    """
    name_of_current_fn = inspect.currentframe().f_code.co_name

    await tracking_lock.acquire()
    assert tracking_lock.validate_lock_for_caller(name_of_current_fn)
    await tracking_lock.release()


async def test_validate_lock_for_caller_lock_acquired_by_other_function(tracking_lock):
    """Test to check if validate_lock_for_caller returns False when the lock was acquired by
    some other function

    Args:
        tracking_lock (TrackingLock): Pytest fixture
    """
    # Arrange
    name_of_current_fn = inspect.currentframe().f_code.co_name

    # Acquire lock inside a nested function
    def nested_fn():
        tracking_lock.acquire()

    # Act
    nested_fn()

    # Assert
    assert not tracking_lock.validate_lock_for_caller(name_of_current_fn)
