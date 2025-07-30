# Copyright 2024-2025 The MathWorks, Inc.

import asyncio
import os
import re
import signal
import sys
from collections import namedtuple
from typing import Optional

import aiohttp
from aiohttp import ClientSession, client_exceptions, web

import matlab_proxy.util.mwi.environment_variables as mwi_env
import matlab_proxy.util.system as mwi_sys
import matlab_proxy_manager.lib.api as mpm_lib
import matlab_proxy.constants as mp_constants
from matlab_proxy_manager.utils import constants, helpers, logger
from matlab_proxy_manager.utils import environment_variables as mpm_env
from matlab_proxy_manager.utils.auth import authenticate_access_decorator
from matlab_proxy_manager.web import watcher
from matlab_proxy_manager.web.monitor import OrphanedProcessMonitor

# List of public-facing APIs exported by this module.
# This list contains the names of functions or classes that are intended to be
# used by external code importing this module. Only items listed here will be
# directly accessible when using "from module import *".
__all__ = ["proxy"]

log = logger.get(init=True)


def init_app() -> web.Application:
    """
    Initialize and configure the aiohttp web application.

    This function sets up the web application with necessary configurations,
    including creating the proxy manager data directory, setting up an idle
    timeout monitor, and configuring client sessions.

    Returns:
        web.Application: The configured aiohttp web application.
    """
    app = web.Application()
    # Async event is utilized to signal app termination from this and other modules
    app["shutdown_event"] = asyncio.Event()

    # Tracks whether default matlab proxy is started or not
    app["has_default_matlab_proxy_started"] = False

    # Create and get the proxy manager data directory
    try:
        data_dir = helpers.create_and_get_proxy_manager_data_dir()
        app["data_dir"] = data_dir
    except Exception as ex:
        raise RuntimeError(f"Failed to create or get data directory: {ex}") from ex

    # Setup idle timeout monitor for the app
    monitor = OrphanedProcessMonitor(app)

    # Load existing matlab proxy servers into app state for consistency
    app["servers"] = helpers.pre_load_from_state_file(app.get("data_dir"))
    log.debug("Loaded existing matlab proxy servers into app state: %s", app["servers"])

    async def start_idle_monitor(app):
        """Start the idle timeout monitor."""
        app["monitor_task"] = asyncio.create_task(monitor.start())

    async def create_client_session(app):
        """Create an aiohttp client session."""
        app["session"] = ClientSession(
            trust_env=True, connector=aiohttp.TCPConnector(ssl=False, ttl_dns_cache=600)
        )

    async def cleanup_client_session(app):
        """Cleanup the aiohttp client session."""
        await app["session"].close()

    async def cleanup_monitor(app):
        """Cancel the idle timeout monitor task."""
        if "monitor_task" in app:
            app["monitor_task"].cancel()
            try:
                await app["monitor_task"]
            except asyncio.CancelledError:
                pass

    async def cleanup_watcher(app):
        """Cleanup the filesystem watcher."""
        if "observer" in app:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, watcher.stop_watcher, app)

        if "watcher_future" in app:
            app["watcher_future"].cancel()
            try:
                await app["watcher_future"]
            except asyncio.CancelledError:
                pass

    app.on_startup.append(start_idle_monitor)
    app.on_startup.append(create_client_session)
    app.on_cleanup.append(helpers.delete_dangling_servers)
    app.on_cleanup.append(cleanup_client_session)
    app.on_cleanup.append(cleanup_monitor)
    app.on_cleanup.append(cleanup_watcher)

    app.router.add_route("*", "/{tail:.*}", proxy)

    return app


async def start_app(env_vars):
    """
    Initialize and start the web application.

    This function sets up logging, initializes the web application, and starts
    the default matlab proxy. It also sets up signal handlers for graceful shutdown
    and starts a file watcher in a separate thread.

    Raises:
        Exception: If any error occurs during the application startup or runtime.
    """
    app = init_app()

    app["port"] = env_vars.mpm_port
    app["auth_token"] = env_vars.mpm_auth_token
    app["parent_pid"] = env_vars.mpm_parent_pid
    app["base_url_prefix"] = env_vars.base_url_prefix

    web_logger = None if not mwi_env.is_web_logging_enabled() else log

    # Run the app
    runner = web.AppRunner(app, logger=web_logger, access_log=web_logger)
    await runner.setup()
    site = web.TCPSite(runner, port=env_vars.mpm_port)
    await site.start()
    log.debug("Proxy manager started at http://127.0.0.1:%d", site._port)

    # Get the default event loop
    loop = asyncio.get_running_loop()

    # Run the observer in a separate thread and store the future
    app["watcher_future"] = loop.run_in_executor(None, watcher.start_watcher, app)

    # Register signal handler for graceful shutdown
    _register_signal_handler(loop, app)

    # Wait for receiving shutdown_event (set by interrupts or by monitoring process)
    await app.get("shutdown_event").wait()

    # After receiving the shutdown signal, perform cleanup by stopping the web server
    await runner.cleanup()


