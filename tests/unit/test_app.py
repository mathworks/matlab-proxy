# Copyright 2020-2025 The MathWorks, Inc.

import asyncio
import datetime
import json
import platform
import random
import time
from datetime import timedelta, timezone
from http import HTTPStatus, cookies

import pytest
from aiohttp import WSMsgType
from aiohttp.web import WebSocketResponse
from multidict import CIMultiDict

import tests.unit.test_constants as test_constants
from matlab_proxy import app, util
from matlab_proxy.app import matlab_view
from matlab_proxy.util.mwi import environment_variables as mwi_env
from matlab_proxy.util.mwi.exceptions import EntitlementError, MatlabInstallError
from tests.unit.fixtures.fixture_auth import (
    patch_authenticate_access_decorator,  # noqa: F401
)
from tests.unit.mocks.mock_client import MockWebSocketClient


@pytest.mark.parametrize(
    "no_proxy_user_configuration",
    [
        "",
        "1234.1234.1234, localhost , 0.0.0.0,1.2.3.4",
        "0.0.0.0",
        "1234.1234.1234",
        " 1234.1234.1234 ",
    ],
)
def test_configure_no_proxy_in_env(monkeypatch, no_proxy_user_configuration):
    """Tests the behavior of the configure_no_proxy_in_env function

    Args:
        monkeypatch (environment): MonkeyPatches the environment to mimic possible user environment settings
    """
    no_proxy_user_configuration_set = set(
        [val.lstrip().rstrip() for val in no_proxy_user_configuration.split(",")]
    )
    # Update the environment to simulate user environment
    monkeypatch.setenv("no_proxy", no_proxy_user_configuration)

    # This function will modify the environment variables to include 0.0.0.0, localhost & 127.0.0.1
    app.configure_no_proxy_in_env()

    import os

    modified_no_proxy_env = os.environ.get("no_proxy")

    # Convert to set to compare, as list generated need not be ordered
    modified_no_proxy_env_set = set(
        [val.lstrip().rstrip() for val in modified_no_proxy_env.split(",")]
    )

    expected_no_proxy_configuration_set = {"0.0.0.0", "localhost", "127.0.0.1"}

    # We expect the modified set of values to include the localhost configurations
    # along with whatever else the user had set with no duplicates.
    assert modified_no_proxy_env_set == no_proxy_user_configuration_set.union(
        expected_no_proxy_configuration_set
    )


def test_create_app(event_loop):
    """Test if aiohttp server is being created successfully.

    Checks if the aiohttp server is created successfully, routes, startup and cleanup
    tasks are added.
    """
    test_server = app.create_app()

    # Verify router is configured with some routes
    assert test_server.router._resources is not None

    # Verify app server has a cleanup task
    # By default there is 1 for clean up task
    assert len(test_server.on_cleanup) > 1
    event_loop.run_until_complete(test_server["state"].stop_server_tasks())


def get_email():
    """Returns a placeholder email

    Returns:
        String: A placeholder email as a string.
    """
    return "abc@mathworks.com"


def get_connection_string():
    """Returns a placeholder nlm connection string

    Returns:
        String : A placeholder nlm connection string
    """
    return "nlm@localhost.com"


async def wait_for_matlab_to_be_up(test_server, sleep_seconds):
    """Checks at max five times for the MATLAB status to be up and throws ConnectionError
    if MATLAB status is not up.

    This function mitigates the scenario where the tests may try to send the request
    to the test server and the MATLAB status is not up yet which may cause the test to fail
    unexpectedly.

    Use this function if the test intends to wait for the matlab status to be up before
    sending any requests.

    Args:
        test_server (aiohttp_client) : A aiohttp_client server to send HTTP GET request.
        sleep_seconds : Seconds to be sent to the asyncio.sleep method
    """

    count = 0
    while True:
        resp = await test_server.get("/get_status")
        assert resp.status == HTTPStatus.OK

        resp_json = json.loads(await resp.text())

        if resp_json["matlab"]["status"] == "up":
            break
        else:
            count += 1
            await asyncio.sleep(sleep_seconds)
            if count > test_constants.FIVE_MAX_TRIES:
                raise ConnectionError


@pytest.fixture(
    name="licensing_data",
    params=[
        {"input": None, "expected": None},
        {
            "input": {"type": "mhlm", "email_addr": get_email()},
            "expected": {
                "type": "mhlm",
                "emailAddress": get_email(),
                "entitlements": [],
                "entitlementId": None,
            },
        },
        {
            "input": {"type": "nlm", "conn_str": get_connection_string()},
            "expected": {"type": "nlm", "connectionString": get_connection_string()},
        },
        {
            "input": {"type": "existing_license"},
            "expected": {"type": "existing_license"},
        },
    ],
    ids=[
        "No Licensing info  supplied",
        "Licensing type is mhlm",
        "Licensing type is nlm",
        "Licensing type is existing_license",
    ],
)
def licensing_info_fixture(request):
    """A pytest fixture which returns licensing_data

    A parameterized pytest fixture which returns a licensing_data dict.
    licensing_data of three types:
        None : No licensing
        MHLM : Matlab Hosted License Manager
        NLM : Network License Manager.


    Args:
        request : A built-in pytest fixture

    Returns:
        Array : Containing expected and actual licensing data.
    """
    return request.param


