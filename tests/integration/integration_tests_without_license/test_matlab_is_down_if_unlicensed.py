# Copyright 2023 The MathWorks, Inc.

import os
import json
import requests
from requests.adapters import HTTPAdapter, Retry


def test_matlab_down():
    """Test that matlab is down and no license is picked up

    Args:
        start_matlab_proxy_fixture : A pytest fixture to start the matlab proxy
    """

    mwi_app_port = os.environ["MWI_APP_PORT"]
    mwi_base_url = os.environ["MWI_BASE_URL"]
    http_endpoint = "get_status"

    uri = f"http://127.0.0.1:{mwi_app_port}{mwi_base_url}/{http_endpoint}"

    json_response = None
    with requests.Session() as s:
        retries = Retry(total=10, backoff_factor=0.1)
        s.mount("http://", HTTPAdapter(max_retries=retries))
        response = s.get(uri)
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
