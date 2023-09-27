# Copyright (c) 2020-2023 The MathWorks, Inc.

import asyncio
import json
import mimetypes
import pkgutil
import sys

import aiohttp
from aiohttp import client_exceptions, web
from aiohttp_session import setup as aiohttp_session_setup
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from cryptography import fernet

import matlab_proxy
from matlab_proxy import constants, settings, util
from matlab_proxy.app_state import AppState
from matlab_proxy.util import mwi
from matlab_proxy.util.mwi import environment_variables as mwi_env
from matlab_proxy.util.mwi import token_auth
from matlab_proxy.util.mwi.exceptions import AppError, InvalidTokenError, LicensingError


mimetypes.add_type("font/woff", ".woff")
mimetypes.add_type("font/woff2", ".woff2")
mimetypes.add_type("font/eot", ".eot")
mimetypes.add_type("font/ttf", ".ttf")
mimetypes.add_type("application/json", ".map")
mimetypes.add_type("image/png", ".ico")

# TODO It is bad practice to have global state in aiohttp applications, instead this
# mount point should be read in the application start up function, then if it is not
# an empty string, registering a subapp with the given prefix. In addition, if it is
# possible and does not mess-up the MATLAB iframe base_url detection, register a
# nested subapp (with a name unlikely to cause collisions) containing this API and the
# static serving.

# Setup logger for the integration and a web logger. Override any default loggers.
logger = mwi.logger.get(init=True)


def marshal_licensing_info(licensing_info):
    """Gather/Marshal licensing information for MHLM and NLM Licensing types.

    Args:
        licensing_info (Dict): Contains licensing information

    Returns:
        Dict: Licensing information specific to the type of Licensing.
    """
    if licensing_info is None:
        return None

    licensing_type = licensing_info.get("type")

    if licensing_type is None:
        return None

    if licensing_type == "mhlm":
        return {
            "type": "mhlm",
            "emailAddress": licensing_info["email_addr"],
            "entitlements": licensing_info.get("entitlements", []),
            "entitlementId": licensing_info.get("entitlement_id", None),
        }
    elif licensing_type == "nlm":
        return {
            "type": "nlm",
            "connectionString": licensing_info["conn_str"],
        }
    elif licensing_type == "existing_license":
        return {"type": "existing_license"}


def marshal_error(error):
    """Gather/Marshal error details.

    Args:
        error (Object): Instance of NetworkLicensingError or OnlineLicensingError or MatlabError

    Returns:
        Dict: Containing information about the error.
    """
    if error is None:
        return None
    if isinstance(error, AppError):
        return {
            "message": error.message,
            "logs": error.logs,
            "type": error.__class__.__name__,
        }
    else:
        return {"message": error.__str__, "logs": "", "type": error.__class__.__name__}


async def create_status_response(app, loadUrl=None):
    """Send a generic status response about the state of server,MATLAB and MATLAB Licensing

    Args:
        app (aiohttp.web.Application): Web Server
        loadUrl (String, optional): Represents the root URL. Defaults to None.

    Returns:
        JSONResponse: A JSONResponse object containing the generic state of the server, MATLAB and MATLAB Licensing.
    """
    state = app["state"]

    return web.json_response(
        {
            "matlab": {
                "status": await state.get_matlab_state(),
                "version": state.settings.get("matlab_version", "Unknown"),
            },
            "licensing": marshal_licensing_info(state.licensing),
            "loadUrl": loadUrl,
            "error": marshal_error(state.error),
            "wsEnv": state.settings.get("ws_env", ""),
        }
    )


@token_auth.authenticate_access_decorator
async def get_auth_token(req):
    """API endpoint to return the auth token

    Args:
        req (HTTPRequest): HTTPRequest Object

    Returns:
        Response: auth token in JSON format
    """
    auth_token = await token_auth._get_token(req)

    return web.json_response(
        {
            "authToken": auth_token,
        }
    )


