from matlab_proxy import util


def test_is_python_version_newer_than_3_6():
    """Test to check python version is 3.7 or later"""
    assert util.is_python_version_newer_than_3_6() is not None


def test_get_supported_termination_signals():
    assert len(util.__get_supported_termination_signals()) >= 1


def test_add_signal_handlers(loop):
    """Test to check if signal handlers are being added to asyncio loop

    Args:
        loop (asyncio loop): In built-in pytest fixture.
    """

    loop = util.add_signal_handlers(loop)
    assert loop._signal_handlers is not None
    assert loop._signal_handlers.items() is not None
