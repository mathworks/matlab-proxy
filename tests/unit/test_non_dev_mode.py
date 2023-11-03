# Copyright 2020-2022 The MathWorks, Inc.

import os
import shutil
from pathlib import Path

import matlab_proxy
import pytest
from matlab_proxy.util.mwi import environment_variables as mwi_env

from tests.unit.test_app import FakeServer

"""
This file checks whether static assets are being added successfully to the
test web server's static route table in non-dev mode.
"""


@pytest.fixture(name="matlab_port_setup")
def matlab_port_fixture(monkeypatch):
    """A pytest fixture which monkeypatches an environment variable.

    Pytest by default sets MWI_DEV to true.
    Args:
        monkeypatch : A built-in pytest fixture
    """
    # For the test: test_non_dev, when run independently, works as expected.
    # But, when all the tests are run, if port 8000 was picked
    # by some previous test and was not released yet, then test_non_dev will fail to bind to it.
    # To overcome this, I've temporarily patched MWI_APP_PORT to pick a random port.
    try:
        import socket

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("", 0))
        port = s.getsockname()[1]
        s.close()
    except Exception as e:
        pass

    monkeypatch.setenv(mwi_env.get_env_name_development(), "false")
    monkeypatch.setenv(mwi_env.get_env_name_app_port(), str(port))


@pytest.fixture(name="build_frontend")
def build_frontend_fixture():
    """A method to build react front-end and place it in matlab_proxy directory

    This method builds react front-end and copies the built files to matlab_proxy/gui.
    Then adds __init__.py to each folder within it to make it accessible for python.
    This prework is for the purpose of adding the built files as static assets to the server.
    """

    static_files_dir = os.path.join(os.getcwd(), "matlab_proxy", "gui")

    try:
        shutil.rmtree(static_files_dir)

    except FileNotFoundError:
        pass

    finally:
        # Create static files
        os.mkdir(static_files_dir)
        with open(Path(static_files_dir) / "index.html", "w") as f:
            f.write("<h1> Hello World </h1>")

        with open(Path(static_files_dir) / "manifest.json", "w") as f:
            f.write('{"display: "standalone"}')

        build_contents = [
            {
                "dir": "css",
                "file": "index.css",
                "file_content": "html { height: 100%;}",
            },
            {
                "dir": "js",
                "file": "index.js",
                "file_content": "import React from 'react';'",
            },
            {
                "dir": "media",
                "file": "media.txt",
                "file_content": "Copyright (c) 2020-2022 The Mathworks, Inc.",
            },
        ]

        for build_content in build_contents:
            os.makedirs(Path(static_files_dir) / "static" / build_content["dir"])
            with open(
                Path(static_files_dir)
                / "static"
                / build_content["dir"]
                / build_content["file"],
                "w",
            ) as f:
                f.write(build_content["file_content"])

        (Path(static_files_dir) / "__init__.py").touch(exist_ok=True)

        for path, directories, filenames in os.walk(static_files_dir):
            for directory in directories:
                (Path(path) / directory / "__init__.py").touch(exist_ok=True)

        # Yield to execute test
        yield

        # Delete the static files after executing test.
        shutil.rmtree(static_files_dir)


@pytest.fixture(name="mock_settings_get")
def mock_settings_get_fixture(mocker):
    """Pytest fixture which mocks settings.get() method to return
    dev settings.

    Args:
        mocker : Built in pytest fixture
    """
    mocker.patch(
        "matlab_proxy.settings.get",
        return_value=matlab_proxy.settings.get(dev=True),
    )


@pytest.fixture(name="test_server")
def test_server_fixture(
    loop,
    aiohttp_client,
    build_frontend,
    matlab_port_setup,
    mock_settings_get,
):
    """A pytest fixture which yields a test server.

    This test server is used to test various endpoints. After gaining control back, gracefully shuts
    down the server.

    This fixture 'initializes' the test server with different constraints from the test server in test_app.py

    Args:
        loop : Event Loop
        aiohttp_client : A built-in pytest fixture
        build_frontend: Pytest fixture which generates the directory structure of static files with some placeholder content
        matlab_port_setup: Pytest fixture which monkeypatches 'MWI_DEV' env to False. This is required for the test_server to add static content
        mock_settings_get: Pytest fixture which mocks settings.get() to return dev settings when env 'MWI_DEV' is set to False.

    Yields:
        [aiohttp_client]: A aiohttp_client to send HTTP requests.
    """

    with FakeServer(loop, aiohttp_client) as test_server:
        yield test_server


async def test_non_dev(test_server):
    """Tests whether static files are being added to the web server.

    This test checks if the test_server successfully added the static files built and
    copied into matlab_proxy/gui folder are added to the static_route_table of the server.

    Args:
        test_server (aiohttp_client): A aiohttp server to send HTTP requests to.
    """
    resp = await test_server.get("/get_status")
    assert resp.status == 200

    assert test_server.app["static_route_table"] is not None
