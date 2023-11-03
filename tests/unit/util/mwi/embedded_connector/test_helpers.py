# Copyright 2022 The MathWorks, Inc.

from matlab_proxy.util import mwi


def test_get_data_to_eval_mcode():
    necessary_keys = ["uuid", "messages", "computeToken"]
    mcode = "exit"
    data = mwi.embedded_connector.helpers.get_data_to_eval_mcode(mcode)

    assert set(necessary_keys).issubset(set(data.keys()))
    assert data["messages"]["Eval"][0]["mcode"] == mcode


def test_get_data_to_feval_mcode():
    necessary_keys = ["uuid", "messages", "computeToken"]
    m_function = "round"
    args = [3.135, 2]
    nargout = 2
    data = mwi.embedded_connector.helpers.get_data_to_feval_mcode(
        m_function, *args, nargout=nargout
    )

    assert set(necessary_keys).issubset(set(data.keys()))
    feval_data = data["messages"]["FEval"][0]

    assert feval_data["function"] == m_function
    assert feval_data["arguments"] == args
    assert feval_data["nargout"] == nargout