def _register_signal_handler(loop, app):
    """
    Registers signal handlers for graceful shutdown of the application.

    This function sets up handlers for supported termination signals to allow
    the application to shut down gracefully. It uses different methods for
    POSIX and non-POSIX systems to add the signal handlers.

    Args:
        loop (asyncio.AbstractEventLoop): The event loop to which the signal handlers
            should be added.
        app (aiohttp.web.Application): The web application instance.
    """
    signals = mwi_sys.get_supported_termination_signals()
    for sig_name in signals:
        if mwi_sys.is_posix():
            loop.add_signal_handler(sig_name, lambda: _catch_signals(app))
        else:
            # loop.add_signal_handler() is not yet supported in Windows.
            # Using the 'signal' package instead.
            # signal module expects a handler function that takes two arguments:
            # the signal number and the current stack frame
            signal.signal(sig_name, lambda s, f: _catch_signals(app))


def _catch_signals(app):
    """Handle termination signals for graceful shutdown."""
    # Poll for parent process to clean up to avoid race conditions in cleanup of matlab proxies
    # Ideally, we should minimize the work done when we catch exit signals, which would mean the
    # polling for parent process should happen elsewhere
    helpers.poll_for_server_deletion()
    app.get("shutdown_event").set()


async def _start_default_proxy(app):
    """
    Starts the default MATLAB proxy and updates the application state.

    Args:
        app : The aiohttp web application.
    """
    server_process = await mpm_lib.start_matlab_proxy_for_jsp(
        parent_id=app.get("parent_pid"),
        is_shared_matlab=True,
        mpm_auth_token=app.get("auth_token"),
        base_url_prefix=app.get("base_url_prefix"),
    )
    errors = server_process.get("errors")

    # Raising an exception if there was an error starting the default MATLAB proxy
    if errors:
        raise Exception(":".join(errors))

    # Add the new/existing server to the app state
    app["servers"][server_process.get("id")] = server_process


@authenticate_access_decorator
async def proxy(req):
    """
    Proxy incoming HTTP requests to the appropriate MATLAB proxy backend server.

    This function handles requests by:
    1. Redirecting paths ending with '/matlab/' to '/matlab/default/'.
    2. Extracting client identifiers from the request path.
    3. Routing the request to the appropriate MATLAB backend server based on the client identifier.
    4. Handling various exceptions and providing appropriate HTTP responses.

    Args:
        req (aiohttp.web.Request): The incoming HTTP request.

    Returns:
        aiohttp.web.Response: The HTTP response from the backend server or an error page.

    Raises:
        aiohttp.web.HTTPFound: If the request path needs to be redirected.
        aiohttp.web.HTTPServiceUnavailable: If the MATLAB proxy process is not running.
        aiohttp.web.HTTPNotFound: If the request cannot be forwarded to the MATLAB proxy.
    """
    # Special keys for web socket requests
    connection = "connection"
    upgrade = "upgrade"
    req_headers = req.headers.copy()
    req_body = await req.read()

    # Set content length in case of modification
    req_headers["Content-Length"] = str(len(req_body))
    req_headers["X-Forwarded-Proto"] = "http"
    req_path = req.rel_url

    # Redirect block to move /*/matlab to /*/matlab/default/
    if str(req_path).endswith(f"{constants.MWI_BASE_URL_PREFIX}"):
        return _redirect_to_default(req_path)

    match = re.compile(r".*?/matlab/([^/]+)/(.*)").match(str(req.rel_url))

    if not match:
        # Path doesn't contain /matlab/default|<id> in the request path
        # redirect to error page
        log.debug("Regex match not found, match: %s", match)
        return _render_error_page(
            "Incorrect request path in the URL, please try with correct URL."
        )

    ident = match.group(1).rstrip("/")
    log.debug("Client identifier for proxy: %s", ident)

    ctx = req_headers.get(constants.HEADER_MWI_MPM_CONTEXT)
    if not ctx:
        log.debug("MPM Context header not found in the request")
        return _render_error_page(
            f"Required header: ${constants.HEADER_MWI_MPM_CONTEXT} not found in the request"
        )

    # Raising exception from here is not cleanly handled by Jupyter server proxy.
    # It only shows 599 with a generic stream closed error message.
    # Hence returning 503 with custom error message as response.
    try:
        await _start_default_proxy_if_not_already_started(req)
    except Exception as e:
        log.error("Error starting default proxy: %s", e)
        return _render_error_page(f"Error during startup: {e}")

    client_key = f"{ctx}_{ident}"
    default_key = f"{ctx}_default"
    group_two_rel_url = match.group(2)

    backend_server = _get_backend_server(req, client_key, default_key)
    proxy_url = f"{backend_server.get('absolute_url')}/{group_two_rel_url}"
    log.debug("Proxy URL: %s", proxy_url)

    if (
        req_headers.get(connection, "").lower() == upgrade
        and req_headers.get(upgrade, "").lower() == "websocket"
        and req.method == "GET"
    ):
        return await _forward_websocket_request(req, proxy_url)
    try:
        return await _forward_http_request(
            req, req_body, proxy_url, _collate_headers(req_headers, backend_server)
        )
    except web.HTTPFound:
        log.debug("Redirection to path with /default")
        raise

    # Handles any pending HTTP requests from the browser when the MATLAB proxy process is
    # terminated before responding to them.
    except (
        client_exceptions.ServerDisconnectedError,
        client_exceptions.ClientConnectionError,
    ) as ex:
        log.debug("MATLAB proxy process may not be running.")
        raise web.HTTPServiceUnavailable() from ex
    except Exception as err:
        log.error("Failed to forward HTTP request to MATLAB proxy with error: %s", err)
        raise web.HTTPNotFound() from err


