# Copyright 2026 The MathWorks, Inc.

import pytest

from matlab_proxy.util import window_manager
from matlab_proxy.util.mwi.exceptions import WindowManagerError

"""This file tests methods defined in window_manager.py file
"""


@pytest.fixture(autouse=True)
def mock_is_linux(mocker):
    """window_manager.start() asserts it is only invoked on Linux; force that here so
    the launch logic can be exercised regardless of the host OS."""
    mocker.patch("matlab_proxy.util.window_manager.system.is_linux", return_value=True)


@pytest.fixture(name="mock_create_subprocess")
def mock_create_subprocess_fixture(mocker):
    """Patches asyncio.create_subprocess_exec to return a sentinel process."""
    fake_process = object()
    mock = mocker.patch("asyncio.create_subprocess_exec", return_value=fake_process)
    mock.fake_process = fake_process
    return mock


async def test_asserts_on_non_linux(mocker):
    """window_manager.start() must refuse to run on non-Linux systems."""
    mocker.patch("matlab_proxy.util.window_manager.system.is_linux", return_value=False)
    with pytest.raises(AssertionError):
        await window_manager.start(":0")


async def test_no_display():
    """With no display, no window manager is started."""
    assert await window_manager.start(None) is None


async def test_none_available(mocker):
    """With a display but no supported window manager on PATH, returns None."""
    mocker.patch("shutil.which", return_value=None)
    assert await window_manager.start(":0") is None


async def test_prefers_openbox(mocker, mock_create_subprocess):
    """When both openbox and fluxbox are available, openbox is launched."""
    mocker.patch("shutil.which", side_effect=lambda binary: f"/usr/bin/{binary}")

    result = await window_manager.start(":0")

    assert result is mock_create_subprocess.fake_process
    args, kwargs = mock_create_subprocess.call_args
    assert list(args) == ["openbox", "--sm-disable"]
    assert kwargs["env"]["DISPLAY"] == ":0"


async def test_falls_back_to_fluxbox(mocker, mock_create_subprocess):
    """When only fluxbox is available, it is launched."""
    mocker.patch(
        "shutil.which",
        side_effect=lambda binary: "/usr/bin/fluxbox" if binary == "fluxbox" else None,
    )

    await window_manager.start(":0")

    args, _ = mock_create_subprocess.call_args
    assert list(args) == ["fluxbox", "-screen", "0", "-log", "/dev/null"]


async def test_raises_on_spawn_failure(mocker):
    """A failure to spawn the window manager surfaces as WindowManagerError."""
    mocker.patch("shutil.which", side_effect=lambda binary: f"/usr/bin/{binary}")
    mocker.patch("asyncio.create_subprocess_exec", side_effect=OSError("boom"))
    with pytest.raises(WindowManagerError):
        await window_manager.start(":0")
