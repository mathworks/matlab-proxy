# Copyright 2020-2022 The MathWorks, Inc.

import matlab_proxy
from matlab_proxy import util


def test_get_mwi_ddux_value():
    """Tests ddux value for matlab-proxy with different extension names"""
    expected_result = matlab_proxy.__get_matlab_proxy_base_ddux_value()
    actual_result = matlab_proxy.get_mwi_ddux_value(
        matlab_proxy.get_default_config_name()
    )

    assert expected_result == actual_result

    expected_result = f"MATLAB_PROXY:HELLO_WORLD:V1"
    actual_result = matlab_proxy.get_mwi_ddux_value("hello world")

    assert expected_result == actual_result

    actual_result = matlab_proxy.get_mwi_ddux_value(" \n \t hello-world  \n")
    assert expected_result == actual_result
