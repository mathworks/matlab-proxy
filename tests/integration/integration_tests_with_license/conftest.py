# Copyright 2023 The MathWorks, Inc.

import os
import sys
from integration import integration_tests_utils as utils
import pytest
import requests
import shutil
from matlab_proxy.util import system
from matlab_proxy.util.mwi import environment_variables as mwi_env


@pytest.fixture(scope="module", name="module_monkeypatch")
def monkeypatch_module_scope_fixture():
    """
    To ensure that modifications made with the monkeypatch fixture
    persist across all tests in the module, this fixture
    has been created in 'module' scope. This is done because a 'module'
    scope object is needed with matlab-proxy 'module' scope fixture.
    This allows us to patch certain aspects, like environment variables,
    for all tests within the module.

    Yields:
        class object: Object of class MonkeyPatch
    """
    with pytest.MonkeyPatch.context() as mp:
        yield mp


@pytest.fixture(scope="module", autouse=True)
def matlab_config_cleanup_fixture(request):
    """
    Cleanup the directory that contains matlab config file
    before and after running the tests. This is done to make sure that
    matlab-proxy is unlicensed.
    """

    def delete_matlab_test_dir():
        # Delete matlab_config_file & its owning directory
        matlab_config_file = utils.get_matlab_config_file()
        matlab_config_dir = os.path.dirname(matlab_config_file)
        try:
            shutil.rmtree(matlab_config_dir)
        except FileNotFoundError:
            pass

        temp_dir_path = os.path.join(os.path.dirname(matlab_config_dir), "temp_dir")

        try:
            shutil.rmtree(temp_dir_path)
        except FileNotFoundError:
            pass

    # Runs in the beginning to make sure that matlab-proxy is
    # not already licensed
    delete_matlab_test_dir()

    # Runs in the end to cleanup licensing cache
    request.addfinalizer(delete_matlab_test_dir)


@pytest.fixture(autouse=True, scope="module")
def matlab_proxy_fixture(module_monkeypatch, request):
    """
    Pytest fixture for managing a standalone matlab-proxy process
    for testing purposes. This fixture sets up a matlab-proxy process in
    the module scope, and tears it down after all the tests are executed.
    """
    import matlab_proxy.util

    utils.perform_basic_checks()

    # Select a random free port to serve matlab-proxy for testing
    mwi_app_port = utils.get_random_free_port()
    mwi_base_url = "/matlab-test"
    module_monkeypatch.setenv(mwi_env.get_env_name_testing(), "false")
    module_monkeypatch.setenv(mwi_env.get_env_name_development(), "false")

    # '127.0.0.1' is used instead 'localhost' for testing since Windows machines consume
    # some time to resolve 'localhost' hostname
    matlab_proxy_url = f"http://127.0.0.1:{mwi_app_port}{mwi_base_url}"

    # Start matlab-proxy-app for testing
    input_env = {
        "MWI_APP_PORT": mwi_app_port,
        "MWI_BASE_URL": mwi_base_url,
    }

    # Get event loop to start matlab-proxy in background
    loop = matlab_proxy.util.get_event_loop()

    # Run matlab-proxy in the background in an event loop
    proc = loop.run_until_complete(utils.start_matlab_proxy_app(input_env=input_env))

    # Poll for matlab-proxy URL to respond
    utils.poll_web_service(
        matlab_proxy_url,
        step=5,
        timeout=120,
        ignore_exceptions=(
            requests.exceptions.ConnectionError,
            requests.exceptions.SSLError,
        ),
    )
    # License matlab-proxy using playwright UI automation
    utils.license_matlab_proxy(matlab_proxy_url)

    # Wait for matlab-proxy to be up and running
    utils.wait_matlab_proxy_ready(matlab_proxy_url)

    # Get the location of ".matlab"
    matlab_config_file = str(
        utils.get_matlab_config_file()
    )  # ~/.matlab/MWI/proxy_app_config.json

    dotmatlab_dir_path = os.path.dirname(os.path.dirname(matlab_config_file))

    # Create a temporary location in .matlab directory
    temp_dir_path = os.path.join(dotmatlab_dir_path, "temp_dir")
    os.mkdir(temp_dir_path)  # delete this folder after the test execution
    shutil.move(matlab_config_file, temp_dir_path)

    proc.terminate()
    loop.run_until_complete(proc.wait())

    # Run the matlab proxy tests
    yield
