# Copyright 2020-2024 The MathWorks, Inc.

import asyncio
import pytest
import psutil

from matlab_proxy.util import get_child_processes, system, add_signal_handlers, prettify
from matlab_proxy.util import system
from matlab_proxy.util.mwi.exceptions import (
    UIVisibleFatalError,
)


def test_get_supported_termination_signals():
    """Test to check for supported OS signals."""
    assert len(system.get_supported_termination_signals()) >= 1


def test_add_signal_handlers(loop: asyncio.AbstractEventLoop):
    """Test to check if signal handlers are being added to asyncio loop

    Args:
        loop (asyncio loop): In built-in pytest fixture.
    """

    loop = add_signal_handlers(loop)

    # In posix systems, event loop is modified with new signal handlers
    if system.is_posix():
        assert loop._signal_handlers is not None
        assert loop._signal_handlers.items() is not None

    else:
        import signal

        # In a windows system, the signal handlers are added to the 'signal' package.
        for interrupt_signal in system.get_supported_termination_signals():
            assert signal.getsignal(interrupt_signal) is not None


def test_prettify():
    """Tests if text is prettified"""
    txt_arr = ["Hello world"]

    prettified_txt = prettify(boundary_filler="=", text_arr=txt_arr)

    assert txt_arr[0] in prettified_txt
    assert "=" in prettified_txt


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