# @token_auth.authenticate_access_decorator
# Explicitly disabling authentication for this end-point,
# because the front end requires this endpoint to be available at all times.
async def get_env_config(req):
    """API Endpoint to get Matlab Web Desktop environment specific configuration.

    Args:
        req (HTTPRequest): HTTPRequest Object.

    Returns:
        JSONResponse: contains a Dict representing environment specific configuration serialized to JSON
    """
    state = req.app["state"]
    config = state.settings["env_config"]
    config["authEnabled"] = state.settings["mwi_is_token_auth_enabled"]

    # In a previously authenticated session, if the url is accessed without the token(using session cookie), send the token as well.
    config["authStatus"] = True if await token_auth.authenticate_request(req) else False
    return web.json_response(config)


# @token_auth.authenticate_access_decorator
# Explicitly disabling authentication for this end-point,
# because the front end requires this endpoint to be available at all times.
async def get_status(req):
    """API Endpoint to get the generic status of the server, MATLAB and MATLAB Licensing.

    Args:
        req (HTTPRequest): HTTPRequest Object.

    Returns:
        JSONResponse: JSONResponse object containing information about the server, MATLAB and MATLAB Licensing.
    """
    return await create_status_response(req.app)


# @token_auth.authenticate_access_decorator
# Explicitly disabling authentication for this end-point, as it checks for authenticity internally.
async def authenticate(req):
    """API Endpoint to authenticate request to access server

    Returns:
        JSONResponse: JSONResponse object containing information about authentication status and error if any.
    """
    is_authenticated = await token_auth.authenticate_request(req)
    error = (
        None
        if is_authenticated
        else marshal_error(
            InvalidTokenError(
                "Token invalid. Please enter a valid token to authenticate"
            )
        )
    )
    # If there is an error, state.error is not updated because the client may have set the
    # token incorrectly which is not an error raised on the backend.

    return web.json_response(
        {
            "authStatus": is_authenticated,
            "error": error,
        }
    )


@token_auth.authenticate_access_decorator
async def start_matlab(req):
    """API Endpoint to start MATLAB

    Args:
        req (HTTPRequest): HTTPRequest Object

    Returns:
        JSONResponse: JSONResponse object containing updated information on the state of MATLAB among other information.
    """
    state = req.app["state"]

    # Start MATLAB
    await state.start_matlab(restart_matlab=True)

    return await create_status_response(req.app)


@token_auth.authenticate_access_decorator
async def stop_matlab(req):
    """API Endpoint to stop MATLAB

    Args:
        req (HTTPRequest): HTTPRequest Object.

    Returns:
        JSONResponse: JSONResponse object containing updated information on the state of MATLAB among other information.
    """
    state = req.app["state"]

    await state.stop_matlab()

    return await create_status_response(req.app)


@token_auth.authenticate_access_decorator
async def set_licensing_info(req):
    """API Endpoint to set licensing information on the server side.

    Args:
        req (HTTPRequest): HTTPRequest Object

    Raises:
        Exception: If Licensing type is neither MHLM nor NLM.
        web.HTTPBadRequest: If any error with Licensing.

    Returns:
        JSONResponse: JSONResponse object containing updated information on the state of MATLAB among other information.
    """
    state = req.app["state"]

    data = await req.json()
    lic_type = data.get("type")

    try:
        if lic_type == "nlm":
            await state.set_licensing_nlm(data.get("connectionString"))

        elif lic_type == "mhlm":
            await state.set_licensing_mhlm(
                data.get("token"), data.get("emailAddress"), data.get("sourceId")
            )
        elif lic_type == "existing_license":
            state.set_licensing_existing_license()
        else:
            raise Exception(
                'License type must be "NLM" or "MHLM" or "ExistingLicense"!'
            )
    except Exception as e:
        raise web.HTTPBadRequest(text="Error with licensing!")

    # This is true for a user who has only one license associated with their account
    await __start_matlab_if_licensed(state)

    return await create_status_response(req.app)


@token_auth.authenticate_access_decorator
async def update_entitlement(req):
    """API endpoint to update selected entitlement to start MATLAB with.

    Args:
        req (HTTPRequest): HTTPRequest Object

    Returns:
        JSONResponse: JSONResponse object containing updated information on the state of MATLAB among other information.
    """
    state = req.app["state"]
    data = await req.json()
    lic_type = data.get("type")

    # Set the entitlement id only if we are not already licensed
    if lic_type == "mhlm" and not state.is_licensed():
        entitlement_id = data.get("entitlement_id")
        logger.debug(f"Received type: {lic_type}, entitlement_id: {entitlement_id}")
        await state.update_user_selected_entitlement_info(entitlement_id)
        await __start_matlab_if_licensed(state)

    return await create_status_response(req.app)


