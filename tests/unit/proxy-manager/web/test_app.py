# Copyright 2024-2025 The MathWorks, Inc.
import asyncio
import os
from collections import namedtuple

import pytest
from aiohttp import client_exceptions, web

import matlab_proxy_manager.utils.environment_variables as mpm_env
from matlab_proxy_manager.web import app


@pytest.fixture
def mock_app(mocker):
    """Create and return a mock web application."""
    # Create a mock app
    mock = mocker.AsyncMock(spec=web.Application)
    mock.get.return_value = mocker.AsyncMock()
    return mock


class TestStartApp:
    """TestStartApp class contains unit tests for the start_app function in the web application."""

    @pytest.fixture
    def mock_env_vars(self):
        """Fixture that creates and returns a mock environment variables object."""
        return namedtuple(
            "EnvVars",
            ["mpm_port", "mpm_auth_token", "mpm_parent_pid", "base_url_prefix"],
        )(8888, "test_token", 12345, "/matlab/test")

    @pytest.fixture
    def mock_runner(self, mocker):
        """Fixture that creates and returns a mock AppRunner."""
        return mocker.Mock(spec=web.AppRunner)

    @pytest.fixture
    def mock_site(self, mocker):
        """Fixture that creates and returns a mock TCPSite."""
        return mocker.Mock(spec=web.TCPSite)

    async def test_start_app_initializes_correctly(
        self, mocker, mock_env_vars, mock_app, mock_runner, mock_site
    ):
        """Test that start_app initializes correctly."""
        mocker.patch("matlab_proxy_manager.web.app.init_app", return_value=mock_app)
        mocker.patch("matlab_proxy_manager.web.app._start_default_proxy")
        mocker.patch("aiohttp.web.AppRunner", return_value=mock_runner)
        mocker.patch("aiohttp.web.TCPSite", return_value=mock_site)
        mocker.patch("asyncio.get_event_loop")
        mocker.patch("matlab_proxy_manager.web.app.watcher.start_watcher")
        mocker.patch("matlab_proxy_manager.web.app._register_signal_handler")

        await app.start_app(mock_env_vars)

        mock_app.get.assert_called_once_with("shutdown_event")
        mock_runner.setup.assert_called_once()
        mock_site.start.assert_called_once()

    async def test_start_app_handles_shutdown_event(
        self, mocker, mock_env_vars, mock_app, mock_runner, mock_site
    ):
        """
        Test that start_app handles the shutdown event correctly.

        This test ensures that when a shutdown event is triggered, the app runner's
        cleanup method is called, indicating proper shutdown handling.
        """
        mocker.patch("matlab_proxy_manager.web.app.init_app", return_value=mock_app)
        mocker.patch("matlab_proxy_manager.web.app._start_default_proxy")
        mocker.patch("aiohttp.web.AppRunner", return_value=mock_runner)
        mocker.patch("aiohttp.web.TCPSite", return_value=mock_site)
        mocker.patch("asyncio.get_event_loop")
        mocker.patch("matlab_proxy_manager.web.app.watcher.start_watcher")
        mocker.patch("matlab_proxy_manager.web.app._register_signal_handler")

        shutdown_event = asyncio.Event()
        mock_app["shutdown_event"] = shutdown_event

        async def trigger_shutdown():
            await asyncio.sleep(0.1)
            shutdown_event.set()

        shutdown_task = asyncio.create_task(trigger_shutdown())

        await app.start_app(mock_env_vars)

        mock_runner.cleanup.assert_called_once()
        shutdown_task.cancel()

    @pytest.mark.parametrize("is_web_logging_enabled", [True, False])
    async def test_start_app_configures_logging_correctly(
        self, mocker, mock_env_vars, mock_app, is_web_logging_enabled, mock_site
    ):
        """
        Test that start_app configures logging correctly.

        This test verifies that the web application's logging is configured
        correctly based on the is_web_logging_enabled flag. It checks whether
        the AppRunner is initialized with the appropriate logger settings.
        """
        mocker.patch("matlab_proxy_manager.web.app.init_app", return_value=mock_app)
        mocker.patch("matlab_proxy_manager.web.app._start_default_proxy")
        mock_runner = mocker.Mock(spec=web.AppRunner)
        mocker.patch("aiohttp.web.AppRunner", return_value=mock_runner)
        mocker.patch("aiohttp.web.TCPSite", return_value=mock_site)
        mocker.patch("asyncio.get_event_loop")
        mocker.patch("matlab_proxy_manager.web.app.watcher.start_watcher")
        mocker.patch("matlab_proxy_manager.web.app._register_signal_handler")
        mocker.patch(
            "matlab_proxy_manager.web.app.mwi_env.is_web_logging_enabled",
            return_value=is_web_logging_enabled,
        )

        await app.start_app(mock_env_vars)

        expected_logger = app.log if is_web_logging_enabled else None
        web.AppRunner.assert_called_once_with(
            mock_app, logger=expected_logger, access_log=expected_logger
        )

    async def test_start_app_runs_watcher_in_separate_thread(
        self, mocker, mock_env_vars, mock_app, mock_site, mock_runner
    ):
        """
        Test that start_app runs the watcher in a separate thread.

        This test verifies that the watcher is started in a separate thread
        using the event loop's run_in_executor method when start_app is called.
        It mocks the necessary dependencies and checks if the watcher is
        executed correctly.
        """
        mocker.patch("matlab_proxy_manager.web.app.init_app", return_value=mock_app)
        mocker.patch("matlab_proxy_manager.web.app._start_default_proxy")
        mocker.patch("aiohttp.web.AppRunner", return_value=mock_runner)
        mocker.patch("aiohttp.web.TCPSite", return_value=mock_site)
        mock_loop = mocker.Mock()
        mocker.patch("asyncio.get_running_loop", return_value=mock_loop)
        mock_watcher = mocker.patch(
            "matlab_proxy_manager.web.app.watcher.start_watcher"
        )
        mocker.patch("matlab_proxy_manager.web.app._register_signal_handler")

        await app.start_app(mock_env_vars)

        mock_loop.run_in_executor.assert_called_once_with(None, mock_watcher, mock_app)

    async def test_start_app_registers_signal_handler(
        self, mocker, mock_env_vars, mock_app, mock_site, mock_runner
    ):
        """Test that start_app registers the signal handler."""
        mocker.patch("matlab_proxy_manager.web.app.init_app", return_value=mock_app)
        mocker.patch("matlab_proxy_manager.web.app._start_default_proxy")
        mocker.patch("aiohttp.web.AppRunner", return_value=mock_runner)
        mocker.patch("aiohttp.web.TCPSite", return_value=mock_site)
        mock_loop = mocker.Mock()
        mocker.patch("asyncio.get_running_loop", return_value=mock_loop)
        mocker.patch("matlab_proxy_manager.web.app.watcher.start_watcher")
        mock_register_signal_handler = mocker.patch(
            "matlab_proxy_manager.web.app._register_signal_handler"
        )

        await app.start_app(mock_env_vars)

        mock_register_signal_handler.assert_called_once_with(mock_loop, mock_app)


