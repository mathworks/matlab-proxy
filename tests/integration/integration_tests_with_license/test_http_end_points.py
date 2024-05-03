# Copyright 2023-2024 The MathWorks, Inc.

import json
import os
import time
import matlab_proxy.settings as settings
from tests.integration.utils import integration_tests_utils as utils
import pytest
from matlab_proxy.util import system
import requests
import re
from requests.adapters import HTTPAdapter, Retry
from urllib.parse import urlparse, parse_qs
from tests.utils.logging_util import create_integ_test_logger
from matlab_proxy.constants import MWI_AUTH_TOKEN_NAME_FOR_HTTP

_logger = create_integ_test_logger(__name__)

# Timeout for polling the matlab-proxy http endpoints
# matlab proxy in Mac machines takes more time to be 'up'

MAX_TIMEOUT = settings.get_process_startup_timeout()


class RealMATLABServer:
    """
    Context Manager class which returns matlab proxy web server serving real MATLAB
    for testing.

    Setting up the server in the context of Pytest.
    """

    def __init__(self, event_loop):
        self.event_loop = event_loop

    def __enter__(self):
        # Store the matlab proxy logs in os.pipe for testing
        # os.pipe2 is only supported in Linux systems
        _logger.info("Setting up MATLAB Server for integration test")

        _logger.debug("Entering RealMATLABServer enter section.")
        self.dpipe = os.pipe2(os.O_NONBLOCK) if system.is_linux() else os.pipe()
        self.mwi_app_port = utils.get_random_free_port()
        self.matlab_config_file_path = str(utils.get_matlab_config_file())

        self.temp_dir_path = os.path.dirname(
            os.path.dirname(self.matlab_config_file_path)
        )

        self.temp_dir_name = "temp_dir"
        self.mwi_base_url = "/matlab-test"

        # Environment variables to launch matlab proxy
        input_env = {
            "MWI_APP_PORT": self.mwi_app_port,
            "MWI_BASE_URL": self.mwi_base_url,
        }

        self.proc = self.event_loop.run_until_complete(
            utils.start_matlab_proxy_app(out=self.dpipe[1], input_env=input_env)
        )

        utils.wait_server_info_ready(self.mwi_app_port)
        parsed_url = urlparse(utils.get_connection_string(self.mwi_app_port))

        self.headers = {
            MWI_AUTH_TOKEN_NAME_FOR_HTTP: (
                parse_qs(parsed_url.query)[MWI_AUTH_TOKEN_NAME_FOR_HTTP][0]
                if MWI_AUTH_TOKEN_NAME_FOR_HTTP in parse_qs(parsed_url.query)
                else ""
            )
        }
        self.connection_scheme = parsed_url.scheme
        self.url = parsed_url.scheme + "://" + parsed_url.netloc + parsed_url.path
        return self

    async def _terminate_process(self, timeout=0):
        """
        Asynchronous helper method to terminate the process with a timeout.

        Args:
            timeout: Maximum number of seconds to wait
                    for the process to terminate

        """
        import asyncio

        process = self.proc
        try:
            process.terminate()
            await asyncio.wait_for(process.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            _logger.warning(
                "Termination of the MATLAB Server process timed out. Attempting to kill."
            )
            process.kill()
            await process.wait()
            _logger.debug("Killed the MATLAB process after timeout.")

    def __exit__(self, exc_type, exc_value, exc_traceback):
        _logger.info("Tearing down the MATLAB Server.")
        self.event_loop.run_until_complete(self._terminate_process(timeout=10))
        _logger.debug("Terminated the MATLAB process.")


def _send_http_get_request(uri, connection_scheme, headers, http_endpoint=""):
    """Send HTTP request to matlab-proxy server.
    Returns HTTP response JSON"""

    request_uri = uri + http_endpoint

    json_response = None
    with requests.Session() as s:
        retries = Retry(total=10, backoff_factor=0.1)
        s.mount(f"{connection_scheme}://", HTTPAdapter(max_retries=retries))
        response = s.get(request_uri, headers=headers, verify=False)
        json_response = json.loads(response.text)

    return json_response


def _check_matlab_status(matlab_proxy_app_fixture, status):
    uri = matlab_proxy_app_fixture.url
    connection_scheme = matlab_proxy_app_fixture.connection_scheme
    headers = matlab_proxy_app_fixture.headers

    matlab_status = None

    start_time = time.time()
    while matlab_status != status and (time.time() - start_time < MAX_TIMEOUT):
        time.sleep(1)
        res = _send_http_get_request(
            uri, connection_scheme, headers, http_endpoint="/get_status"
        )
        matlab_status = res["matlab"]["status"]

    return matlab_status


@pytest.fixture
def matlab_proxy_app_fixture(
    loop,
):
    """A pytest fixture which yields a real matlab server to be used by tests.

    Args:
        loop (Event event_loop): The built-in event event_loop provided by pytest.

    Yields:
        real_matlab_server : A real matlab web server used by tests.
    """

    try:
        with RealMATLABServer(loop) as matlab_proxy_app:
            yield matlab_proxy_app
    except ProcessLookupError as e:
        _logger.debug("ProcessLookupError found in matlab proxy app fixture")
        _logger.debug(e)
        pass


def test_matlab_is_up(matlab_proxy_app_fixture):
    """Test that the status switches from 'starting' to 'up' within a timeout.

    Args:
        matlab_proxy_app_fixture: A pytest fixture which yields a real matlab server to be used by tests.
    """

    status = _check_matlab_status(matlab_proxy_app_fixture, "up")
    assert status == "up"


def test_stop_matlab(matlab_proxy_app_fixture):
    """Test to check that matlab is in 'down' state when
    we send the delete request to 'stop_matlab' endpoint

    Args:
        matlab_proxy_app_fixture: A pytest fixture which yields a real matlab server to be used by tests.
    """
    status = _check_matlab_status(matlab_proxy_app_fixture, "up")
    assert status == "up"

    http_endpoint_to_test = "/stop_matlab"
    stop_url = matlab_proxy_app_fixture.url + http_endpoint_to_test

    with requests.Session() as s:
        retries = Retry(total=10, backoff_factor=0.1)
        s.mount(
            f"{matlab_proxy_app_fixture.connection_scheme}://",
            HTTPAdapter(max_retries=retries),
        )
        s.delete(stop_url, headers=matlab_proxy_app_fixture.headers, verify=False)

    status = _check_matlab_status(matlab_proxy_app_fixture, "down")
    assert status == "down"


# FIXME: If output has logging or extra debug info, 600 bytes might not be enough.
async def test_print_message(matlab_proxy_app_fixture):
    """Test if the right logs are printed

    Args:
        matlab_proxy_app_fixture: A pytest fixture which yields a real matlab server to be used by tests.

    """
    # Checks if matlab proxy is in "up" state or not
    status = _check_matlab_status(matlab_proxy_app_fixture, "up")
    assert status == "up"

    uri_regex = f"{matlab_proxy_app_fixture.connection_scheme}://[a-zA-Z0-9\-_.]+:{matlab_proxy_app_fixture.mwi_app_port}{matlab_proxy_app_fixture.mwi_base_url}"

    read_descriptor, write_descriptor = matlab_proxy_app_fixture.dpipe
    number_of_bytes = 600

    if read_descriptor:
        line = os.read(read_descriptor, number_of_bytes).decode("utf-8")
        process_logs = line.strip()

    assert bool(re.search(uri_regex, process_logs)) == True

    # Close the read and write descriptors.
    os.close(read_descriptor)
    os.close(write_descriptor)