# Helper private functions


def _collate_headers(req_headers: dict, backend_server: dict) -> dict:
    """Combines request headers with backend server (matlab-proxy) headers.

    Args:
        req_headers (dict): The headers from the incoming request.
        backend_server (dict): The backend server configuration.

    Returns:
        dict: A new dictionary containing all headers from both sources.
    """
    return {**req_headers, **backend_server.get("headers")}


async def _forward_websocket_request(
    req: web.Request, proxy_url: str
) -> web.WebSocketResponse:
    """Handles a websocket request to the backend matlab proxy server

    Args:
        req (web.Request): websocket request from the client
        proxy_url (str): backend matlab proxy server URL

    Raises:
        ValueError: when an unexpected websocket message type is received
        aiohttp.WebSocketError: For any exception raised while forwarding request from src to dest

    Returns:
        web.WebSocketResponse: The response from the backend server
    """
    ws_server = web.WebSocketResponse(
        max_msg_size=mp_constants.MAX_WEBSOCKET_MESSAGE_SIZE_IN_MB, compress=True
    )
    await ws_server.prepare(req)

    async with aiohttp.ClientSession(
        trust_env=True,
        cookies=req.cookies,
        connector=aiohttp.TCPConnector(ssl=False),
    ) as client_session:
        try:
            async with client_session.ws_connect(
                proxy_url,
                max_msg_size=mp_constants.MAX_WEBSOCKET_MESSAGE_SIZE_IN_MB,  # max websocket message size from MATLAB to browser
                compress=12,  # enable websocket messages compression
            ) as ws_client:

                async def ws_forward(ws_src, ws_dest):
                    async for msg in ws_src:
                        msg_type = msg.type
                        msg_data = msg.data

                        # When a websocket is closed by the MATLAB JSD, it sends out a few
                        # http requests to the Embedded Connector about the events that had occurred
                        # (figureWindowClosed etc.) The Embedded Connector responds by sending a
                        # message of type 'Error' with close code as Abnormal closure. When this
                        # happens, matlab-proxy can safely exit out of the loop and close the
                        # websocket connection it has with the Embedded Connector (ws_client)
                        if (
                            msg_type == aiohttp.WSMsgType.ERROR
                            and ws_src.close_code
                            == aiohttp.WSCloseCode.ABNORMAL_CLOSURE
                        ):
                            log.debug(
                                "Src: %s, msg_type= %s, ws_src.close_code= %s",
                                ws_src,
                                msg_type,
                                ws_src.close_code,
                            )
                            break
                        if msg_type == aiohttp.WSMsgType.TEXT:
                            await ws_dest.send_str(msg_data)
                        elif msg_type == aiohttp.WSMsgType.BINARY:
                            await ws_dest.send_bytes(msg_data)
                        elif msg_type == aiohttp.WSMsgType.PING:
                            await ws_dest.ping()
                        elif msg_type == aiohttp.WSMsgType.PONG:
                            await ws_dest.pong()
                        elif ws_dest.closed:
                            log.debug("Destination: %s closed", ws_dest)
                            await ws_dest.close(
                                code=ws_dest.close_code, message=msg.extra
                            )
                        elif msg_type == aiohttp.WSMsgType.ERROR:
                            log.error(f"WebSocket error received: {msg}")
                            if "exceeds limit" in str(msg.data):
                                log.error(
                                    f"Message too large: {msg.data}. Please refresh browser tab to reconnect."
                                )
                            break
                        else:
                            raise ValueError(f"Unexpected message type: {msg}")

                await asyncio.wait(
                    [
                        asyncio.create_task(ws_forward(ws_server, ws_client)),
                        asyncio.create_task(ws_forward(ws_client, ws_server)),
                    ],
                    return_when=asyncio.FIRST_COMPLETED,
                )

                return ws_server
        except Exception as err:
            log.error("Failed to create web socket connection with error: %s", err)

            code, message = (
                aiohttp.WSCloseCode.INTERNAL_ERROR,
                "Failed to establish websocket connection with the backend server",
            )
            await ws_server.close(code=code, message=message.encode("utf-8"))
            raise aiohttp.WebSocketError(code=code, message=message)


