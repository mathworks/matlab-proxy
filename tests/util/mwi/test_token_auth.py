# Copyright (c) 2023 The MathWorks, Inc.

import pytest
from aiohttp import web
from aiohttp_session import setup as aiohttp_session_setup
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from cryptography import fernet

from matlab_proxy.util.mwi import environment_variables as mwi_env
from matlab_proxy.util.mwi import token_auth

## APIs to test:
# 1. generate_mwi_auth_token (auth enabled, auth enabled+custom token, custom token, auth disabled)
# 2. authenticate_access_decorator (headers & url_string, and session storage)

## Testing generate_mwi_auth_token :


def test_generate_mwi_auth_token(monkeypatch):
    # Test if token is auto-generated when MWI_ENABLE_AUTH_TOKEN is True
    expected_auth_enablement = "True"
    monkeypatch.setenv(
        mwi_env.get_env_name_enable_mwi_auth_token(), str(expected_auth_enablement)
    )

    generated_token = token_auth.generate_mwi_auth_token_and_hash()["token"]
    assert generated_token is not None

    # Test if token is generated when MWI_ENABLE_AUTH_TOKEN is True & has custom token set
    expected_auth_token = "CustomTokenStr123_-Test1"
    expected_auth_enablement = "True"
    monkeypatch.setenv(
        mwi_env.get_env_name_enable_mwi_auth_token(), str(expected_auth_enablement)
    )
    monkeypatch.setenv(mwi_env.get_env_name_mwi_auth_token(), str(expected_auth_token))

    generated_token = token_auth.generate_mwi_auth_token_and_hash()["token"]
    assert generated_token == expected_auth_token

    # Test if token is generated when MWI_ENABLE_AUTH_TOKEN is unset & has custom token set
    expected_auth_token = "CustomTokenStr123_-Test2"
    monkeypatch.delenv(mwi_env.get_env_name_enable_mwi_auth_token())
    monkeypatch.setenv(mwi_env.get_env_name_mwi_auth_token(), str(expected_auth_token))

    generated_token = token_auth.generate_mwi_auth_token_and_hash()["token"]
    assert generated_token == expected_auth_token

    # Test if token is not generated when MWI_ENABLE_AUTH_TOKEN is explicitly disabled & has custom token set
    expected_auth_token = "CustomTokenStr123_-Test3"
    expected_auth_enablement = "False"
    monkeypatch.setenv(
        mwi_env.get_env_name_enable_mwi_auth_token(), str(expected_auth_enablement)
    )
    monkeypatch.setenv(mwi_env.get_env_name_mwi_auth_token(), str(expected_auth_token))

    generated_token = token_auth.generate_mwi_auth_token_and_hash()["token"]
    assert generated_token is None


## Testing authenticate_access_decorator :
# This in turn, also tests authenticate_request


@pytest.fixture
def get_custom_auth_token_str():
    return "CustomTokenStr123_-TestOtherAPIS"


@token_auth.authenticate_access_decorator
async def fake_endpoint(request):
    if request.method == "POST":
        request.app["value"] = (await request.post())["value"]
        return web.Response(body=b"thanks for the data")
    return web.Response(body="value: {}".format(request.app["value"]).encode("utf-8"))


@pytest.fixture
def fake_server_with_auth_enabled(
    loop, aiohttp_client, monkeypatch, get_custom_auth_token_str
):
    auth_token = get_custom_auth_token_str
    auth_enablement = "True"
    monkeypatch.setenv(
        mwi_env.get_env_name_enable_mwi_auth_token(), str(auth_enablement)
    )
    monkeypatch.setenv(mwi_env.get_env_name_mwi_auth_token(), str(auth_token))

    (
        mwi_auth_token,
        mwi_auth_token_hash,
    ) = token_auth.generate_mwi_auth_token_and_hash().values()

    app = web.Application()
    app["settings"] = {
        "mwi_is_token_auth_enabled": mwi_auth_token != None,
        "mwi_auth_token": mwi_auth_token,
        "mwi_auth_token_hash": mwi_auth_token_hash,
        "mwi_auth_token_name": mwi_env.get_env_name_mwi_auth_token().lower(),
    }
    app.router.add_get("/", fake_endpoint)
    app.router.add_post("/", fake_endpoint)
    # Setup the session storage
    fernet_key = fernet.Fernet.generate_key()
    f = fernet.Fernet(fernet_key)
    aiohttp_session_setup(
        app, EncryptedCookieStorage(f, cookie_name="matlab-proxy-session")
    )
    return loop.run_until_complete(aiohttp_client(app))


async def test_set_value_with_token(
    fake_server_with_auth_enabled, get_custom_auth_token_str
):
    resp = await fake_server_with_auth_enabled.post(
        "/",
        data={"value": "foo"},
        headers={"mwi_auth_token": get_custom_auth_token_str},
    )
    assert resp.status == web.HTTPOk.status_code
    assert await resp.text() == "thanks for the data"
    assert fake_server_with_auth_enabled.server.app["value"] == "foo"

    # Test subsequent requests do not need token authentication
    resp2 = await fake_server_with_auth_enabled.post(
        "/",
        data={"value": "foobar"},
    )
    assert resp2.status == web.HTTPOk.status_code
    assert fake_server_with_auth_enabled.server.app["value"] == "foobar"

    # Test request which accepts cookies from previous request
    resp3 = await fake_server_with_auth_enabled.post(
        "/",
        data={"value": "foobar1"},
        cookies=resp.cookies,
    )
    assert resp3.status == web.HTTPOk.status_code
    assert fake_server_with_auth_enabled.server.app["value"] == "foobar1"


