# Copyright 2020-2024 The MathWorks, Inc.

"""This file contains helper methods which return the details required for sending
a HTTP request to the Embedded Connector."""


from matlab_proxy.util import mwi
from matlab_proxy.util.mwi import environment_variables as mwi_env


def get_mvm_endpoint(mwi_server_url):
    """Returns the endpoint at which mvm can be communicated with

    Args:
        mwi_server_url (str): The complete origin where the matlab-proxy server
        is running at.
        Example: https://www.matlab-proxy.com:8056

    Returns:
        str: Complete origin URL to communicate with mvm
    """
    return f"{mwi_server_url}/messageservice/json/secure"


def get_ping_endpoint(mwi_server_url):
    """Returns the endpoint to communicate with MATLAB's Embedded Connector to
    get its latest status.

    Args:
        mwi_server_url (str): The complete origin where the matlab-proxy server
        is running at.
        Example: https://www.matlab-proxy.com:8056

    Returns:
        str: Complete origin URL to communicate with MATLAB's Embedded Connector.
    """
    return f"{mwi_server_url}/messageservice/json/state"


def get_data_for_ping_request():
    """Returns data required to send in the payload for a ping request to the embedded connector

    Returns:
        dict: Payload data
    """
    return {"messages": {"Ping": [{}]}}


def get_data_for_matlab_busy_status_request():
    """Returns data required to send in the payload for a MATLAB busy/idle status request to the embedded connector

    Returns:
        dict: Payload data
    """
    return {"messages": {"GetMatlabStatus": [{}]}}


def get_data_to_eval_mcode(m_code):
    """Returns the data required to send in the payload for evaluating mcode using eval function to the embedded connector.

    Args:
        m_code (str): MATLAB code to be evaluated

    Returns:
        dict: Payload data.
    """
    data = {
        "uuid": __generate_uuid(),
        "messages": {"Eval": [{"mcode": m_code, "uuid": __generate_uuid()}]},
        "computeToken": {"computeSessionId": "unused"},
    }

    return data


def get_data_to_feval_mcode(m_function, *args, nargout):
    """Returns the data required to send in the payload for evaluating mcode using Feval function to the embedded connector.

    Args:
        m_function (str): MATLAB function to be evaluated
        nargout (int): Number of return values the MATLAB function will return

    Returns:
        dict: Payload data.
    """
    data = {
        "uuid": __generate_uuid(),
        "messages": {
            "FEval": [
                {
                    "function": m_function,
                    "arguments": [*args],
                    "nargout": nargout,
                    "priority": 1,
                    "dequeMode": "ppe",
                    "uuid": __generate_uuid(),
                }
            ]
        },
        "computeToken": {"computeSessionId": "unused"},
    }

    return data


def __generate_uuid():
    """Generates random strings of length 8 containing mix of numbers and capital letters.
        Note: This function mimics the UUID generation in MOS.
    Returns:
        str: Generates a 8 character long string used to represent an UUID for use with JS API
    """
    import random

    uuid = ""
    numbers = "0123456789"
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    for i in range(0, 8):
        if random.random() <= 0.5:
            index = random.randint(0, len(numbers) - 1)
            uuid += numbers[index]
        else:
            index = random.randint(0, len(letters) - 1)
            uuid += letters[index]

    return uuid
