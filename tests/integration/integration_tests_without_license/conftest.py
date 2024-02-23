# Copyright 2023-2024 The MathWorks, Inc.

import pytest
from integration import integration_tests_utils as utils
import requests


@pytest.fixture(scope="module", name="module_monkeypatch")
def monkeypatch_module_scope_fixture():
    """
    Pytest fixture for creating a monkeypatch object in 'module' scope.
    The default monkeypatch fixture returns monkeypatch object in
    'function' scope but a 'module' scope object is needed with matlab-proxy
    'module' scope fixture.

    Yields:
        class object: Object of class MonkeyPatch
    """
    with pytest.MonkeyPatch.context() as mp:
        yield mp


@pytest.fixture(scope="module", autouse=True)
def start_matlab_proxy_fixture(module_monkeypatch):
    """Starts the matlab proxy process"""
    utils.perform_basic_checks()

    # Start matlab-proxy-app for testing

    mwi_app_port = utils.get_random_free_port()
    mwi_base_url = "/matlab-test"

    input_env = {
        "MWI_APP_PORT": mwi_app_port,
        "MWI_BASE_URL": mwi_base_url,
        "MWI_ENABLE_TOKEN_AUTH": "false",
    }

    import matlab_proxy

    loop = matlab_proxy.util.get_event_loop()

    # Run matlab-proxy in the background in an event loop
    proc = loop.run_until_complete(utils.start_matlab_proxy_app(input_env=input_env))

    # Wait for mwi_server.info file to be ready
    utils.wait_server_info_ready(mwi_app_port)

    # Get the scheme on which MATLAB Proxy connection string
    matlab_proxy_url = utils.get_connection_string(mwi_app_port)

    utils.poll_web_service(
        matlab_proxy_url,
        step=5,
        timeout=120,
        ignore_exceptions=(
            requests.exceptions.ConnectionError,
            requests.exceptions.SSLError,
        ),
    )

    for key, value in input_env.items():
        module_monkeypatch.setenv(key, value)

    yield

    proc.terminate()
    loop.run_until_complete(proc.wait())