async def _forward_http_request(
    req: web.Request,
    req_body: Optional[bytes],
    proxy_url: str,
    headers: dict,
) -> web.Response:
    """
    Forwards an incoming HTTP request to a specified backend server.

    Returns:
        web.Response: The response from the backend server, including headers, status, and body.
    """
    client_session = req.app.get("session")
    async with client_session.request(
        req.method,
        proxy_url,
        allow_redirects=True,
        data=req_body,
        headers=headers,
    ) as res:
        headers = res.headers.copy()
        body = await res.read()
        return web.Response(headers=headers, status=res.status, body=body)


async def _start_default_proxy_if_not_already_started(req):
    app = req.app
    req_path = req.rel_url

    # Start default matlab-proxy only when it is not already started and
    # if the request path contains the default MATLAB path (/matlab/default)
    if not app.get(
        "has_default_matlab_proxy_started", False
    ) and constants.MWI_DEFAULT_MATLAB_PATH in str(req_path):
        log.debug("Starting default matlab-proxy for request path: %s", str(req_path))
        await _start_default_proxy(app)
        app["has_default_matlab_proxy_started"] = True


def _get_backend_server(req: web.Request, client_key: str, default_key: str) -> dict:
    """
    Retrieves the backend server configuration for a given client key.
    """
    app = req.app
    backend_server = app["servers"].get(client_key)
    # Route to default matlab if the specified path doesn't exist
    if not backend_server:
        log.debug("Client not found in the current servers, using default matlab proxy")
        backend_server = app["servers"].get(default_key)
    return backend_server


def _redirect_to_default(req_path) -> None:
    """
    Redirects the request to the default path.

    This function constructs a new URL by appending '/default/' to the given request path
    and raises an HTTPFound exception to redirect the client.

    Raises:
        web.HTTPFound: Redirects the client to the new URL.
    """
    new_redirect_url = f"{str(req_path).rstrip('/')}/default/"
    log.info("Redirecting to %s", new_redirect_url)
    raise web.HTTPFound(new_redirect_url)


def _render_error_page(error_msg: str) -> web.Response:
    """Returns 503 with error text"""
    return web.HTTPServiceUnavailable(
        text=f'<p style="color: red;">{error_msg}</p>', content_type="text/html"
    )


def _fetch_and_validate_required_env_vars():
    EnvVars = namedtuple(
        "EnvVars", ["mpm_port", "mpm_auth_token", "mpm_parent_pid", "base_url_prefix"]
    )

    port = os.getenv(mpm_env.get_env_name_mwi_mpm_port())
    mpm_auth_token = os.getenv(mpm_env.get_env_name_mwi_mpm_auth_token())
    ctx = os.getenv(mpm_env.get_env_name_mwi_mpm_parent_pid())

    if not ctx or not port or not mpm_auth_token:
        log.error("Error: One or more required environment variables are missing.")
        sys.exit(1)

    try:
        base_url_prefix = os.getenv(mpm_env.get_env_name_base_url_prefix(), "")
        mwi_mpm_port: int = int(port)
        return EnvVars(
            mpm_port=mwi_mpm_port,
            mpm_auth_token=mpm_auth_token,
            mpm_parent_pid=ctx,
            base_url_prefix=base_url_prefix,
        )
    except ValueError as ve:
        log.error("Error: Invalid type for port: %s", ve)
        sys.exit(1)


def main() -> None:
    """
    The main entry point of the application. Starts the app and run until the shutdown
    signal to terminate the app is received.
    """
    env_vars = _fetch_and_validate_required_env_vars()
    asyncio.run(start_app(env_vars))


if __name__ == "__main__":
    # This ensures that the app is not created when the module is imported and
    # is only started when the script is run directly or via executable invocation
    main()
