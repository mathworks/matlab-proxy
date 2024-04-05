# Copyright 2023-2024 The MathWorks, Inc.

import os
from tests.integration.utils import integration_tests_utils as utils
import pytest
from matlab_proxy.util.mwi import environment_variables as mwi_env
from tests.utils.logging_util import create_integ_test_logger


_logger = create_integ_test_logger(
    __name__, log_file_path=os.getenv("MWI_INTEG_TESTS_LOG_FILE_PATH")
)


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


@pytest.fixture(autouse=True, scope="module")
def matlab_proxy_fixture(module_monkeypatch, request):
    """
    Pytest fixture for managing a standalone matlab-proxy process
    for testing purposes. This fixture sets up a matlab-proxy process in
    the module scope, and tears it down after all the tests are executed.
    """

    utils.perform_basic_checks()

    module_monkeypatch.setenv(mwi_env.get_env_name_testing(), "false")
    module_monkeypatch.setenv(mwi_env.get_env_name_development(), "false")
    _logger.info("Started MATLAB Proxy process")

    # Run the matlab proxy tests
    yield