async def __start_matlab_if_licensed(state):
    # Start MATLAB if licensing is complete
    if state.is_licensed() and not isinstance(state.error, LicensingError):
        await state.start_matlab(restart_matlab=True)


@token_auth.authenticate_access_decorator
async def licensing_info_delete(req):
    """API Endpoint to stop MATLAB and remove licensing details.

    Args:
        req (HTTPRequest): HTTPRequest Object
    Returns:
        JSONResponse: JSONResponse object containing updated information on the state of MATLAB among other information.
    """
    state = req.app["state"]

    # Removing license information implies terminating MATLAB
    await state.stop_matlab()

    # Unset licensing information
    state.unset_licensing()

    # Persist licensing information
    state.persist_licensing()

    return await create_status_response(req.app)


@token_auth.authenticate_access_decorator
async def termination_integration_delete(req):
    """API Endpoint to terminate the Integration and shutdown the server.

    Args:
        req (HTTPRequest): HTTPRequest Object
    """
    logger.debug("Terminating the integration...")
    state = req.app["state"]

    # Send response manually because this has to happen before the application exits
    res = await create_status_response(req.app, "../")
    await res.prepare(req)
    await res.write_eof()

    logger.debug("Shutting down the server...")
    # End termination with 0 exit code to indicate intentional termination
    await req.app.shutdown()
    await req.app.cleanup()
    """When testing with pytest, its not possible to catch sys.exit(0) using the construct
    'with pytest.raises()', there by causing the test : test_termination_integration_delete()
    to fail. Inorder to avoid this, adding the below if condition to check to skip sys.exit(0) when testing
    """
    logger.debug("Exiting with return code 0")
    if not mwi_env.is_testing_mode_enabled():
        sys.exit(0)


# @token_auth.authenticate_access_decorator
# Explicitly disabling authentication for this end-point, as authenticity is checked by the redirected endpoint.
async def root_redirect(request):
    """API Endpoint to return the root index.html file.

    Args:
        request (HTTPRequest): HTTPRequest Object

    Returns:
        HTTPResponse: HTTPResponse Object containing the index.html file.
    """
    base_url = request.app["settings"]["base_url"]
    query_params = f"?{request.query_string}" if request.query_string else ""
    response_url = f"{base_url}/index.html{query_params}"

    return aiohttp.web.HTTPFound(response_url)


async def static_get(req):
    """Returns HTTP Response objects for the static files

    Args:
        req (HTTPRequest): HTTPRequest object

    Returns:
        HTTPResponse: HTTPResponse object containing the static file.
    """
    details = req.app["static_route_table"][req.path]
    return web.Response(
        headers=details["headers"],
        status=200,
        body=pkgutil.get_data(details["mod"], details["name"]),
    )


def make_static_route_table(app):
    """Traverses the built static files in ./gui folder and adds to a Dict.
    Key for the Dict is the complete path to a file
    Value for the Dict is the header and other information.

    Args:
        app (aiohttp server): The aiohttp server.

    Returns:
        Dict: Containing information about the static files and header information.
    """
    from pkg_resources import resource_isdir, resource_listdir

    from matlab_proxy import gui
    from matlab_proxy.gui import static
    from matlab_proxy.gui.static import css, js, media

    base_url = app["settings"]["base_url"]

    table = {}

    for mod, parent in [
        (gui.__name__, ""),
        (gui.static.__name__, "/static"),
        (gui.static.css.__name__, "/static/css"),
        (gui.static.js.__name__, "/static/js"),
        (gui.static.media.__name__, "/static/media"),
    ]:
        for name in resource_listdir(mod, ""):
            if not resource_isdir(mod, name):
                if name != "__init__.py":
                    # Special case for manifest.json
                    if "manifest.json" in name:
                        content_type = "application/manifest+json"
                    else:
                        content_type = mimetypes.guess_type(name)[0]

                    headers = {"content-type": content_type}
                    headers.update(app["settings"]["mwi_custom_http_headers"])

                    table[f"{base_url}{parent}/{name}"] = {
                        "mod": mod,
                        "name": name,
                        "headers": headers,
                    }

    return table


