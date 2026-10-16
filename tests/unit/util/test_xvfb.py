# Copyright 2026 The MathWorks, Inc.

import pytest

from matlab_proxy.util import xvfb
from matlab_proxy.util import system
from matlab_proxy.util.mwi.exceptions import XvfbError

"""This file tests methods defined in xvfb.py file
"""


@pytest.fixture(autouse=True)
def mock_is_linux(mocker):
    """xvfb.start() asserts it is only invoked on Linux; force that here so the
    launch logic can be exercised regardless of the host OS."""
    mocker.patch("matlab_proxy.util.xvfb.system.is_linux", return_value=True)


@pytest.fixture(name="mock_spawn")
def mock_spawn_fixture(mocker):
    """Stubs out the pipe/command builder and the low-level spawn so start() can be
    tested without launching a real Xvfb. Returns the patched spawn mock."""
    mocker.patch(
        "matlab_proxy.util.xvfb._create_xvfb_cmd", return_value=(["Xvfb"], (3, 4))
    )
    fake_process = mocker.MagicMock(pid=1234)
    mock = mocker.patch(
        "matlab_proxy.util.xvfb._create_xvfb_process", return_value=(fake_process, "2")
    )
    mock.fake_process = fake_process
    return mock


def test_is_available_true(mocker):
    mocker.patch("shutil.which", return_value="/usr/bin/Xvfb")
    assert xvfb.is_available() is True


def test_is_available_false(mocker):
    mocker.patch("shutil.which", return_value=None)
    assert xvfb.is_available() is False


async def test_asserts_on_non_linux(mocker):
    """xvfb.start() must refuse to run on non-Linux systems."""
    mocker.patch("matlab_proxy.util.xvfb.system.is_linux", return_value=False)
    with pytest.raises(AssertionError):
        await xvfb.start()


async def test_start_returns_none_when_not_installed(mocker):
    """With Xvfb not on PATH, start() warns and returns None (MATLAB runs headless)."""
    mocker.patch("shutil.which", return_value=None)
    assert await xvfb.start() is None


async def test_start_returns_process_and_display(mocker, mock_spawn):
    """On success, start() returns the process and a ':'-prefixed display."""
    mocker.patch("shutil.which", return_value="/usr/bin/Xvfb")

    result = await xvfb.start()

    assert result == (mock_spawn.fake_process, ":2")


async def test_start_raises_when_installed_but_fails(mocker, mock_spawn):
    """An installed Xvfb that fails to launch surfaces as XvfbError."""
    mocker.patch("shutil.which", return_value="/usr/bin/Xvfb")
    mock_spawn.side_effect = XvfbError("boom")

    with pytest.raises(XvfbError):
        await xvfb.start()


async def test_start_filters_mwi_env(mocker, monkeypatch, mock_spawn):
    """start() must not leak matlab-proxy's own MWI_-prefixed env into Xvfb."""
    mocker.patch("shutil.which", return_value="/usr/bin/Xvfb")
    monkeypatch.setenv("MWI_AUTH_TOKEN", "secret")
    monkeypatch.setenv("PATH_LIKE", "keep-me")

    await xvfb.start()

    env = mock_spawn.call_args.args[2]
    assert "MWI_AUTH_TOKEN" not in env
    assert env.get("PATH_LIKE") == "keep-me"


@pytest.mark.skipif(
    not system.is_linux(),
    reason="Xvfb is only required on linux based operating systems",
)
async def test_start_launches_unique_displays():
    """Two Xvfb processes started with -displayfd get unique display numbers."""
    if not xvfb.is_available():
        pytest.skip("Xvfb is not installed on this system")

    result_1 = await xvfb.start()
    result_2 = await xvfb.start()

    assert result_1 is not None and result_2 is not None
    xvfb_1, display_1 = result_1
    xvfb_2, display_2 = result_2

    assert display_1 != display_2

    # Clean up
    xvfb_1.terminate()
    await xvfb_1.wait()
    xvfb_2.terminate()
    await xvfb_2.wait()
