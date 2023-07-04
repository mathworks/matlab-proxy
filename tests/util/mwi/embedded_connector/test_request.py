import pytest
from matlab_proxy.util import mwi
from matlab_proxy.util.mwi.exceptions import EmbeddedConnectorError
from tests.util import MockResponse


async def test_send_request_success(mocker):
    json_data = {"hello": "world"}

    payload = json_data
    mock_resp = MockResponse(payload=payload, ok=True)

    mocked = mocker.patch("aiohttp.ClientSession.request", return_value=mock_resp)
    res = await mwi.embedded_connector.send_request(
        url="https://localhost:3000", data=json_data, method="GET"
    )

    assert json_data["hello"] == res["hello"]


async def test_send_request_failure(mocker):
    json_data = {"hello": "world"}

    payload = json_data
    mock_resp = MockResponse(payload=payload, ok=False)

    mocked = mocker.patch("aiohttp.ClientSession.request", return_value=mock_resp)

    # Failed to communicate with EmbeddedConnector
    with pytest.raises(EmbeddedConnectorError):
        res = await mwi.embedded_connector.send_request(
            url="https://localhost:3000", method="GET", data=json_data
        )

    # Doesnt have url or data or method
    mock_resp = MockResponse(payload=payload, ok=False)

    for key in ["url", "method"]:
        options = {
            "url": "https://localhost:3000",
            "data": json_data,
            "method": "GET",
        }
        options[key] = ""
        with pytest.raises(EmbeddedConnectorError):
            res = await mwi.embedded_connector.send_request(**options)
