# Copyright 2023-2024 The MathWorks, Inc.

import os
import json
import requests
from requests.adapters import HTTPAdapter, Retry
from integration import integration_tests_utils as utils
from urllib.parse import urlparse


def test_matlab_down():
    """Test that matlab is down and no license is picked up"""

    mwi_app_port = os.environ["MWI_APP_PORT"]
    http_endpoint = "/get_status"

    parsed_url = urlparse(utils.get_connection_string(mwi_app_port))

    connection_scheme = parsed_url.scheme
    uri = (
        connection_scheme + "://" + parsed_url.netloc + parsed_url.path + http_endpoint
    )

    json_response = None

    with requests.Session() as s:
        retries = Retry(total=10, backoff_factor=0.1)
        s.mount(f"{connection_scheme}://", HTTPAdapter(max_retries=retries))
        response = s.get(uri, verify=False)
        json_response = json.loads(response.text)

    matlab_status = json_response["matlab"]["status"]
    assert matlab_status == "down"


def test_matlab_proxy_app_installed():
    import shutil

    """Test that the executable matlab_proxy_app is located on PATH and executable"""

    which_matlabproxyapp = shutil.which("matlab-proxy-app")
    assert (
        which_matlabproxyapp is not None
    ), "matlab-proxy-app does not exist in system path"
    assert (
        os.access(which_matlabproxyapp, os.R_OK) == True
    ), """matlab-proxy-app does not have the read permissions"""
    assert (
        os.access(which_matlabproxyapp, os.X_OK) == True
    ), """matlab-proxy-app does not have the execute permissions"""