def test_marshal_licensing_info(licensing_data):
    """Test app.marshal_licensing_info method works correctly

    This test checks if app.marshal_licensing_info returns correct licensing data.
    Test checks for 3 cases:
        1) No Licensing Provided
        2) MHLM type Licensing
        3) NLM type licensing

    Args:
        licensing_data (Array): An array containing actual and expected licensing data to assert.
    """

    actual_licensing_info = licensing_data["input"]
    expected_licensing_info = licensing_data["expected"]

    assert app.marshal_licensing_info(actual_licensing_info) == expected_licensing_info


@pytest.mark.parametrize(
    "actual_error, expected_error",
    [
        (None, None),
        (
            MatlabInstallError("'matlab' executable not found in PATH"),
            {
                "message": "'matlab' executable not found in PATH",
                "logs": None,
                "type": MatlabInstallError.__name__,
            },
        ),
    ],
    ids=["No error", "Raise Matlab Install Error"],
)
def test_marshal_error(actual_error, expected_error):
    """Test if marshal_error returns an expected Dict when an error is raised

    Upon raising MatlabInstallError, checks if the the relevant information is returned as a
    Dict.

    Args:
        actual_error (Exception): An instance of Exception class
        expected_error (Dict): A python Dict containing information on the type of Exception
    """
    assert app.marshal_error(actual_error) == expected_error


class FakeServer:
    """Context Manager class which returns a web server wrapped in aiohttp_client pytest fixture
    for testing.

    The server setup and startup does not need to mimic the way it is being done in main() method in app.py.
    Setting up the server in the context of Pytest.
    """

    def __init__(self, event_loop, aiohttp_client):
        self.loop = event_loop
        self.aiohttp_client = aiohttp_client

    def __enter__(self):
        server = app.create_app()
        self.server = app.configure_and_start(server)
        return self.loop.run_until_complete(self.aiohttp_client(self.server))

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.loop.run_until_complete(self.server.shutdown())
        self.loop.run_until_complete(self.server.cleanup())


@pytest.fixture
def mock_request(mocker):
    """Creates a mock request with required attributes"""
    req = mocker.MagicMock()
    req.app = {
        "state": mocker.MagicMock(matlab_port=8000),
        "settings": {
            "matlab_protocol": "http",
            "mwapikey": "test-key",
            "cookie_jar": None,
        },
    }
    req.headers = CIMultiDict()
    req.cookies = {}
    return req


@pytest.fixture(name="mock_websocket_messages")
def mock_messages(mocker):
    # Mock WebSocket messages
    return [
        mocker.MagicMock(type=WSMsgType.TEXT, data="test message"),
        mocker.MagicMock(type=WSMsgType.BINARY, data=b"test binary"),
        mocker.MagicMock(type=WSMsgType.PING),
        mocker.MagicMock(type=WSMsgType.PONG),
    ]


@pytest.fixture(name="test_server")
def test_server_fixture(event_loop, aiohttp_client, monkeypatch, request):
    """A pytest fixture which yields a test server to be used by tests.

    Args:
        loop (Event loop): The built-in event loop provided by pytest.
        aiohttp_client (aiohttp_client): Built-in pytest fixture used as a wrapper to the aiohttp web server.

    Yields:
        aiohttp_client : A aiohttp_client server used by tests.
    """
    # Default set of environment variables for testing convenience
    default_env_vars_for_testing = [
        (mwi_env.get_env_name_enable_mwi_auth_token(), "False")
    ]
    custom_env_vars = getattr(request, "param", None)

    if custom_env_vars:
        default_env_vars_for_testing.extend(custom_env_vars)

    for env_var_name, env_var_value in default_env_vars_for_testing:
        monkeypatch.setenv(env_var_name, env_var_value)

    try:
        with FakeServer(event_loop, aiohttp_client) as test_server:
            yield test_server

    except ProcessLookupError:
        pass

    finally:
        # Cleaning up the environment variables set for testing
        for env_var_name, _ in default_env_vars_for_testing:
            monkeypatch.delenv(env_var_name, raising="False")


async def test_get_status_route(test_server):
    """Test to check endpoint : "/get_status"

    Args:
        test_server (aiohttp_client): A aiohttp_client server for sending GET request.
    """

    resp = await test_server.get("/get_status")
    assert resp.status == HTTPStatus.OK


async def test_clear_client_id_route(test_server):
    """Test to check endpoint: "/clear_client_id"

    Args:
        test_server (aiohttp_client): A aiohttp_client server for sending POST request.
    """

    state = test_server.server.app["state"]
    state.active_client = "mock_client_id"
    resp = await test_server.post("/clear_client_id")
    assert resp.status == HTTPStatus.OK
    assert state.active_client is None


async def test_get_env_config(test_server):
    """Test to check endpoint : "/get_env_config"

    Args:
        test_server (aiohttp_client): A aiohttp_client server for sending GET request.
    """
    expected_json_structure = {
        "authentication": {"enabled": False, "status": False},
        "matlab": {
            "status": "up",
            "version": "R2023a",
            "supportedVersions": ["R2020b", "R2023a"],
        },
        "doc_url": "foo",
        "extension_name": "bar",
        "extension_name_short_description": "foobar",
        "should_show_shutdown_button": True,
        "isConcurrencyEnabled": "foobar",
        "idleTimeoutDuration": 100,
    }
    resp = await test_server.get("/get_env_config")
    assert resp.status == HTTPStatus.OK

    text = await resp.json()
    assert text is not None
    assert set(expected_json_structure.keys()) == set(text.keys())


