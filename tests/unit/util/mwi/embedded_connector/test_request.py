# Copyright 2022-2023 The MathWorks, Inc.

import pytest
from matlab_proxy.util import mwi
from matlab_proxy.util.mwi.exceptions import EmbeddedConnectorError
from tests.unit.util import MockResponse


async def test_send_request_success(mocker):
    """Test to check the happy path for send_request
    Args:
        mocker : Built in pytest fixture
    """
    # Arrange
    json_data = {"hello": "world"}
    payload = json_data
    mock_resp = MockResponse(payload=payload, ok=True)
    _ = mocker.patch("aiohttp.ClientSession.request", return_value=mock_resp)

    # Act
    res = await mwi.embedded_connector.send_request(
        url="https://localhost:3000", data=json_data, method="GET"
    )

    # Assert
    assert json_data["hello"] == res["hello"]


async def test_send_request_failure(mocker):
    """Test to check if send_request fails when
    1) EC does not respond
    2) url or method is not supplied
    Args:
        mocker : Built in pytest fixture
    """

    # Arrange
    json_data = {"hello": "world"}

    payload = json_data
    mock_resp = MockResponse(payload=payload, ok=False)
    _ = mocker.patch("aiohttp.ClientSession.request", return_value=mock_resp)

    # Doesnt have url or data or method
    mock_resp = MockResponse(payload=payload, ok=False)

    # Act

    # Failed to communicate with EmbeddedConnector
    with pytest.raises(EmbeddedConnectorError):
        _ = await mwi.embedded_connector.send_request(
            url="https://localhost:3000", method="GET", data=json_data
        )

    for key in ["url", "method"]:
        options = {
            "url": "https://localhost:3000",
            "data": json_data,
            "method": "GET",
        }
        options[key] = ""
        # Assert
        with pytest.raises(EmbeddedConnectorError):
            _ = await mwi.embedded_connector.send_request(**options)
