# Copyright 2026 The MathWorks, Inc.

import asyncio
from pathlib import Path

import pytest

from matlab_proxy import app, settings
from matlab_proxy.app_state import AppState
from matlab_proxy.constants import ExitReason
from tests.unit.fixtures.fixture_auth import (
    patch_authenticate_access_decorator,  # noqa: F401
)
from tests.unit.test_constants import FIVE_MAX_TRIES


@pytest.fixture
def sample_settings(tmp_path):
    tmp_file = tmp_path / "parent_1" / "parent_2" / "tmp_file.json"
    return {
        "error": None,
        "warnings": [],
        "matlab_config_file": tmp_file,
        "mwi_server_url": "dummy",
        "mwi_logs_root_dir": Path(settings.get_mwi_config_folder(dev=True)),
        "app_port": 12345,
        "mwapikey": "asdf",
        "has_custom_code_to_execute": False,
        "mwi_idle_timeout": None,
        "mwi_is_token_auth_enabled": False,
        "integration_name": "MATLAB Desktop",
    }


class TestAppStateExitReason:
    async def test_default_exit_reason_is_normal_shutdown(self, sample_settings):
        app_state = AppState(settings=sample_settings)
        assert app_state.exit_reason == ExitReason.NORMAL_SHUTDOWN
        await app_state.stop_server_tasks()

    async def test_exit_reason_can_be_set_to_idle_timeout(self, sample_settings):
        app_state = AppState(settings=sample_settings)
        app_state.exit_reason = ExitReason.IDLE_TIMEOUT
        assert app_state.exit_reason == ExitReason.IDLE_TIMEOUT
        assert int(app_state.exit_reason) == 100
        await app_state.stop_server_tasks()

    async def test_idle_timer_sets_exit_reason_on_expiry(self, sample_settings, mocker):
        idle_timeout = 1
        sample_settings["mwi_idle_timeout"] = idle_timeout
        app_state = AppState(settings=sample_settings)
        app_state.licensing = {"type": "existing_license"}

        mock_loop = asyncio.new_event_loop()
        mocker.patch(
            "matlab_proxy.app_state.util.get_event_loop", return_value=mock_loop
        )
        mocker.patch(
            "matlab_proxy.util.xvfb.start", return_value=(mocker.MagicMock(), ":12345")
        )
        mocker.patch.object(
            AppState, "_AppState__start_matlab_process", return_value=mocker.MagicMock()
        )

        await asyncio.sleep(idle_timeout * FIVE_MAX_TRIES)

        assert app_state.exit_reason == ExitReason.IDLE_TIMEOUT


@pytest.mark.usefixtures("patch_authenticate_access_decorator")
class TestShutdownEndpointExitReason:
    async def test_shutdown_without_reason_keeps_normal(self, aiohttp_client):
        test_app = app.create_app()
        client = await aiohttp_client(test_app)

        await client.delete("/shutdown_integration")
        state = test_app["state"]
        assert state.exit_reason == ExitReason.NORMAL_SHUTDOWN
        await state.stop_server_tasks()

    async def test_shutdown_with_idle_timeout_reason(self, aiohttp_client):
        test_app = app.create_app()
        client = await aiohttp_client(test_app)

        await client.delete("/shutdown_integration?reason=IDLE_TIMEOUT")
        state = test_app["state"]
        assert state.exit_reason == ExitReason.IDLE_TIMEOUT
        await state.stop_server_tasks()

    async def test_shutdown_with_invalid_reason_keeps_normal(self, aiohttp_client):
        test_app = app.create_app()
        client = await aiohttp_client(test_app)

        await client.delete("/shutdown_integration?reason=BOGUS")
        state = test_app["state"]
        assert state.exit_reason == ExitReason.NORMAL_SHUTDOWN
        await state.stop_server_tasks()

    async def test_shutdown_reason_case_insensitive(self, aiohttp_client):
        test_app = app.create_app()
        client = await aiohttp_client(test_app)

        await client.delete("/shutdown_integration?reason=idle_timeout")
        state = test_app["state"]
        assert state.exit_reason == ExitReason.IDLE_TIMEOUT
        await state.stop_server_tasks()


class TestExitCodeTopLevelGuard:
    """Tests that create_and_start_app guards against unexpected exits.

    Only the controlled shutdown path should produce application-defined exit codes
    (e.g., 100 for IDLE_TIMEOUT). Any unexpected exception or SystemExit from a
    library must result in UNEXPECTED_ERROR (1).
    """

    def test_library_system_exit_produces_unexpected_error(self, mocker):
        mocker.patch(
            "matlab_proxy.app.util.system.configure_no_proxy_in_env",
            side_effect=SystemExit(100),
        )

        with pytest.raises(SystemExit) as exc_info:
            app.create_and_start_app(config_name="default_configuration_name")

        assert exc_info.value.code == int(ExitReason.UNEXPECTED_ERROR)

    def test_library_runtime_error_produces_unexpected_error(self, mocker):
        mocker.patch(
            "matlab_proxy.app.util.system.configure_no_proxy_in_env",
            side_effect=RuntimeError("simulated library crash"),
        )

        with pytest.raises(SystemExit) as exc_info:
            app.create_and_start_app(config_name="default_configuration_name")

        assert exc_info.value.code == int(ExitReason.UNEXPECTED_ERROR)

    def test_library_system_exit_with_zero_still_produces_unexpected_error(
        self, mocker
    ):
        mocker.patch(
            "matlab_proxy.app.util.system.configure_no_proxy_in_env",
            side_effect=SystemExit(0),
        )

        with pytest.raises(SystemExit) as exc_info:
            app.create_and_start_app(config_name="default_configuration_name")

        assert exc_info.value.code == int(ExitReason.UNEXPECTED_ERROR)