async def test_start_matlab_route(test_server):
    """Test to check endpoint : "/start_matlab"

    Test waits for matlab status to be "up" before sending the GET request to start matlab
    Checks whether matlab restarts.

    Args:
        test_server (aiohttp_client): A aiohttp_client server to send GET request to.
    """
    # Waiting for the matlab process to start up.
    await wait_for_matlab_to_be_up(
        test_server, test_constants.CHECK_MATLAB_STATUS_INTERVAL
    )

    # Send get request to end point
    await test_server.put("/start_matlab")

    # Check if Matlab restarted successfully
    await __check_for_matlab_status(test_server, "starting")


async def __check_for_matlab_status(test_server, status, sleep_interval=0.5):
    """Helper function to check if the status of MATLAB returned by the server is either of the values mentioned in statuses

    Args:
        test_server (aiohttp_client): A aiohttp_client server to send HTTP DELETE request.
        statuses ([str]): Possible MATLAB statuses.

    Raises:
        ConnectionError: Exception raised if the test_server is not reachable.
    """
    count = 0
    while True:
        resp = await test_server.get("/get_status")
        assert resp.status == HTTPStatus.OK
        resp_json = json.loads(await resp.text())
        if resp_json["matlab"]["status"] == status:
            break
        else:
            count += 1
            await asyncio.sleep(sleep_interval)
            if count > test_constants.FIVE_MAX_TRIES:
                raise ConnectionError


async def test_stop_matlab_route(test_server):
    """Test to check endpoint : "/stop_matlab"

    Sends HTTP DELETE request to stop matlab and checks if matlab status is down.

    Args:
        test_server (aiohttp_client): A aiohttp_client server to send HTTP DELETE request.
    """
    # Arrange
    # Nothing to arrange

    # Act
    resp = await test_server.delete("/stop_matlab")
    assert resp.status == HTTPStatus.OK

    # Assert
    # Check if Matlab restarted successfully
    await __check_for_matlab_status(test_server, "stopping")


async def test_root_redirect(test_server):
    """Test to check endpoint : "/"

    Should throw a 404 error. This will look for index.html in root directory of the project
    (In non-dev mode, root directory is the package)
    This file will not be available in the expected location in dev mode.

    Args:
        test_server (aiohttp_client):  A aiohttp_client server to send HTTP GET request.

    """
    count = 0
    while True:
        resp = await test_server.get("/")
        if resp.status == HTTPStatus.SERVICE_UNAVAILABLE:
            time.sleep(test_constants.ONE_SECOND_DELAY)
            count += 1
        else:
            assert resp.status == HTTPStatus.NOT_FOUND
            break

        if count > test_constants.FIVE_MAX_TRIES:
            raise ConnectionError


@pytest.fixture(name="proxy_payload")
def proxy_payload_fixture():
    """Pytest fixture which returns a Dict representing the payload.

    Returns:
        Dict: A Dict representing the payload for HTTP request.
    """
    payload = {"messages": {"ClientType": [{"properties": {"TYPE": "jsd"}}]}}

    return payload


async def test_matlab_proxy_404(proxy_payload, test_server):
    """Test to check if test_server is able to proxy HTTP request to fake matlab server
    for a non-existing file. Should return 404 status code in response

    Args:
        proxy_payload (Dict): Pytest fixture which returns a Dict.
        test_server (aiohttp_client): Test server to send HTTP requests.
    """

    headers = {"content-type": "application/json"}

    # Request a non-existing html file.
    # Request gets proxied to app.matlab_view() which should raise HTTPNotFound() exception ie. return HTTP status code 404

    count = 0
    while True:
        resp = await test_server.post(
            "/1234.html", data=json.dumps(proxy_payload), headers=headers
        )
        if resp.status == HTTPStatus.SERVICE_UNAVAILABLE:
            time.sleep(test_constants.ONE_SECOND_DELAY)
            count += 1
        else:
            assert resp.status == HTTPStatus.NOT_FOUND
            break

        if count > test_constants.FIVE_MAX_TRIES:
            raise ConnectionError


async def test_matlab_proxy_http_get_request(proxy_payload, test_server):
    """Test to check if test_server proxies a HTTP request to fake matlab server and returns
    the response back

    Args:
        proxy_payload (Dict): Pytest fixture which returns a Dict representing payload for the HTTP request
        test_server (aiohttp_client): Test server to send HTTP requests.

    Raises:
        ConnectionError: If fake matlab server is not reachable from the test server, raises ConnectionError
    """

    max_tries = 5
    count = 0

    while True:
        resp = await test_server.get(
            "/http_get_request.html", data=json.dumps(proxy_payload)
        )

        if resp.status in (HTTPStatus.NOT_FOUND, HTTPStatus.SERVICE_UNAVAILABLE):
            time.sleep(1)
            count += 1

        else:
            resp_body = await resp.text()
            assert json.dumps(proxy_payload) == resp_body
            break

        if count > max_tries:
            raise ConnectionError