@token_auth.authenticate_access_decorator
async def matlab_view(req):
    """API Endpoint which proxies requests to the MATLAB Embedded Connector

    Args:
        req (HTTPRequest): HTTPRequest Object

    Raises:
        ValueError: When unable to handle WebSocket Request.
        web.HTTPNotFound: When a non-existing file is requested.

    Returns:
        WebSocketResponse or HTTPResponse: based on the Request type.
    """
    # Special keys for web socket requests
    CONNECTION = "connection"
    UPGRADE = "upgrade"

    reqH = req.headers.copy()

    state = req.app["state"]
    matlab_port = state.matlab_port
    matlab_protocol = req.app["settings"]["matlab_protocol"]
    mwapikey = req.app["settings"]["mwapikey"]
    matlab_base_url = f"{matlab_protocol}://127.0.0.1:{matlab_port}"

    # WebSocket
    # According to according to RFC6455 (https://www.rfc-editor.org/rfc/rfc6455.html)
    # the values of 'connection' and 'upgrade'  keys of request header
    # should be ASCII case-insensitive matches.
    if (
        reqH.get(CONNECTION, "").lower() == UPGRADE
        and reqH.get(UPGRADE, "").lower() == "websocket"
        and req.method == "GET"
    ):
        ws_server = web.WebSocketResponse()
        await ws_server.prepare(req)

        async with aiohttp.ClientSession(
            cookies=req.cookies, connector=aiohttp.TCPConnector(verify_ssl=False)
        ) as client_session:
            try:
                async with client_session.ws_connect(
                    matlab_base_url + req.path_qs,
                ) as ws_client:

                    async def wsforward(ws_from, ws_to):
                        async for msg in ws_from:
                            mt = msg.type
                            md = msg.data

                            # When a websocket is closed by the MATLAB JSD, it sends out a few http requests to the Embedded Connector about the events
                            # that had occured (figureWindowClosed etc.)
                            # The Embedded Connector responds by sending a message of type 'Error' with close code as Abnormal closure.
                            # When this happens, matlab-proxy can safely exit out of the loop
                            # and close the websocket connection it has with the Embedded Connector (ws_client)
                            if (
                                mt == aiohttp.WSMsgType.ERROR
                                and ws_from.close_code
                                == aiohttp.WSCloseCode.ABNORMAL_CLOSURE
                            ):
                                break

                            if mt == aiohttp.WSMsgType.TEXT:
                                await ws_to.send_str(md)
                            elif mt == aiohttp.WSMsgType.BINARY:
                                await ws_to.send_bytes(md)
                            elif mt == aiohttp.WSMsgType.PING:
                                await ws_to.ping()
                            elif mt == aiohttp.WSMsgType.PONG:
                                await ws_to.pong()
                            elif ws_to.closed:
                                await ws_to.close(
                                    code=ws_to.close_code, message=msg.extra
                                )
                            else:
                                raise ValueError(f"Unexpected message type: {msg}")

                    await asyncio.wait(
                        [
                            asyncio.create_task(wsforward(ws_server, ws_client)),
                            asyncio.create_task(wsforward(ws_client, ws_server)),
                        ],
                        return_when=asyncio.FIRST_COMPLETED,
                    )
                    return ws_server

            except Exception as err:
                logger.error(
                    f"Failed to create web socket connection with error: {err}"
                )

                code, message = (
                    aiohttp.WSCloseCode.INTERNAL_ERROR,
                    "Failed to establish websocket connection with MATLAB",
                )
                await ws_server.close(code=code, message=message.encode("utf-8"))
                raise aiohttp.WebSocketError(code=code, message=message)

    # Standard HTTP Request
    else:
        # Proxy, injecting request header
        async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(verify_ssl=False),
        ) as client_session:
            try:
                req_body = await transform_body(req)
                # Set content length in case of modification
                reqH["Content-Length"] = str(len(req_body))
                reqH["x-forwarded-proto"] = "http"

                async with client_session.request(
                    req.method,
                    f"{matlab_base_url}{req.rel_url}",
                    headers={**reqH, **{"mwapikey": mwapikey}},
                    allow_redirects=False,
                    data=req_body,
                ) as res:
                    headers = res.headers.copy()
                    body = await res.read()
                    headers.update(req.app["settings"]["mwi_custom_http_headers"])

                    return web.Response(headers=headers, status=res.status, body=body)

            # Handles any pending HTTP requests from the browser when the MATLAB process is terminated before responding to them.
            except (
                client_exceptions.ServerDisconnectedError,
                client_exceptions.ClientConnectionError,
            ):
                logger.debug(
                    "Failed to forward HTTP request as MATLAB process may not be running."
                )
                raise web.HTTPServiceUnavailable()

            # Some other exception has been raised (by MATLAB Embedded Connector), log the error and return 404
            except Exception as err:
                logger.error(
                    f"Failed to forward HTTP request to MATLAB with error: {err}"
                )
                raise web.HTTPNotFound()


