# Copyright 2023-2025 The MathWorks, Inc.

"""
Contains integration tests which exercise HTTP endpoints of interest exposed by matlab-proxy-app
"""

# Imports
from enum import Enum
import json
import os
import pytest
import re
import requests
import time
from requests.adapters import HTTPAdapter, Retry
from urllib.parse import urlparse, parse_qs

# Local module imports
import matlab_proxy.settings as settings
from matlab_proxy.constants import MWI_AUTH_TOKEN_NAME_FOR_HTTP
from matlab_proxy.util import system
from tests.integration.utils import integration_tests_utils as utils
from tests.utils.logging_util import create_integ_test_logger

# Logger Setup
_logger = create_integ_test_logger(__name__)

# Constants

# Timeout for polling the matlab-proxy http endpoints
# matlab proxy in Mac machines takes more time to be 'up'
MAX_TIMEOUT = settings.get_process_startup_timeout()


class Format(Enum):
    """
    An enumeration to specify different format types.

    Attributes:
        JSON (int): Represents the JSON format type.
        TEXT (int): Represents the plain text format type.
    """

    JSON = 1
    TEXT = 2


# Utility Functions
def _http_get_request(
    uri, connection_scheme, headers, http_endpoint="", outputFormat=Format.TEXT
):
    """
    Sends an HTTP GET request to a specified URI, optionally appending an endpoint to the URI.

    This function uses a session with retries configured for transient network errors. It can return
    the response in either text or JSON format, based on the outputFormat parameter.

    Parameters:
    - uri (str): The base URI for the HTTP request.
    - connection_scheme (str): The scheme to use for the connection (e.g., 'http' or 'https').
    - headers (dict): A dictionary of HTTP headers to include in the request.
    - http_endpoint (str, optional): An additional endpoint to append to the base URI. Defaults to an empty string.
    - outputFormat (format, optional): The desired format for the response content. This should be an attribute
      of a format enumeration, supporting at least 'TEXT' and 'JSON' options. Defaults to Format.TEXT.

    Returns:
    - str or dict: The response content as a string if outputFormat is Format.TEXT, or as a dictionary
      if outputFormat is Format.JSON.

    Raises:
    - Exception: If an invalid output format is specified.

    Note:
    - The function disables SSL certificate verification (`verify=False`). This may introduce security risks,
      such as vulnerability to man-in-the-middle attacks. Use with caution in a production environment.
    """
    request_uri = uri + http_endpoint
    with requests.Session() as s:
        retries = Retry(total=10, backoff_factor=0.1)
        s.mount(f"{connection_scheme}://", HTTPAdapter(max_retries=retries))
        response = s.get(request_uri, headers=headers, verify=False)

        if outputFormat == Format.TEXT:
            return response.text
        elif outputFormat == Format.JSON:
            return json.loads(response.text)

    raise Exception("Invalid output format specified.")


def _check_matlab_status(matlab_proxy_app_fixture, status):
    """
    Check the status of a MATLAB session until a specified status is reached or a timeout occurs.

    This function repeatedly sends HTTP GET requests to a MATLAB proxy application to check the current
    status of MATLAB. It continues checking until MATLAB's status matches the specified target status or
    until a maximum timeout is reached.

    Parameters:
    - matlab_proxy_app_fixture: An object containing configuration for connecting to the MATLAB proxy application.
      This object must have the following attributes:
        - url (str): The base URL of the MATLAB proxy application.
        - connection_scheme (str): The scheme used for the connection (e.g., 'http' or 'https').
        - headers (dict): A dictionary of HTTP headers to be sent with each request.
    - status (str): The target status to wait for MATLAB to reach.

    Returns:
    - str: The status of MATLAB at the end of the function execution. This could be the target status if
      it was reached within the timeout period, or the last known status of MATLAB if the timeout was reached
      first.

    Notes:
    - The function waits for a maximum of MAX_TIMEOUT seconds, defined elsewhere, before exiting.
    - It checks the MATLAB status every 1 second.
    - The MATLAB status is obtained by sending a GET request to the '/get_status' endpoint of the proxy application.
    - The response from the proxy application is expected to be in JSON format, with MATLAB's status accessible
      via `res["matlab"]["status"]`.

    Exceptions:
    - This function may raise exceptions related to network issues or JSON parsing errors, which are not
      explicitly handled within the function.
    """
    uri = matlab_proxy_app_fixture.url
    connection_scheme = matlab_proxy_app_fixture.connection_scheme
    headers = matlab_proxy_app_fixture.headers

    matlab_status = None

    start_time = time.time()
    while matlab_status != status and (time.time() - start_time < MAX_TIMEOUT):
        time.sleep(1)
        res = _http_get_request(
            uri,
            connection_scheme,
            headers,
            http_endpoint="/get_status",
            outputFormat=Format.JSON,
        )
        matlab_status = res["matlab"]["status"]

    return matlab_status