async def test_matlab_proxy_http_put_request(proxy_payload, test_server):
    """Test to check if test_server proxies a HTTP request to fake matlab server and returns
    the response back

    Args:
        proxy_payload (Dict): Pytest fixture which returns a Dict representing payload for the HTTP request
        test_server (aiohttp_client): Test server to send HTTP requests.

    Raises:
        ConnectionError: If fake matlab server is not reachable from the test server, raises ConnectionError
    """

    max_tries = 5
    count = 0

    while True:
        resp = await test_server.put(
            "/http_put_request.html", data=json.dumps(proxy_payload)
        )

        if resp.status in (HTTPStatus.NOT_FOUND, HTTPStatus.SERVICE_UNAVAILABLE):
            time.sleep(1)
            count += 1

        else:
            resp_body = await resp.text()
            assert json.dumps(proxy_payload) == resp_body
            break

        if count > max_tries:
            raise ConnectionError


async def test_matlab_proxy_http_delete_request(proxy_payload, test_server):
    """Test to check if test_server proxies a HTTP request to fake matlab server and returns
    the response back

    Args:
        proxy_payload (Dict): Pytest fixture which returns a Dict representing payload for the HTTP request
        test_server (aiohttp_client): Test server to send HTTP requests.

    Raises:
        ConnectionError: If fake matlab server is not reachable from the test server, raises ConnectionError
    """

    max_tries = 5
    count = 0

    while True:
        resp = await test_server.delete(
            "/http_delete_request.html", data=json.dumps(proxy_payload)
        )

        if resp.status in (HTTPStatus.NOT_FOUND, HTTPStatus.SERVICE_UNAVAILABLE):
            time.sleep(1)
            count += 1

        else:
            resp_body = await resp.text()
            assert json.dumps(proxy_payload) == resp_body
            break

        if count > max_tries:
            raise ConnectionError


async def test_matlab_proxy_http_post_request(proxy_payload, test_server):
    """Test to check if test_server proxies http post request to fake matlab server.
    Checks if payload is being modified before proxying.
    Args:
        proxy_payload (Dict): Pytest fixture which returns a Dict representing payload for the HTTP Request
        test_server (aiohttp_client): Test server to send HTTP requests

    Raises:
        ConnectionError: If unable to proxy to fake matlab server raise Connection error
    """
    max_tries = 5
    count = 0

    while True:
        resp = await test_server.post(
            "/messageservice/json/secure",
            data=json.dumps(proxy_payload),
        )

        if resp.status in (HTTPStatus.NOT_FOUND, HTTPStatus.SERVICE_UNAVAILABLE):
            time.sleep(1)
            count += 1

        else:
            resp_json = await resp.json()
            assert set(resp_json.keys()).issubset(proxy_payload.keys())
            break

        if count > max_tries:
            raise ConnectionError


async def test_set_licensing_info_put_nlm(test_server):
    """Test to check endpoint : "/set_licensing_info"

    Test which sends HTTP PUT request with NLM licensing information.
    Args:
        test_server (aiohttp_client): A aiohttp_client server to send HTTP GET request.
    """

    data = {
        "type": "nlm",
        "status": "starting",
        "version": "R2020b",
        "connectionString": "123@nlm",
    }
    resp = await test_server.put("/set_licensing_info", data=json.dumps(data))
    assert resp.status == HTTPStatus.OK


async def test_set_licensing_info_put_invalid_license(test_server):
    """Test to check endpoint : "/set_licensing_info"

    Test which sends HTTP PUT request with INVALID licensing information type.
    Args:
        test_server (aiohttp_client): A aiohttp_client server to send HTTP GET request.
    """

    data = {
        "type": "INVALID_TYPE",
        "status": "starting",
        "version": "R2020b",
        "connectionString": "123@nlm",
    }
    resp = await test_server.put("/set_licensing_info", data=json.dumps(data))
    assert resp.status == HTTPStatus.BAD_REQUEST


# While acceessing matlab-proxy directly, the web socket request looks like
#     {
#         "connection": "Upgrade",
#         "Upgrade": "websocket",
#     }
# whereas while accessing matlab-proxy with nginx as the reverse proxy, the nginx server
# modifies the web socket request to
#     {
#         "connection": "upgrade",
#         "upgrade": "websocket",
#     }
@pytest.mark.parametrize(
    "headers",
    [
        CIMultiDict(
            {
                "connection": "Upgrade",
                "Upgrade": "websocket",
            }
        ),
        CIMultiDict(
            {
                "connection": "upgrade",
                "upgrade": "websocket",
            }
        ),
    ],
    ids=["Uppercase header", "Lowercase header"],
)
async def test_matlab_view_websocket_success(
    mocker,
    mock_request,
    mock_websocket_messages,
    headers,
    patch_authenticate_access_decorator,  # noqa: F401
):
    """Test successful websocket connection and message forwarding"""

    # Configure request for WebSocket
    mock_request.headers = headers
    mock_request.method = "GET"
    mock_request.path_qs = "/test"

    # Mock WebSocket setup
    mock_ws_server = mocker.MagicMock(spec=WebSocketResponse)
    mocker.patch(
        "matlab_proxy.app.aiohttp.web.WebSocketResponse", return_value=mock_ws_server
    )

    # Mock WebSocket client
    mock_ws_client = MockWebSocketClient(messages=mock_websocket_messages)
    mocker.patch(
        "matlab_proxy.app.aiohttp.ClientSession.ws_connect", return_value=mock_ws_client
    )

    # Execute
    result = await matlab_view(mock_request)

    # Assertions
    assert result == mock_ws_server
    assert mock_ws_server.send_str.call_count == 1
    assert mock_ws_server.send_bytes.call_count == 1
    assert mock_ws_server.ping.call_count == 1
    assert mock_ws_server.pong.call_count == 1