async def transform_body(req):
    """Transform HTTP POST requests as required by the MATLAB JavaScript Desktop.

    Args:
        req (HTTPRequest): HTTPRequest Object.

    Returns:
        String: String containing JSON object representing the body of a HTTPResponse.
    """

    body = await req.read()

    # Only attempt to rewrite requests known to need rewriting
    if req.method == "POST" and req.rel_url.path.endswith("messageservice/json/secure"):
        data = json.loads(body)
        # Change messages.ClientType.properties.TYPE if necessary
        try:
            replace = False
            for client_type in data["messages"]["ClientType"]:
                if client_type["properties"]["TYPE"] == "jsd":
                    client_type["properties"]["TYPE"] = "jsd_rmt_tmw"
                    replace = True

            if replace is True:
                body = json.dumps(data)
        except KeyError:
            pass

    return body


async def license_init(app):
    """Initializes licensing for the app and is one of the starter tasks when
    the server is started.

    Args:
        app (aiohttp server): The aiohttp server.
    """
    state = app["state"]

    try:
        await state.init_licensing()
    except asyncio.CancelledError:
        pass


async def matlab_starter(app):
    """Upon app startup, start MATLAB if able to do so.

    Args:
        app (aiohttp server): The aiohttp server.
    """
    state = app["state"]

    try:
        if state.is_licensed() and await state.get_matlab_state() == "down":
            await state.start_matlab()
    except asyncio.CancelledError:
        # Ensure MATLAB is terminated
        await state.stop_matlab()


async def start_background_tasks(app):
    """Runs startup tasks asynchronously.
    Initiates licensing and starts matlab asynchronously.

    Args:
        app (aiohttp_server): Instance of aiohttp server
    """
    await license_init(app)
    await matlab_starter(app)


async def cleanup_background_tasks(app):
    """Runs cleanup tasks asynchronously.
    Stops any running tasks and stops matlab asynchronously.

    Args:
        app (aiohttp_server): Instance of aiohttp server
    """
    # First stop matlab
    state = app["state"]
    state.clean_up_mwi_server_session()

    await state.stop_matlab(force_quit=True)

    # Stop any running async tasks
    logger = mwi.logger.get()
    tasks = state.tasks
    for task_name, task in tasks.items():
        if not task.cancelled():
            logger.debug(f"Cancelling MWI task: {task_name} : {task} ")
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