async def test_set_value_with_token_hash(
    fake_server_with_auth_enabled, get_custom_auth_token_str
):
    resp = await fake_server_with_auth_enabled.post(
        "/",
        data={"value": "foo"},
        headers={
            "mwi_auth_token": token_auth._generate_hash(get_custom_auth_token_str)
        },
    )
    assert resp.status == web.HTTPOk.status_code
    assert await resp.text() == "thanks for the data"
    assert fake_server_with_auth_enabled.server.app["value"] == "foo"

    # Test subsequent requests do not need token authentication
    resp2 = await fake_server_with_auth_enabled.post(
        "/",
        data={"value": "foobar"},
    )
    assert resp2.status == web.HTTPOk.status_code
    assert fake_server_with_auth_enabled.server.app["value"] == "foobar"

    # Test request which accepts cookies from previous request
    resp3 = await fake_server_with_auth_enabled.post(
        "/",
        data={"value": "foobar1"},
        cookies=resp.cookies,
    )
    assert resp3.status == web.HTTPOk.status_code
    assert fake_server_with_auth_enabled.server.app["value"] == "foobar1"


async def test_set_value_without_token(fake_server_with_auth_enabled):
    resp2 = await fake_server_with_auth_enabled.post(
        "/",
        data={"value": "foobar"},
    )
    assert resp2.status == web.HTTPForbidden.status_code


async def test_set_value_with_invalid_token(fake_server_with_auth_enabled):
    resp2 = await fake_server_with_auth_enabled.post(
        "/", data={"value": "foobar"}, headers={"mwi_auth_token": "invalid-token"}
    )
    assert resp2.status == web.HTTPForbidden.status_code


async def test_set_value_with_token_in_params(
    fake_server_with_auth_enabled, get_custom_auth_token_str
):
    fake_server_with_auth_enabled.server.app["value"] = "foo"
    resp = await fake_server_with_auth_enabled.post(
        "/",
        data={"value": "foofoo"},
        params={"mwi_auth_token": token_auth._generate_hash(get_custom_auth_token_str)},
    )
    assert resp.status == web.HTTPOk.status_code
    assert await resp.text() == "thanks for the data"
    assert fake_server_with_auth_enabled.server.app["value"] == "foofoo"

    # Test subsequent requests do not need token authentication
    resp2 = await fake_server_with_auth_enabled.post(
        "/",
        data={"value": "foobar"},
    )
    assert resp2.status == web.HTTPForbidden.status_code
    # assert server_with_auth_enabled.server.app["value"] == "foobar"


async def test_get_value_without_token(fake_server_with_auth_enabled):
    fake_server_with_auth_enabled.server.app["value"] = "bar"
    resp = await fake_server_with_auth_enabled.get("/")
    assert resp.status == web.HTTPForbidden.status_code


async def test_get_value_with_token_in_query_params(
    fake_server_with_auth_enabled, get_custom_auth_token_str
):
    fake_server_with_auth_enabled.server.app["value"] = "bar"
    resp = await fake_server_with_auth_enabled.get(
        "/",
        params={"mwi_auth_token": token_auth._generate_hash(get_custom_auth_token_str)},
    )
    assert resp.status == web.HTTPOk.status_code
    assert await resp.text() == "value: bar"


## Create a fake_server without authentication enabled, and test that you can access data.


@pytest.fixture
def fake_server_without_auth_enabled(loop, aiohttp_client, monkeypatch):
    auth_enablement = "False"
    monkeypatch.setenv(
        mwi_env.get_env_name_enable_mwi_auth_token(), str(auth_enablement)
    )
    (
        mwi_auth_token,
        mwi_auth_token_hash,
    ) = token_auth.generate_mwi_auth_token_and_hash().values()

    app = web.Application()
    app["settings"] = {
        "mwi_is_token_auth_enabled": mwi_auth_token != None,
        "mwi_auth_token": mwi_auth_token,
        "mwi_auth_token_hash": mwi_auth_token_hash,
        "mwi_auth_token_name": mwi_env.get_env_name_mwi_auth_token().lower(),
    }
    app.router.add_get("/", fake_endpoint)
    app.router.add_post("/", fake_endpoint)
    # Setup the session storage
    fernet_key = fernet.Fernet.generate_key()
    f = fernet.Fernet(fernet_key)
    aiohttp_session_setup(
        app, EncryptedCookieStorage(f, cookie_name="matlab-proxy-session")
    )
    return loop.run_until_complete(aiohttp_client(app))


async def test_get_value(fake_server_without_auth_enabled):
    fake_server_without_auth_enabled.server.app["value"] = "bar1"
    resp = await fake_server_without_auth_enabled.get("/")
    assert resp.status == web.HTTPOk.status_code
    assert await resp.text() == "value: bar1"


async def test_get_value_in_query_params(
    fake_server_without_auth_enabled, get_custom_auth_token_str
):
    # Server should respond even if token is provided when not needed.
    fake_server_without_auth_enabled.server.app["value"] = "bar2"
    resp = await fake_server_without_auth_enabled.get(
        "/", params={"mwi_auth_token": get_custom_auth_token_str}
    )
    assert resp.status == web.HTTPOk.status_code
    assert await resp.text() == "value: bar2"