@pytest.fixture
def patch_authenticate_access_decorator(mocker):
    """
    Fixture to patch the authenticate_access decorator for testing purposes.

    This fixture mocks the 'authenticate_request' function from the
    'matlab_proxy_manager.utils.auth' module to always return True,
    effectively bypassing authentication for tests.
    """
    return mocker.patch(
        "matlab_proxy_manager.utils.auth.authenticate_request",
        return_value=True,
    )


@pytest.mark.usefixtures("patch_authenticate_access_decorator")
class TestProxy:
    """TestProxy class contains unit tests for the proxy functionality in the web application."""

    async def test_proxy_redirect_to_default(self, mocker):
        """
        Test proxy redirection to default path.

        This test ensures that the proxy function correctly redirects
        requests to the default path when the URL ends with the base
        URL prefix. It verifies that a web.HTTPFound exception is raised
        for such requests.
        """
        mock_req = mocker.Mock()
        mock_req.headers = mocker.MagicMock()
        mock_req.headers.copy.return_value = {}
        mock_req.read = mocker.AsyncMock(return_value=b"request_body")
        mock_req.rel_url = "/matlab/"

        with pytest.raises(web.HTTPFound):
            await app.proxy(mock_req)

    async def test_proxy_invalid_path(self, mocker):
        """
        Test proxy behavior when an invalid path is provided.

        This test ensures that the proxy function returns a 503 response
        with an appropriate error message when the request URL contains
        an invalid path.
        """
        mock_req = mocker.AsyncMock()
        mock_req.rel_url = "/invalid/path"
        mock_req.headers = {}

        response = await app.proxy(mock_req)

        assert isinstance(response, web.Response)
        assert response.status == 503
        assert "Incorrect request path in the URL" in response.text

    async def test_proxy_missing_context_header(self, mocker):
        """
        Test proxy behavior when the required context header is missing.

        This test ensures that the proxy function returns a 503 response
        with an appropriate error message when the 'MWI-MPM-CONTEXT' header
        is not present in the request.
        """
        mock_req = mocker.AsyncMock()
        mock_req.rel_url = "/matlab/default/some/path"
        mock_req.headers = {}

        response = await app.proxy(mock_req)

        assert isinstance(response, web.Response)
        assert response.status == 503
        assert "Required header" in response.text

    async def test_proxy_websocket_request(self, mocker):
        """
        Test proxy behavior for WebSocket requests.

        This test ensures that the proxy function correctly handles
        WebSocket upgrade requests by calling the appropriate handler
        and returning a WebSocketResponse.
        """
        mock_req = mocker.AsyncMock()
        mock_req.rel_url = "/matlab/default/some/path"
        mock_req.headers = {
            "connection": "upgrade",
            "upgrade": "websocket",
            "MWI-MPM-CONTEXT": "test_context",
        }
        mock_req.method = "GET"

        mocker.patch(
            "matlab_proxy_manager.web.app._get_backend_server",
            return_value={"absolute_url": "http://server1"},
        )
        mock_forward_websocket = mocker.patch(
            "matlab_proxy_manager.web.app._forward_websocket_request",
            return_value=web.WebSocketResponse(),
        )

        await app.proxy(mock_req)

        mock_forward_websocket.assert_called_once()

    async def test_proxy_http_request(self, mocker):
        """
        Test proxy behavior for HTTP requests.

        This test ensures that the proxy function correctly handles
        HTTP requests by calling the appropriate handler and returning
        a Response object.
        """
        mock_req = mocker.MagicMock()
        mock_req.rel_url = "/matlab/default/some/path"
        mock_req.headers = {"MWI-MPM-CONTEXT": "test_context"}
        mock_req.method = "POST"
        mock_req.read = mocker.AsyncMock(return_value=b"request_body")

        mocker.patch(
            "matlab_proxy_manager.web.app._get_backend_server",
            return_value={"absolute_url": "http://server", "headers": {}},
        )
        mock_forward_http = mocker.patch(
            "matlab_proxy_manager.web.app._forward_http_request",
            return_value=web.Response(),
        )

        await app.proxy(mock_req)

        mock_forward_http.assert_called_once()

    async def test_proxy_server_disconnected(self, mocker):
        """
        Test proxy behavior when the backend server disconnects.

        This test ensures that the proxy function raises an HTTPServiceUnavailable
        exception when the backend server disconnects during an HTTP request.
        """
        mock_req = mocker.MagicMock()
        mock_req.rel_url = "/matlab/default/some/path"
        mock_req.headers = {"MWI-MPM-CONTEXT": "test_context"}
        mock_req.method = "GET"
        mock_req.read = mocker.AsyncMock(return_value=b"")

        mocker.patch(
            "matlab_proxy_manager.web.app._get_backend_server",
            return_value={"absolute_url": "http://backend", "headers": {}},
        )
        mocker.patch(
            "matlab_proxy_manager.web.app._forward_http_request",
            side_effect=client_exceptions.ServerDisconnectedError,
        )

        with pytest.raises(web.HTTPServiceUnavailable):
            await app.proxy(mock_req)

    async def test_proxy_unexpected_exception(self, mocker):
        """
        Test proxy behavior when an unexpected exception occurs.

        This test ensures that the proxy function raises an HTTPNotFound
        exception when an unexpected error occurs during the HTTP request
        handling process.
        """
        mock_req = mocker.MagicMock()
        mock_req.rel_url = "/matlab/default/some/path"
        mock_req.headers = {"MWI-MPM-CONTEXT": "test_context"}
        mock_req.method = "GET"
        mock_req.read = mocker.AsyncMock(return_value=b"")

        mocker.patch(
            "matlab_proxy_manager.web.app._get_backend_server",
            return_value={"absolute_url": "http://backend"},
        )
        mocker.patch(
            "matlab_proxy_manager.web.app._forward_http_request",
            side_effect=Exception("Unexpected error"),
        )

        with pytest.raises(web.HTTPNotFound):
            await app.proxy(mock_req)

    async def test_proxy_correct_req_headers_are_forwarded(self, mocker):
        """
        Test that the correct request headers are forwarded to the backend server.

        This test ensures that the proxy function correctly forwards the necessary
        headers to the backend server, including the MWI-MPM-CONTEXT header.
        """
        mock_req = mocker.AsyncMock()
        mock_req.read = mocker.AsyncMock(return_value=b"request_body")
        mock_req.rel_url = "/matlab/default/some/path"
        mock_req.headers = {
            "JSESSION-ID": "123456789",
            "MWI-MPM-CONTEXT": "test_context",
        }
        mock_req.method = "GET"

        mocker.patch(
            "matlab_proxy_manager.web.app._get_backend_server",
            return_value={
                "absolute_url": "http://server1",
                "headers": {"MWI-AUTH-TOKEN": "token"},
            },
        )
        mock_forward_http = mocker.patch(
            "matlab_proxy_manager.web.app._forward_http_request",
            return_value=web.Response(),
        )
        await app.proxy(mock_req)
        mock_forward_http.assert_called_once_with(
            mock_req,
            b"request_body",
            "http://server1/some/path",
            {
                **mock_req.headers,
                **{
                    "MWI-AUTH-TOKEN": "token",
                    "Content-Length": "12",
                    "X-Forwarded-Proto": "http",
                },
            },
        )

    async def test_proxy_start_default_proxy_is_called_if_default_proxy_not_already_started(
        self, mocker
    ):
        # Setup
        mock_req = mocker.MagicMock()
        mock_req.rel_url = "/matlab/default/some/path"
        mock_req.headers = {"MWI-MPM-CONTEXT": "test_context"}
        mock_req.method = "POST"
        mock_req.read = mocker.AsyncMock(return_value=b"request_body")
        mock_req.app = {"has_default_matlab_proxy_started": False, "servers": {}}
        mock_start_default_proxy = mocker.patch(
            "matlab_proxy_manager.web.app._start_default_proxy",
        )
        mocker.patch(
            "matlab_proxy_manager.web.app._get_backend_server",
            return_value={"absolute_url": "http://server", "headers": {}},
        )
        mock_forward_http = mocker.patch(
            "matlab_proxy_manager.web.app._forward_http_request",
            return_value=web.Response(),
        )

        # Execute
        await app.proxy(mock_req)

        # Assertions
        mock_start_default_proxy.assert_called_once()
        mock_forward_http.assert_called_once()

    async def test_proxy_start_default_proxy_is_not_called_if_proxying_non_default_matlab_request(
        self, mocker
    ):
        # Setup
        mock_req = mocker.MagicMock()
        mock_req.rel_url = "/matlab/12345/some/path"
        mock_req.headers = {"MWI-MPM-CONTEXT": "test_context"}
        mock_req.method = "POST"
        mock_req.read = mocker.AsyncMock(return_value=b"request_body")
        mock_req.app = {"has_default_matlab_proxy_started": False, "servers": {}}
        mock_start_default_proxy = mocker.patch(
            "matlab_proxy_manager.web.app._start_default_proxy",
        )
        mocker.patch(
            "matlab_proxy_manager.web.app._get_backend_server",
            return_value={"absolute_url": "http://server", "headers": {}},
        )
        mock_forward_http = mocker.patch(
            "matlab_proxy_manager.web.app._forward_http_request",
            return_value=web.Response(),
        )

        # Execute
        await app.proxy(mock_req)

        # Assertions
        mock_start_default_proxy.assert_not_called()
        mock_forward_http.assert_called_once()

    async def test_proxy_start_default_proxy_is_not_called_if_default_proxy_already_started(
        self, mocker
    ):
        # Setup
        mock_req = mocker.MagicMock()
        mock_req.rel_url = "/matlab/default/some/path"
        mock_req.headers = {"MWI-MPM-CONTEXT": "test_context"}
        mock_req.method = "POST"
        mock_req.read = mocker.AsyncMock(return_value=b"request_body")
        mock_req.app = {"has_default_matlab_proxy_started": True, "servers": {}}
        mock_start_default_proxy = mocker.patch(
            "matlab_proxy_manager.web.app._start_default_proxy",
        )
        mocker.patch(
            "matlab_proxy_manager.web.app._get_backend_server",
            return_value={"absolute_url": "http://server", "headers": {}},
        )
        mock_forward_http = mocker.patch(
            "matlab_proxy_manager.web.app._forward_http_request",
            return_value=web.Response(),
        )

        # Execute
        await app.proxy(mock_req)

        # Assertions
        mock_start_default_proxy.assert_not_called()
        mock_forward_http.assert_called_once()