def configure_and_start(app):
    """Configure the site for the app and update app with appropriate values

    Args:
        app (aiohttp.web.Application): A aiohttp web server.

    Returns:
        aiohttp.web.Application: Updated web server.
    """
    loop = util.get_event_loop()

    web_logger = None if not mwi_env.is_web_logging_enabled() else logger

    # Setup runner
    runner = web.AppRunner(app, logger=web_logger, access_log=web_logger)
    loop.run_until_complete(runner.setup())

    # Prepare site to start, then set port of the app.
    site = util.prepare_site(app, runner)

    # This would be required when MWI_APP_PORT env variable is not set and the site starts on a random port.
    app["settings"]["app_port"] = site._port

    # Update the site origin in settings.
    # The origin will be used for communicating with the Embedded connector.
    app["settings"]["mwi_server_url"] = util.get_access_url(app)

    loop.run_until_complete(site.start())

    logger.debug("Starting MATLAB proxy app")
    logger.debug(
        f' with base_url: {app["settings"]["base_url"]} and app_port:{app["settings"]["app_port"]}.'
    )

    app["state"].create_server_info_file()

    # Startup tasks are being done here as app.on_startup leads
    # to a race condition for mwi_server_url information which is
    # extracted from the site info.
    loop.run_until_complete(start_background_tasks(app))
    return app


# config has a default initializer because it needs to be callable without inputs from ADEV servers
def create_app(config_name=matlab_proxy.get_default_config_name()):
    """Creates the web server and adds the routes,settings and env_config to the server.

    Returns:
        aiohttp server: An aiohttp server with routes, settings and env_config.
    """
    app = web.Application(client_max_size=constants.MAX_HTTP_REQUEST_SIZE)

    # Get application settings
    app["settings"] = settings.get(
        config_name, dev=mwi_env.is_development_mode_enabled()
    )

    # Initialise application state
    app["state"] = AppState(app["settings"])

    # In development mode, the node development server proxies requests to this
    # development server instead of serving the static files directly
    if not mwi_env.is_development_mode_enabled():
        app["static_route_table"] = make_static_route_table(app)
        for key in app["static_route_table"].keys():
            app.router.add_route("GET", key, static_get)

    base_url = app["settings"]["base_url"]
    app.router.add_route("GET", f"{base_url}/get_status", get_status)
    app.router.add_route("POST", f"{base_url}/authenticate", authenticate)
    app.router.add_route("GET", f"{base_url}/get_auth_token", get_auth_token)
    app.router.add_route("GET", f"{base_url}/get_env_config", get_env_config)
    app.router.add_route("PUT", f"{base_url}/start_matlab", start_matlab)
    app.router.add_route("DELETE", f"{base_url}/stop_matlab", stop_matlab)
    app.router.add_route("PUT", f"{base_url}/set_licensing_info", set_licensing_info)
    app.router.add_route("PUT", f"{base_url}/update_entitlement", update_entitlement)
    app.router.add_route(
        "DELETE", f"{base_url}/set_licensing_info", licensing_info_delete
    )
    app.router.add_route(
        "DELETE", f"{base_url}/terminate_integration", termination_integration_delete
    )
    app.router.add_route("*", f"{base_url}/", root_redirect)
    app.router.add_route("*", f"{base_url}", root_redirect)

    app.router.add_route("*", f"{base_url}/{{proxyPath:.*}}", matlab_view)
    app.on_cleanup.append(cleanup_background_tasks)

    # Setup the session storage
    fernet_key = fernet.Fernet.generate_key()
    f = fernet.Fernet(fernet_key)
    aiohttp_session_setup(
        app, EncryptedCookieStorage(f, cookie_name="matlab-proxy-session")
    )

    return app


def main():
    """Starting point of the integration. Creates the web app and runs indefinitely."""

    # The integration needs to be called with --config flag.
    # Parse the passed cli arguments.
    desired_configuration_name = util.parse_cli_args()["config"]

    # Create, configure and start the app.
    app = create_app(config_name=desired_configuration_name)
    app = configure_and_start(app)

    loop = util.get_event_loop()

    # Add signal handlers for the current python process
    loop = util.add_signal_handlers(loop)
    try:
        loop.run_forever()
    except SystemExit:
        pass

    async def shutdown():
        """Shuts down the app in the event of a signal interrupt."""
        logger.info("Shutting down MATLAB proxy-app")

        await app.shutdown()
        await app.cleanup()

        # Shutdown any running tasks.
        await util.cancel_tasks(asyncio.all_tasks())

    try:
        loop.run_until_complete(shutdown())
    except:
        pass

    logger.info("Finished shutting down. Thank you for using the MATLAB proxy.")
    loop.close()
    sys.exit(0)
