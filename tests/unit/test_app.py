# Copyright (c) 2020-2023 The MathWorks, Inc.

import asyncio
import json
import time
import datetime

import aiohttp
import pytest
import random
from http import HTTPStatus
from matlab_proxy import app, util
from matlab_proxy.util.mwi import environment_variables as mwi_env
from matlab_proxy.util.mwi.exceptions import MatlabInstallError
from datetime import timedelta, timezone
from matlab_proxy.util.mwi.exceptions import EntitlementError
import test_constants
import matlab_proxy


def test_create_app():
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

    The server setup and startup does not need to mimick the way it is being done in main() method in app.py.
    Setting up the server in the context of Pytest.
    """

    def __init__(self, loop, aiohttp_client):
        self.loop = loop
        self.aiohttp_client = aiohttp_client

    def __enter__(self):
        server = app.create_app()
        self.server = app.configure_and_start(server)
        return self.loop.run_until_complete(self.aiohttp_client(self.server))

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.loop.run_until_complete(self.server.shutdown())
        self.loop.run_until_complete(self.server.cleanup())


@pytest.fixture(name="test_server")
def test_server_fixture(
    loop,
    aiohttp_client,
):
    """A pytest fixture which yields a test server to be used by tests.

    Args:
        loop (Event loop): The built-in event loop provided by pytest.
        aiohttp_client (aiohttp_client): Built-in pytest fixture used as a wrapper to the aiohttp web server.

    Yields:
        aiohttp_client : A aiohttp_client server used by tests.
    """
    try:
        with FakeServer(loop, aiohttp_client) as test_server:
            yield test_server
    except ProcessLookupError:
        pass


async def test_get_status_route(test_server):
    """Test to check endpoint : "/get_status"

    Args:
        test_server (aiohttp_client): A aiohttp_client server for sending GET request.
    """

    resp = await test_server.get("/get_status")
    assert resp.status == HTTPStatus.OK


async def test_get_env_config(test_server):
    """Test to check endpoint : "/get_env_config"

    Args:
        test_server (aiohttp_client): A aiohttp_client server for sending GET request.
    """

    resp = await test_server.get("/get_env_config")
    assert resp.status == HTTPStatus.OK

    text = await resp.text()
    assert text is not None


async def test_start_matlab_route(test_server):
    """Test to check endpoint : "/start_matlab"

    Test waits for matlab status to be "up" before sending the GET request to start matlab
    Checks whether matlab restarts.

    Args:
        test_server (aiohttp_client): A aiohttp_client server to send GET request to.
    """
    # Waiting for the matlab process to start up.
    sleep_interval = 1
    await wait_for_matlab_to_be_up(test_server, sleep_interval)

    # Send get request to end point
    await test_server.put("/start_matlab")

    # Check if Matlab restarted successfully
    await check_for_matlab_startup(test_server)


async def check_for_matlab_startup(test_server):
    count = 0
    while True:
        resp = await test_server.get("/get_status")
        assert resp.status == HTTPStatus.OK
        resp_json = json.loads(await resp.text())
        if resp_json["matlab"]["status"] != "down":
            break
        else:
            count += 1
            await asyncio.sleep(0.5)
            if count > test_constants.FIVE_MAX_TRIES:
                raise ConnectionError


async def test_stop_matlab_route(test_server):
    """Test to check endpoint : "/stop_matlab"

    Sends HTTP DELETE request to stop matlab and checks if matlab status is down.
    Args:
        test_server (aiohttp_client): A aiohttp_client server to send HTTP DELETE request.
    """
    resp = await test_server.delete("/stop_matlab")
    assert resp.status == HTTPStatus.OK

    resp_json = json.loads(await resp.text())
    assert resp_json["matlab"]["status"] == "down"


async def test_root_redirect(test_server):
    """Test to check endpoint : "/"

    Should throw a 404 error. This will look for index.html in root directory of the project
    (In non-dev mode, root directory is the package)
    This file will not be available in the expected location in dev mode.

    Args:
        test_server (aiohttp_client):  A aiohttp_client server to send HTTP GET request.

    """
    resp = await test_server.get("/")
    assert resp.status == 404


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
    resp = await test_server.post(
        "./1234.html", data=json.dumps(proxy_payload), headers=headers
    )
    assert resp.status == 404


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

        if resp.status == 404:
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

        if resp.status == 404:
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

        if resp.status == 404:
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

        if resp.status == 404:
            time.sleep(1)
            count += 1

        else:
            resp_json = await resp.json()
            assert set(resp_json.keys()).issubset(proxy_payload.keys())
            break

        if count > max_tries:
            raise ConnectionError


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


@pytest.mark.parametrize(
    "headers",
    [
        {
            "connection": "Upgrade",
            "Upgrade": "websocket",
        },
        {
            "connection": "upgrade",
            "upgrade": "websocket",
        },
    ],
    ids=["Uppercase header", "Lowercase header"],
)
async def test_matlab_proxy_web_socket(test_server, headers):
    """Test to check if test_server proxies web socket request to fake matlab server

    Args:
        test_server (aiohttp_client): Test Server to send HTTP Requests.
    """

    sleep_interval = 2
    await wait_for_matlab_to_be_up(test_server, sleep_interval)
    resp = await test_server.ws_connect("/http_ws_request.html/", headers=headers)
    text = await resp.receive()
    websocket_response_string = (
        "Hello world"  # This string is set by the web_socket_handler in devel.py
    )
    assert text.type == aiohttp.WSMsgType.TEXT
    assert text.data == websocket_response_string


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
    """Test to check endpoint : "/terminate_integration"

    Test which sends HTTP DELETE request to terminate integration. Checks if integration is terminated
    successfully.
    Args:
        test_server (aiohttp_client):  A aiohttp_client server to send HTTP GET request.
    """
    try:
        resp = await test_server.delete("/terminate_integration")
        resp_json = json.loads(await resp.text())
        assert resp.status == HTTPStatus.OK and resp_json["loadUrl"] == "../"
    except ProcessLookupError:
        pass


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
def test_get_access_url_non_dev(non_default_host_interface, non_test_env, test_server):
    """Test to check access url to not be 127.0.0.1 in non-dev mode"""
    assert "127.0.0.1" not in util.get_access_url(test_server.app)


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
    }
    # Pre-req: stop the matlab that got started during test server startup
    resp = await test_server.delete("/stop_matlab")
    assert resp.status == HTTPStatus.OK

    resp = await test_server.put("/set_licensing_info", data=json.dumps(data))
    assert resp.status == HTTPStatus.OK

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
    await check_for_matlab_startup(test_server)

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
    resp_json = json.loads(await resp.text())
    assert resp_json["matlab"]["status"] == "down"

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