@pytest.fixture
def patch_env_vars(monkeypatch):
    """
    Fixture to patch environment variables for testing.

    These environment variables are used to simulate the MATLAB Proxy Manager's
    runtime environment during testing.
    """
    monkeypatch.setitem(os.environ, mpm_env.get_env_name_mwi_mpm_port(), "8888")
    monkeypatch.setitem(
        os.environ, mpm_env.get_env_name_mwi_mpm_auth_token(), "test_token"
    )
    monkeypatch.setitem(os.environ, mpm_env.get_env_name_mwi_mpm_parent_pid(), "12345")


class TestHelpers:
    """Test the helper functions used in the web application."""

    async def test_init_app(self, mocker):
        """
        Test the initialization of the application.

        This test function verifies that the `init_app` function correctly initializes
        the web application with the expected attributes and event handlers.

        It checks:
        1. The returned object is an instance of web.Application
        2. A shutdown event is set
        3. The data directory is correctly set
        4. The appropriate number of startup and cleanup events are added
        """
        mocker.patch(
            "matlab_proxy_manager.web.app.helpers.create_and_get_proxy_manager_data_dir",
            return_value="/tmp/test_dir",
        )
        test_app = app.init_app()

        assert isinstance(test_app, web.Application)
        assert test_app.get("shutdown_event") is not None
        assert test_app["data_dir"] == "/tmp/test_dir"

        # init_app adds two events to on_startup and on_cleanup,
        # while web.Application() adds another
        assert len(test_app.on_startup) >= 2
        assert len(test_app.on_cleanup) >= 2

    def test_catch_signals(self, mocker, mock_app):
        """Test the signal handling in the application."""
        mock_poller = mocker.patch(
            "matlab_proxy_manager.web.app.helpers.poll_for_server_deletion",
            return_value=None,
        )

        # Exercise the system under test
        app._catch_signals(mock_app)

        # Assertions
        mock_poller.assert_called_once()
        mock_app.get.assert_called_once_with("shutdown_event")
        mock_app.get.return_value.set.assert_called_once()

    def test_register_signal_handlers_non_posix(self, mocker):
        """Test the registration of signal handlers in Windows."""
        # mock the signals
        mocker.patch(
            "matlab_proxy.util.system.get_supported_termination_signals",
            return_value=["dummy_signal"],
        )
        mocker.patch(
            "matlab_proxy.util.system.is_posix",
            return_value=False,
        )
        mock_signal = mocker.patch("signal.signal")
        app._register_signal_handler(mocker.MagicMock(), mock_app)

        # Assertions
        mock_signal.assert_called_once()
        args, _ = mock_signal.call_args
        assert args[0] == "dummy_signal"
        assert callable(args[1])

    def test_register_signal_handlers_posix(self, mocker):
        """Test the registration of signal handlers in posix systems."""
        # mock the signals
        mocker.patch(
            "matlab_proxy.util.system.get_supported_termination_signals",
            return_value=["dummy_signal"],
        )
        mocker.patch(
            "matlab_proxy.util.system.is_posix",
            return_value=True,
        )
        mock_loop = mocker.MagicMock()
        mock_loop.add_signal_handler = mocker.MagicMock()
        app._register_signal_handler(mock_loop, mock_app)

        # Assertions
        mock_loop.add_signal_handler.assert_called_once()
        args, _ = mock_loop.add_signal_handler.call_args
        assert args[0] == "dummy_signal"
        assert callable(args[1])

    async def test_start_default_proxy_happy_path(self, mocker):
        """Test the startup of the default proxy."""
        # Mock the necessary components
        app_state = {
            "parent_pid": "123",
            "auth_token": "token",
            "data_dir": "/path/to/data",
            "base_url_prefix": "/matlab/test",
            "servers": {},
        }
        mock_server_process = {"id": "server1", "details": "other details"}
        mock_start_proxy = mocker.patch(
            "matlab_proxy_manager.lib.api.start_matlab_proxy_for_jsp",
            return_value=mock_server_process,
        )

        # Exercise the system under test
        await app._start_default_proxy(app_state)

        # Assertions
        mock_start_proxy.assert_called_once_with(
            parent_id="123",
            is_shared_matlab=True,
            mpm_auth_token="token",
            base_url_prefix="/matlab/test",
        )
        assert app_state["servers"] == {
            "server1": mock_server_process,
        }

    async def test_start_default_proxy_throws_Exception(self, mocker):
        """Test the startup of the default proxy."""
        # Mock the necessary components
        app_state = {
            "parent_pid": "123",
            "auth_token": "token",
            "data_dir": "/path/to/data",
            "servers": {},
        }
        mocker.patch(
            "matlab_proxy_manager.lib.api.start_matlab_proxy_for_jsp",
            return_value={"errors": ["Failed to start matlab-proxy server"]},
        )

        with pytest.raises(Exception):
            # Exercise the system under test
            await app._start_default_proxy(app_state)

        # Assertions
        assert app_state.get("servers") == {}

    def test_fetch_and_validate_required_env_vars(self, patch_env_vars):
        """Test to verify that the function correctly fetches and validates required environment variables."""
        env_vars = app._fetch_and_validate_required_env_vars()
        assert env_vars.mpm_port == 8888
        assert env_vars.mpm_auth_token == "test_token"
        assert env_vars.mpm_parent_pid == "12345"

    def test_fetch_and_validate_required_env_vars_missing_vars(
        self, monkeypatch, patch_env_vars
    ):
        """Test to verify that SystemExit exception is raised when required variables are missing."""
        monkeypatch.delenv(mpm_env.get_env_name_mwi_mpm_port(), raising=False)
        monkeypatch.delenv(mpm_env.get_env_name_mwi_mpm_auth_token(), raising=False)
        monkeypatch.delenv(mpm_env.get_env_name_mwi_mpm_parent_pid(), raising=False)

        with pytest.raises(SystemExit) as excinfo:
            app._fetch_and_validate_required_env_vars()
        assert excinfo.value.code == 1

    def test_fetch_and_validate_required_env_vars_invalid_port(self, monkeypatch):
        """Test to verify that SystemExit exception is raised when the port is invalid."""
        monkeypatch.setenv(mpm_env.get_env_name_mwi_mpm_port(), "not_a_number")
        monkeypatch.setenv(mpm_env.get_env_name_mwi_mpm_auth_token(), "token")
        monkeypatch.setenv(mpm_env.get_env_name_mwi_mpm_parent_pid(), "pid")

        with pytest.raises(SystemExit) as excinfo:
            app._fetch_and_validate_required_env_vars()
        assert excinfo.value.code == 1

    @pytest.mark.parametrize(
        "client_key, default_key, expected_server",
        [
            ("server1", "default", {"id": "server1", "details": "details1"}),
            ("not-existing", "default", {"id": "default", "details": "details3"}),
        ],
    )
    def test_get_backend_server(self, mocker, client_key, default_key, expected_server):
        """
        Test the _get_backend_server function.
        This test verifies that the _get_backend_server function correctly retrieves
        the server information based on the provided client key and default key.
        """
        mock_req = mocker.MagicMock(spec=web.Request)
        mock_req.app = {
            "servers": {
                "server1": {"id": "server1", "details": "details1"},
                "server2": {"id": "server2", "details": "details2"},
                "default": {"id": "default", "details": "details3"},
            }
        }

        backend_server: dict = app._get_backend_server(
            mock_req, client_key, default_key
        )
        assert backend_server == expected_server