def _download_test_file(matlab_proxy_app_fixture, test_file):
    """Returns result of hitting the /download endpoint for test_file.

    Returns:
        str: The contents of the test_file being downloaded through matlab-proxy.
    """
    uri = matlab_proxy_app_fixture.url
    connection_scheme = matlab_proxy_app_fixture.connection_scheme
    headers = matlab_proxy_app_fixture.headers

    res = _http_get_request(
        uri,
        connection_scheme,
        headers,
        http_endpoint="/download/" + test_file,
        outputFormat=Format.TEXT,
    )
    return res


# Main Classes
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


# Fixtures
@pytest.fixture
def matlab_proxy_app_fixture(
    event_loop,
):
    """A pytest fixture which yields a real matlab server to be used by tests.

    Args:
        event_loop (Event loop): The built-in event loop provided by pytest.

    Yields:
        real_matlab_server : A real matlab web server used by tests.
    """

    try:
        with RealMATLABServer(event_loop) as matlab_proxy_app:
            yield matlab_proxy_app
    except ProcessLookupError as e:
        _logger.debug("ProcessLookupError found in matlab proxy app fixture")
        _logger.debug(e)


@pytest.fixture
def test_file_contents():
    """
    A pytest fixture that provides a string for testing purposes.

    This fixture returns a predefined string that can be used in tests to simulate
    the contents of a file or any scenario where a constant string value is needed.

    Returns:
        str: A string containing the text "I LOVE MATLAB."
    """
    return "I LOVE MATLAB."


@pytest.fixture
def test_file(tmp_path, test_file_contents):
    """
    A pytest fixture that creates a temporary test file with given contents.

    This fixture utilizes pytest's `tmp_path` fixture to generate a temporary directory,
    then creates a file named "temporary_test_file.txt" within this directory,
    and writes the provided contents to this file. It is useful for tests that require
    reading from or writing to files without affecting the actual file system.

    Parameters:
    - tmp_path (Path): A pytest fixture that provides a temporary directory unique to the test function.
    - test_file_contents (str): The content to be written into the temporary test file.

    Returns:
    - str: The path to the created temporary test file as a string.
    """
    test_file = os.path.join(tmp_path, "temporary_test_file.txt")
    with open(test_file, "w+") as f:
        f.write(test_file_contents)
    return test_file


# Test Functions
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


async def test_print_message(matlab_proxy_app_fixture):
    """Test if the right logs are printed

    Args:
        matlab_proxy_app_fixture: A pytest fixture which yields a real matlab server to be used by tests.

    FIXME: If output has logging or extra debug info, 600 bytes might not be enough.
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


def test_download_file_from_matlab(
    matlab_proxy_app_fixture, test_file, test_file_contents
):
    """
    Test the downloading of a file from a MATLAB proxy application.

    This test function checks if the MATLAB proxy application is up and running, and then attempts to download
    a specific test file from it. It validates both the status of the MATLAB proxy and the contents of the downloaded file.

    Parameters:
    - matlab_proxy_app_fixture (fixture): A test fixture representing the MATLAB proxy application environment.
    - test_file (str): The name or path of the test file to be downloaded from the MATLAB proxy application.
    - test_file_contents (str): The expected contents of the test file to validate the download operation.

    Assertions:
    - Asserts that the MATLAB proxy application is "up".
    - Asserts that the content of the downloaded file matches the expected `test_file_contents`.

    Raises:
    - AssertionError: If any of the assertions fail, indicating either the MATLAB proxy application is not running
      as expected or there is a mismatch in the file content.
    """
    status = _check_matlab_status(matlab_proxy_app_fixture, "up")
    assert status == "up"

    # Once MATLAB is up, we can then attempt to download
    result = _download_test_file(matlab_proxy_app_fixture, test_file)
    assert result == test_file_contents