async def test_set_licensing_info_put_mhlm(test_server):
    """Test to check endpoint : "/set_licensing_info"

    Test which sends HTTP PUT request with MHLM licensing information.
    Args:
        test_server (aiohttp_client): A aiohttp_client server to send HTTP GET request.
    """
    # FIXME: This test is talking to production loginws endpoint and is resulting in an exception.
    # TODO: Use mocks to test the mhlm workflows is working as expected
    data = {
        "type": "mhlm",
        "status": "starting",
        "version": "R2020b",
        "token": "123@nlm",
        "emailaddress": "123@nlm",
        "sourceId": "123@nlm",
    }
    resp = await test_server.put("/set_licensing_info", data=json.dumps(data))
    assert resp.status == HTTPStatus.OK


async def test_set_licensing_info_put_existing_license(test_server):
    """Test to check endpoint : "/set_licensing_info"

    Test which sends HTTP PUT request with local licensing information.
    Args:
        test_server (aiohttp_client): A aiohttp_client server to send HTTP GET request.
    """

    data = {"type": "existing_license"}
    resp = await test_server.put("/set_licensing_info", data=json.dumps(data))
    assert resp.status == HTTPStatus.OK


async def test_set_licensing_info_delete(test_server):
    """Test to check endpoint : "/set_licensing_info"

    Test which sends HTTP DELETE request to remove licensing. Checks if licensing is set to None
    After request is sent.
    Args:
        test_server (aiohttp_client):  A aiohttp_client server to send HTTP GET request.
    """

    resp = await test_server.delete("/set_licensing_info")
    resp_json = json.loads(await resp.text())
    assert resp.status == HTTPStatus.OK and resp_json["licensing"] is None


async def test_set_termination_integration_delete(test_server):
    """Test to check endpoint : "/shutdown_integration"

    Test which sends HTTP DELETE request to shutdown integration. Checks if integration is shutdown
    successfully.
    Args:
        test_server (aiohttp_client):  A aiohttp_client server to send HTTP GET request.
    """
    # Not awaiting the response here explicitly as the event loop is stopped in the
    # handler function.
    test_server.delete("/shutdown_integration")

    resp = await test_server.get("/")

    # Assert that the service is unavailable
    assert resp.status == 503


def test_get_access_url(test_server):
    """Should return a url with 127.0.0.1 in test mode

    Args:
        test_server (aiohttp.web.Application): Application Server
    """

    assert "127.0.0.1" in util.get_access_url(test_server.app)


@pytest.fixture(name="non_test_env")
def non_test_env_fixture(monkeypatch):
    """Monkeypatches MWI_TEST env var to false

    Args:
        monkeypatch (_pytest.monkeypatch.MonkeyPatch): To monkeypatch env vars
    """
    monkeypatch.setenv(mwi_env.get_env_name_testing(), "false")


@pytest.fixture(name="non_default_host_interface")
def non_default_host_interface_fixture(monkeypatch):
    """Monkeypatches MWI_TEST env var to false

    Args:
        monkeypatch (_pytest.monkeypatch.MonkeyPatch): To monkeypatch env vars
    """
    monkeypatch.setenv(mwi_env.get_env_name_app_host(), "0.0.0.0")


# For pytest fixtures, order of arguments matter.
# First set the default host interface to a non-default value
# Then set MWI_TEST to false and then create an instance of the test_server
# This order will set the test_server with appropriate values.


@pytest.mark.skipif(
    platform.system() == "Linux" or platform.system() == "Darwin",
    reason="Testing the windows access URL",
)
def test_get_access_url_non_dev_windows(
    non_default_host_interface, non_test_env, test_server
):
    """Test to check access url to be 127.0.0.1 in non-dev mode on Windows"""
    assert "127.0.0.1" in util.get_access_url(test_server.app)


@pytest.mark.skipif(
    platform.system() == "Windows", reason="Testing the non-Windows access URL"
)
def test_get_access_url_non_dev_posix(
    non_default_host_interface, non_test_env, test_server
):
    """Test to check access url to be 0.0.0.0 in non-dev mode on Linux/Darwin"""
    assert "0.0.0.0" in util.get_access_url(test_server.app)


@pytest.fixture(name="set_licensing_info_mock_fetch_single_entitlement")
def set_licensing_info_mock_fetch_single_entitlement_fixture():
    """Fixture that returns a single entitlement

    Returns:
        json array: An array consisting of single entitlement information
    """
    return [
        {"id": "Entitlement3", "label": "Label3", "license_number": "License3"},
    ]


