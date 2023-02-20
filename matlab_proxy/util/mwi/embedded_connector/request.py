# Copyright (c) 2020-2022 The MathWorks, Inc.

""" 
This file contains the methods to communicate with the embedded connector.
"""

import json

from matlab_proxy.util.mwi.exceptions import EmbeddedConnectorError

from .helpers import get_data_for_ping_request, get_ping_endpoint


async def send_request(url: str, data: dict, method: str, headers: dict = None) -> dict:
    """A helper method to send various kinds of HTTP requests to the embedded connector.
    The url and method params are required.

    Args:
        url (str): URL to send HTTP request
        method (str): HTTP Request type.
        payload (dict): Payload for the HTTP request
        headers (dict): Headers for the HTTP request.

    Raises:
        EmbeddedConnectorError: When unable to get a response from the Embedded connector

    Returns:
        dict: The json response from Embedded connector
    """
    import aiohttp

    if not url or not method:
        raise EmbeddedConnectorError(
            f"url or method key is missing in the options parameter."
        )

    if data and isinstance(data, dict):
        data = json.dumps(data)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.request(
                method=method, url=url, data=data, headers=None, ssl=False
            ) as resp:
                if resp.reason != "OK":
                    # Converting to dict and formatting for printing
                    data = json.loads(data)

                    raise EmbeddedConnectorError(
                        f"""Failed to communicate with Embedded Connector.\nHTTP Request details:\n{json.dumps(data, indent=2)}"""
                    )

                return await resp.json()
    except Exception as err:
        raise err


async def get_state(mwi_server_url):
    """Returns the state of MATLAB's Embedded Connector.

    Args:
        port (int): The port on which the embedded connector is running at

    Returns:
        str: Either "up" or "down"
    """
    data = get_data_for_ping_request()
    url = get_ping_endpoint(mwi_server_url)
    try:
        resp = await send_request(url=url, data=data, method="POST")
        if not resp["messages"]["PingResponse"][0]["messageFaults"]:
            return "up"
    except Exception:
        pass

    return "down"
