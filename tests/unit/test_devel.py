# Copyright (c) 2020-2023 The MathWorks, Inc.

import os
import socket
import subprocess
import sys
import time
from collections import namedtuple
from pathlib import Path

import pytest
import aiohttp
from matlab_proxy.util.mwi import environment_variables as mwi_env
from matlab_proxy.constants import CONNECTOR_SECUREPORT_FILENAME

"""
This file consists of tests which check the devel.py file
"""

TWO_MAX_TRIES = 2
FIVE_MAX_TRIES = 5
HALF_SECOND_DELAY = 0.5
ONE_SECOND_DELAY = 1


@pytest.fixture(name="matlab_log_dir")
def matlab_log_dir_fixture(monkeypatch, tmp_path):
    """A pytest fixture to monkeypatch an environment variable.

    This fixture monkeypatches MATLAB_LOG_DIR env variable which the
    fake matlab server utilizes to write the matlab_ready_file into.

    Args:
        monkeypatch : A built-in pytest fixture.
        tmp_path: tmp_path fixture provides a temporary directory unique to the test invocation.
    """
    matlab_log_dir = str(tmp_path)
    monkeypatch.setenv("MATLAB_LOG_DIR", matlab_log_dir)
    return matlab_log_dir


@pytest.fixture(name="matlab_ready_file")
def matlab_ready_file_fixture(matlab_log_dir, monkeypatch):
    """A pytest fixture to create the matlab_ready_file.

    This fixture creates the matlab readyfile path based on the matlab_log_dir fixture output.

    Args:
        matlab_log_dir: pytest fixture that returns a temp dir to be used as matlab_log_dir

    Returns:
        Path: Returns path of the matlab_ready_file
    """
    return Path(f"{matlab_log_dir}/{CONNECTOR_SECUREPORT_FILENAME}")


@pytest.fixture(name="valid_nlm")
def valid_nlm_fixture(monkeypatch):
    """A pytest fixture to monkeypatch an environment variable.

    This fixture monkeypatches MLM_LICENSE_FILE with a valid NLM connection string.

    Args:
        monkeypatch : A built-in pytest fixture
    """

    monkeypatch.setenv(mwi_env.get_env_name_network_license_manager(), "123@nlm")


@pytest.fixture(name="invalid_nlm")
def invalid_nlm_fixture(monkeypatch):
    """A pytest fixture to monkeypatch an environment variable.

    This fixture monkeypatches MLM_LICENSE_FILE with an invalid NLM connection string.


    Args:
        monkeypatch : A built-in pytest fixture
    """

    monkeypatch.setenv(mwi_env.get_env_name_network_license_manager(), "123@brokenhost")


@pytest.fixture(name="matlab_process_setup")
def matlab_process_setup_fixture():
    """A pytest fixture which creates a NamedTuple required for creating a fake matlab process

    This fixture returns a NamedTuple containing values required to run the fake matlab process

    Returns:
        variables : A NamedTuple containing the following values:

            devel_file = Path to devel_file
            matlab_cmd = The matlab command to start the matlab process
    """

    matlab_setup_variables = namedtuple(
        "matlab_setup_variables",
        ["devel_file", "matlab_cmd"],
    )
    devel_file = Path(os.path.join(os.getcwd(), "matlab_proxy", "devel.py"))

    python_executable = sys.executable

    matlab_cmd = [
        python_executable,
        "-u",
        str(devel_file),
        "matlab",
        "--ready-delay",
        "0",
    ]
    variables = matlab_setup_variables(devel_file, matlab_cmd)

    return variables


@pytest.fixture(name="matlab_process_valid_nlm")
def matlab_process_valid_nlm_fixture(matlab_log_dir, matlab_process_setup, valid_nlm):
    """A pytest fixture which creates a fake matlab process with a valid NLM connection string.

    This  pytest fixture creates a matlab process and yields control to the test which utilizes this
    fixture. After completion of tests stops the matlab process
    """

    matlab_process = subprocess.Popen(
        matlab_process_setup.matlab_cmd,
        stderr=subprocess.PIPE,
    )

    yield

    matlab_process.terminate()
    matlab_process.wait()


async def test_matlab_valid_nlm(matlab_ready_file, matlab_process_valid_nlm):
    """Test if the Fake Matlab server has started and is able to serve content.

    This test checks if the fake matlab process is able to start a web server and serve some
    fake content.

    Args:
        matlab_process_valid_nlm : A pytest fixture which creates the fake matlab process which starts the web server

    Raises:
        ConnectionError: If the fake matlab server doesn't startup, after the specified number of max_tries this test
        raises a ConnectionError.
    """

    matlab_port = get_matlab_port_from_ready_file(matlab_ready_file)
    if matlab_port is None:
        raise FileNotFoundError(f"matlab_ready_file at {matlab_ready_file} not found")

    count = 0
    while True:
        try:
            url = f"http://localhost:{matlab_port}/index-jsd-cr.html"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    assert resp.content_type == "text/html"
                    assert resp.status == 200
                    assert resp.content is not None
            break
        except:
            count += 1
            if count > FIVE_MAX_TRIES:
                raise ConnectionError
            time.sleep(ONE_SECOND_DELAY)


@pytest.fixture(name="matlab_process_invalid_nlm")
def matlab_process_invalid_nlm_fixture(
    matlab_log_dir, matlab_process_setup, invalid_nlm
):
    """A pytest fixture which creates a fake matlab server with an invalid NLM connection string.

    Utilizes matlab_log_dir, matlab_process_setup and invalid_nlm fixtures for creating a
    fake matlab web server then yields control for tests to utilize it.


    Args:
        matlab_log_dir : A pytest fixture which monkeypatches an environment variable.
        matlab_process_setup (NamedTuple): A NamedTuple which contains values to start the matlab process
        invalid_nlm : A pytest fixture which monkeypatches an invalid nlm connection string
    """

    matlab_process = subprocess.Popen(
        matlab_process_setup.matlab_cmd,
        stderr=subprocess.PIPE,
    )

    yield

    matlab_process.terminate()
    matlab_process.wait()


async def test_matlab_invalid_nlm(matlab_ready_file, matlab_process_invalid_nlm):
    """Test which checks if the fake Matlab process stops when NLM string is invalid

    When the NLM string is invalid, the fake matlab server will automatically
    exit. This test checks if a ConnectionError is raised when a GET request is sent to it.

    Args:
        matlab_process_invalid_nlm (Process): A process which starts a fake Matlab WebServer.
    """
    matlab_port = get_matlab_port_from_ready_file(matlab_ready_file)
    count = 0

    with pytest.raises(ConnectionError):
        while True:
            try:
                url = f"http://localhost:{matlab_port}/index-jsd-cr.html"

                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as resp:
                        assert resp.content_type == "text/html"
                        assert resp.status == 200
                        assert resp.content is not None

                break
            except:
                count += 1
                if count > TWO_MAX_TRIES:
                    raise ConnectionError
                time.sleep(HALF_SECOND_DELAY)


def get_matlab_port_from_ready_file(matlab_ready_file):
    for i in range(FIVE_MAX_TRIES):
        try:
            with open(matlab_ready_file) as f:
                return int(f.read())
        # Retry in the event that matlab_ready_file isn't created yet or
        # it has been created but the matlab_port information is not yet
        # written into the file which throws ValueError while converting to int.
        except (FileNotFoundError, ValueError):
            time.sleep(HALF_SECOND_DELAY)
            continue