@pytest.fixture(name="set_licensing_info_mock_fetch_multiple_entitlements")
def set_licensing_info_mock_fetch_multiple_entitlements_fixture():
    """Fixture that returns multiple entitlements

    Returns:
        json array: An array consisting of multiple entitlements
    """
    return [
        {"id": "Entitlement1", "label": "Label1", "license_number": "License1"},
        {"id": "Entitlement2", "label": "Label2", "license_number": "License2"},
    ]


@pytest.fixture(name="set_licensing_info_mock_access_token")
def set_licensing_info_mock_access_token_fixture():
    """Pytest fixture that returns a mock token that mimics mw.fetch_access_token() response"""
    access_token_string = int("".join([str(random.randint(0, 10)) for _ in range(272)]))
    return {
        "token": str(access_token_string),
    }


@pytest.fixture(name="set_licensing_info_mock_expand_token")
def set_licensing_info_mock_expand_token_fixture():
    """Pytest fixture which returns a dict

    The return value represents a valid json response when mw.fetch_expand_token function is called.

    Returns:
        json data with mimics mw.fetch_expand_token() response
    """
    now = datetime.datetime.now(timezone.utc)
    first_name = "abc"

    json_data = {
        "expiry": str((now + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S.%f%z")),
        "first_name": first_name,
        "last_name": "def",
        "display_name": first_name,
        "email_addr": "test@test.com",
        "user_id": "".join([str(random.randint(0, 10)) for _ in range(13)]),
        "profile_id": "".join([str(random.randint(0, 10)) for _ in range(8)]),
    }

    return json_data


@pytest.fixture(name="set_licensing_info")
async def set_licensing_info_fixture(
    mocker,
    test_server,
    set_licensing_info_mock_expand_token,
    set_licensing_info_mock_access_token,
    set_licensing_info_mock_fetch_multiple_entitlements,
):
    """Fixture to setup correct licensing state on the server"""
    mocker.patch(
        "matlab_proxy.app_state.mw.fetch_expand_token",
        return_value=set_licensing_info_mock_expand_token,
    )

    mocker.patch(
        "matlab_proxy.app_state.mw.fetch_access_token",
        return_value=set_licensing_info_mock_access_token,
    )

    mocker.patch(
        "matlab_proxy.app_state.mw.fetch_entitlements",
        return_value=set_licensing_info_mock_fetch_multiple_entitlements,
    )

    data = {
        "type": "mhlm",
        "status": "starting",
        "version": "R2020b",
        "token": "abc@nlm",
        "emailAddress": "abc@nlm",
        "sourceId": "abc@nlm",
        "matlabVersion": "R2023a",
    }

    # Waiting for the matlab process to start up.
    await wait_for_matlab_to_be_up(test_server, test_constants.ONE_SECOND_DELAY)

    # Set matlab_version to None to check if the version is updated
    # after sending a request t o /set_licensing_info endpoint
    test_server.server.app["settings"]["matlab_version"] = None

    # Pre-req: stop the matlab that got started during test server startup
    resp = await test_server.delete("/stop_matlab")
    assert resp.status == HTTPStatus.OK

    resp = await test_server.put("/set_licensing_info", data=json.dumps(data))
    assert resp.status == HTTPStatus.OK

    # Assert whether the matlab_version was updated from None when licensing type is mhlm
    assert test_server.server.app["settings"]["matlab_version"] == "R2023a"

    return test_server


async def test_set_licensing_mhlm_zero_entitlement(
    mocker,
    set_licensing_info_mock_expand_token,
    set_licensing_info_mock_access_token,
    test_server,
):
    # Patching the functions where it is used (and not where it is defined)
    mocker.patch(
        "matlab_proxy.app_state.mw.fetch_expand_token",
        return_value=set_licensing_info_mock_expand_token,
    )

    mocker.patch(
        "matlab_proxy.app_state.mw.fetch_access_token",
        return_value=set_licensing_info_mock_access_token,
    )

    mocker.patch(
        "matlab_proxy.app_state.mw.fetch_entitlements",
        side_effect=EntitlementError(
            "Your MathWorks account is not linked to a valid license for MATLAB"
        ),
    )

    data = {
        "type": "mhlm",
        "status": "starting",
        "version": "R2020b",
        "token": "abc@nlm",
        "emailaddress": "abc@nlm",
        "sourceId": "abc@nlm",
    }
    # Pre-req: stop the matlab that got started as during test server startup
    resp = await test_server.delete("/stop_matlab")
    assert resp.status == HTTPStatus.OK

    resp = await test_server.put("/set_licensing_info", data=json.dumps(data))
    assert resp.status == HTTPStatus.OK
    resp_json = await resp.json()
    expectedError = EntitlementError(message="entitlement error")
    assert resp_json["error"]["type"] == type(expectedError).__name__


async def test_set_licensing_mhlm_single_entitlement(
    mocker,
    test_server,
    set_licensing_info_mock_expand_token,
    set_licensing_info_mock_access_token,
    set_licensing_info_mock_fetch_single_entitlement,
):
    mocker.patch(
        "matlab_proxy.app_state.mw.fetch_expand_token",
        return_value=set_licensing_info_mock_expand_token,
    )

    mocker.patch(
        "matlab_proxy.app_state.mw.fetch_access_token",
        return_value=set_licensing_info_mock_access_token,
    )

    mocker.patch(
        "matlab_proxy.app_state.mw.fetch_entitlements",
        return_value=set_licensing_info_mock_fetch_single_entitlement,
    )

    data = {
        "type": "mhlm",
        "status": "starting",
        "version": "R2020b",
        "token": "abc@nlm",
        "emailAddress": "abc@nlm",
        "sourceId": "abc@nlm",
    }
    # Pre-req: stop the matlab that got started during test server startup
    resp = await test_server.delete("/stop_matlab")
    assert resp.status == HTTPStatus.OK

    resp = await test_server.put("/set_licensing_info", data=json.dumps(data))
    assert resp.status == HTTPStatus.OK
    resp_json = await resp.json()
    assert len(resp_json["licensing"]["entitlements"]) == 1
    assert resp_json["licensing"]["entitlementId"] == "Entitlement3"

    # validate that MATLAB has started correctly
    await __check_for_matlab_status(test_server, "up", sleep_interval=2)

    # test-cleanup: unset licensing
    # without this, we can leave test drool related to cached license file
    # which can impact other non-dev workflows
    resp = await test_server.delete("/set_licensing_info")
    assert resp.status == HTTPStatus.OK


async def test_set_licensing_mhlm_multi_entitlements(
    mocker,
    test_server,
    set_licensing_info_mock_expand_token,
    set_licensing_info_mock_access_token,
    set_licensing_info_mock_fetch_multiple_entitlements,
):
    mocker.patch(
        "matlab_proxy.app_state.mw.fetch_expand_token",
        return_value=set_licensing_info_mock_expand_token,
    )

    mocker.patch(
        "matlab_proxy.app_state.mw.fetch_access_token",
        return_value=set_licensing_info_mock_access_token,
    )

    mocker.patch(
        "matlab_proxy.app_state.mw.fetch_entitlements",
        return_value=set_licensing_info_mock_fetch_multiple_entitlements,
    )

    data = {
        "type": "mhlm",
        "status": "starting",
        "version": "R2020b",
        "token": "abc@nlm",
        "emailaddress": "abc@nlm",
        "sourceId": "abc@nlm",
    }
    # Pre-req: stop the matlab that got started as during test server startup
    resp = await test_server.delete("/stop_matlab")
    assert resp.status == HTTPStatus.OK

    resp = await test_server.put("/set_licensing_info", data=json.dumps(data))
    assert resp.status == HTTPStatus.OK
    resp_json = await resp.json()
    assert len(resp_json["licensing"]["entitlements"]) == 2
    assert resp_json["licensing"]["entitlementId"] == None

    # MATLAB should not start if there are multiple entitlements and
    # user hasn't selected the license yet
    resp = await test_server.get("/get_status")
    assert resp.status == HTTPStatus.OK
    __check_for_matlab_status(test_server, "down")

    # test-cleanup: unset licensing
    resp = await test_server.delete("/set_licensing_info")
    assert resp.status == HTTPStatus.OK


async def test_update_entitlement_with_correct_entitlement(set_licensing_info):
    data = {
        "type": "mhlm",
        "entitlement_id": "Entitlement1",
    }
    # This test_server is pre-configured with multiple entitlements on app state but no entitlmentId
    test_server = set_licensing_info
    resp = await test_server.put("/update_entitlement", data=json.dumps(data))
    assert resp.status == HTTPStatus.OK
    resp_json = await resp.json()
    assert resp_json["matlab"]["status"] != "down"

    # test-cleanup: unset licensing
    resp = await test_server.delete("/set_licensing_info")
    assert resp.status == HTTPStatus.OK


async def test_get_auth_token_route(test_server):
    """Test to check endpoint : "/get_auth_token"

    Args:
        test_server (aiohttp_client): A aiohttp_client server for sending GET request.
    """
    resp = await test_server.get("/get_auth_token")
    res_json = await resp.json()
    # Testing the default dev configuration where the auth is disabled
    assert res_json["token"] == None
    assert resp.status == HTTPStatus.OK


async def test_check_for_concurrency(test_server):
    """Test to check the response from endpoint : "/get_status" with different query parameters

    Test requests the "/get_status" endpoint with different query parameters to check
    how the server responds.

    Args:
        test_server (aiohttp_client): A aiohttp_client server to send GET request to.
    """
    # Request server to check if concurrency check is enabled.

    env_resp = await test_server.get("/get_env_config")
    assert env_resp.status == HTTPStatus.OK
    env_resp_json = json.loads(await env_resp.text())
    if env_resp_json["isConcurrencyEnabled"]:
        # A normal request should not repond with client id or active status
        status_resp = await test_server.get("/get_status")
        assert status_resp.status == HTTPStatus.OK
        status_resp_json = json.loads(await status_resp.text())
        assert "clientId" not in status_resp_json
        assert "isActiveClient" not in status_resp_json

        # When the request comes from the desktop app the server should respond with client id and active status
        status_resp = await test_server.get('/get_status?IS_DESKTOP="true"')
        assert status_resp.status == HTTPStatus.OK
        status_resp_json = json.loads(await status_resp.text())
        assert "clientId" in status_resp_json
        assert "isActiveClient" in status_resp_json

        # When the desktop client requests for a session transfer without client id respond with cliend id and active status should be true
        status_resp = await test_server.get(
            '/get_status?IS_DESKTOP="true"&TRANSFER_SESSION="true"'
        )
        assert status_resp.status == HTTPStatus.OK
        status_resp_json = json.loads(await status_resp.text())
        assert "clientId" in status_resp_json
        assert status_resp_json["isActiveClient"] == True

        # When transfering the session is requested by a client whihc is not a desktop client it should be ignored
        status_resp = await test_server.get('/get_status?TRANSFER_SESSION="true"')
        assert status_resp.status == HTTPStatus.OK
        status_resp_json = json.loads(await status_resp.text())
        assert "clientId" not in status_resp_json
        assert "isActiveClient" not in status_resp_json

        # When the desktop client requests for a session transfer with a client id then respond only with active status
        status_resp = await test_server.get(
            '/get_status?IS_DESKTOP="true"&MWI_CLIENT_ID="foobar"&TRANSFER_SESSION="true"'
        )
        assert status_resp.status == HTTPStatus.OK
        status_resp_json = json.loads(await status_resp.text())
        assert "clientId" not in status_resp_json
        assert status_resp_json["isActiveClient"] == True
    else:
        # When Concurrency check is disabled the response should not contain client id or active status
        status_resp = await test_server.get("/get_status")
        assert status_resp.status == HTTPStatus.OK
        status_resp_json = json.loads(await status_resp.text())
        assert "clientId" not in status_resp_json
        assert "isActiveClient" not in status_resp_json
        status_resp = await test_server.get(
            '/get_status?IS_DESKTOP="true"&MWI_CLIENT_ID="foobar"&TRANSFER_SESSION="true"'
        )
        assert status_resp.status == HTTPStatus.OK
        status_resp_json = json.loads(await status_resp.text())
        assert "clientId" not in status_resp_json
        assert "isActiveClient" not in status_resp_json


# Pytest construct to set the environment variable `MWI_ENABLE_COOKIE_JAR` to `"True"`
# before initializing the test_server.
@pytest.mark.parametrize(
    "test_server",
    [
        [(mwi_env.Experimental.get_env_name_use_cookie_cache(), "True")],
    ],
    indirect=True,
)
async def test_cookie_jar_http_request(proxy_payload, test_server):
    # Arrange
    actual_custom_cookie = cookies.Morsel()
    actual_custom_cookie.set("custom_cookie", "cookie_value", "cookie_value")
    actual_custom_cookie["domain"] = "example.com"
    actual_custom_cookie["path"] = "/"
    actual_custom_cookie["HttpOnly"] = True
    actual_custom_cookie["expires"] = (
        datetime.datetime.now() + timedelta(days=1)
    ).strftime("%a, %d-%b-%Y %H:%M:%S GMT")

    await wait_for_matlab_to_be_up(test_server, test_constants.ONE_SECOND_DELAY)

    # Manually update cookie in cookie jar
    test_server.app["settings"]["cookie_jar"]._cookie_jar[
        "custom_cookie"
    ] = actual_custom_cookie

    # Act
    async with await test_server.get(
        "/http_get_request.html", data=json.dumps(proxy_payload)
    ) as _:
        expected_custom_cookie = test_server.app["settings"]["cookie_jar"]._cookie_jar[
            "custom_cookie"
        ]

        # Assert
        assert actual_custom_cookie == expected_custom_cookie


# Pytest construct to set the environment variable `MWI_ENABLE_COOKIE_JAR` to `"True"`
# before initializing the test_server.
@pytest.mark.parametrize(
    "test_server",
    [
        [(mwi_env.Experimental.get_env_name_use_cookie_cache(), "True")],
    ],
    indirect=True,
)
async def test_cookie_jar_web_socket(proxy_payload, test_server):
    # Arrange

    # Createa a custom cookie
    actual_custom_cookie = cookies.Morsel()
    actual_custom_cookie.set("custom_cookie", "cookie_value", "cookie_value")
    actual_custom_cookie["domain"] = "example.com"
    actual_custom_cookie["path"] = "/"
    actual_custom_cookie["expires"] = (
        datetime.datetime.now() + timedelta(days=1)
    ).strftime("%a, %d-%b-%Y %H:%M:%S GMT")

    # Update cookie in cookie jar
    test_server.app["settings"]["cookie_jar"]._cookie_jar[
        "custom_cookie"
    ] = actual_custom_cookie

    await wait_for_matlab_to_be_up(test_server, test_constants.ONE_SECOND_DELAY)

    # Act
    async with test_server.get(
        "/http_ws_request.html/",
        headers={
            # Headers required to initiate a websocket connection
            # First 2 headers are required for the connection upgrade
            "Connection": "upgrade",
            "upgrade": "websocket",
            "Sec-WebSocket-Version": "13",  # Required for initiating the websocket handshake with aiohttp server
            "Sec-WebSocket-Key": "dGhlIHNhbXBsZSBub25jZQ==",  # Optional unique key for the websocket handshake
        },
    ) as _:
        expected_custom_cookie = test_server.app["settings"]["cookie_jar"]._cookie_jar[
            "custom_cookie"
        ]
        # Assert
        assert actual_custom_cookie == expected_custom_cookie
