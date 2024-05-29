# Copyright 2024 The MathWorks, Inc.
import pytest

from matlab_proxy.util.mwi.download import (
    _get_download_payload_path,
    get_download_url,
    is_download_request,
)


# Mock the request object
@pytest.fixture
def mock_request_fixture(mocker):
    mock_req = mocker.MagicMock()
    mock_req.app = {
        "settings": {"base_url": ""},
        "state": mocker.MagicMock(),
    }
    mock_req.rel_url = mocker.MagicMock()
    return mock_req


def _get_expected_output_based_on_os_type(paths: list) -> str:
    import matlab_proxy.util.system as system

    return "\\".join(paths) if system.is_windows() else "/".join(paths)


# Test for is_download_request function
@pytest.mark.parametrize(
    "test_base_url, path, expected",
    [
        ("/", "/download/something", True),
        ("", "/download/something", True),
        ("/base", "/base/download/something", True),
        ("/base", "/download/something", False),
    ],
    ids=[
        "/ base url and path starting with /download",
        "empty base url and path starting with /download",
        "non-empty base url and path starting with that base url",
        "non-empty base url and path not starting with that base url",
    ],
)
def test_is_download_request(mock_request_fixture, test_base_url, path, expected):
    mock_request_fixture.app["settings"]["base_url"] = test_base_url
    mock_request_fixture.rel_url.path = path
    assert is_download_request(mock_request_fixture) == expected


# Test for _get_download_payload_path function
# This test is a bit tricky since it involves file system operations and OS checks.
# We will mock system.is_windows() and test for both Windows and Posix systems.
@pytest.mark.parametrize(
    "is_windows, test_base_url, path, expected",
    [
        (
            True,
            "",
            "/downloadC:\\some\\path\\to\\file.txt",
            "C:\\some\\path\\to\\file.txt",
        ),
        (
            True,
            "/base",
            "/base/downloadC:\\some\\path\\to\\file.txt",
            "C:\\some\\path\\to\\file.txt",
        ),
        (
            False,
            "",
            "/download/some/path/to/file.txt",
            _get_expected_output_based_on_os_type(["/some", "path", "to", "file.txt"]),
        ),
        (
            False,
            "/base",
            "/base/download/some/path/to/file.txt",
            _get_expected_output_based_on_os_type(["/some", "path", "to", "file.txt"]),
        ),
    ],
    ids=[
        "Windows with null base url",
        "Windows with non-null base url",
        "Linux with null base url",
        "Linux with non-null base url",
    ],
)
def test_get_download_payload_path(
    mock_request_fixture, mocker, is_windows, test_base_url, path, expected
):
    mocker.patch("matlab_proxy.util.system.is_windows", return_value=is_windows)
    mock_request_fixture.app["settings"]["base_url"] = test_base_url
    mock_request_fixture.rel_url.path = path
    assert _get_download_payload_path(mock_request_fixture) == expected


def test_get_download_payload_path_invalid_request(mock_request_fixture):
    test_base_url = "/base"
    path = "/download/something"

    mock_request_fixture.app["settings"]["base_url"] = test_base_url
    mock_request_fixture.rel_url.path = path

    assert _get_download_payload_path(mock_request_fixture) is None


@pytest.mark.parametrize(
    "response_json, expected_url",
    [
        (
            {
                "messages": {
                    "FEvalResponse": [
                        {"isError": False, "results": ["http://download-url.com"]}
                    ]
                }
            },
            "http://download-url.com",
        ),
        ({"messages": {"FEvalResponse": [{"isError": True}]}}, None),
    ],
    ids=["connector returning correct download url", "connector returning an error"],
)
async def test_get_download_url(
    mock_request_fixture, mocker, response_json, expected_url
):
    test_base_url = "/"
    path = "/download/some/path/to/file.txt"

    mock_request_fixture.app["state"].settings = {
        "mwi_server_url": "http://mwi-server.com"
    }
    mock_request_fixture.app["settings"]["base_url"] = test_base_url
    mock_request_fixture.rel_url.path = path

    mocker.patch(
        "matlab_proxy.util.mwi.embedded_connector.helpers.get_data_to_feval_mcode",
        return_value={},
    )
    mocker.patch(
        "matlab_proxy.util.mwi.embedded_connector.helpers.get_mvm_endpoint",
        return_value="http://mwi-server.com",
    )
    mocker.patch(
        "matlab_proxy.util.mwi.embedded_connector.send_request",
        return_value=response_json,
    )

    download_url = await get_download_url(mock_request_fixture)

    assert download_url == expected_url
