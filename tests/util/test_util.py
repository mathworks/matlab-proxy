import asyncio
import psutil

from matlab_proxy import util


def test_get_supported_termination_signals():
    """Test to check for supported OS signals."""
    assert len(util.system.get_supported_termination_signals()) >= 1


def test_add_signal_handlers(loop):
    """Test to check if signal handlers are being added to asyncio loop

    Args:
        loop (asyncio loop): In built-in pytest fixture.
    """

    loop = util.add_signal_handlers(loop)

    # In posix systems, event loop is modified with new signal handlers
    if util.system.is_posix():
        assert loop._signal_handlers is not None
        assert loop._signal_handlers.items() is not None

    else:
        import signal

        # In a windows system, the signal handlers are added to the 'signal' package.
        for interrupt_signal in util.system.get_supported_termination_signals():
            assert signal.getsignal(interrupt_signal) is not None


def test_prettify():
    """Tests if text is prettified"""
    txt_arr = ["Hello world"]

    prettified_txt = util.prettify(boundary_filler="=", text_arr=txt_arr)

    assert txt_arr[0] in prettified_txt
    assert "=" in prettified_txt


async def test_get_child_processes(loop):
    """Tests if child processes are returned"""

    cmd = ["python"]
    proc = await asyncio.create_subprocess_shell(*cmd)

    children = util.get_child_processes(proc)

    assert len(children) > 0

    # Terminate the parent process (of type asyncio.subprocess.Process)
    proc.terminate()
    await proc.wait()

    # Terminate the child process (of type psutil.Process)
    children[0].terminate()
    children[0].wait()
