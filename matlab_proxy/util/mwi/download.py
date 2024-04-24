# Copyright 2024 The MathWorks, Inc.

# This file contains functions required to enable downloads from the file browser
from matlab_proxy.util.mwi import logger as mwi_logger
from matlab_proxy.util import mwi, system

logger = mwi_logger.get()


def _is_null_base_url(base_url):
    return base_url == "/" or base_url == ""


def is_download_request(req):
    """
    Determine if the incoming request is for a download action.

    This function checks if the request's relative URL path starts with
    '/download/' or with '{base_url}/download/', depending on the base URL
    specified in the application settings.

    Parameters:
        req (HTTPRequest): HTTPRequest Object

    Returns:
    - bool: True if the request is for a download, False otherwise.
    ```
    """

    base_url = req.app["settings"]["base_url"]
    if _is_null_base_url(base_url):
        return req.rel_url.path.startswith("/download")
    else:
        return req.rel_url.path.startswith(f"{base_url}/download")


async def get_download_url(req):
    """
    Asynchronously generates a download URL for a file.

    This function takes a request object, extracts the full path to the file, and
    uses the MATLAB Web Interface (MWI) to generate a download URL for that file.
    It logs the full path and the response from the MWI. If successful, it returns
    the download URL; otherwise, it returns None.

    Parameters:
        The request object containing necessary information to process the download.
    Returns:
        The download URL string if successful, None otherwise.
    Raises:
        Logs an error message and returns None if an error occurs.
    """
    full_path_to_file = _get_download_payload_path(req)
    logger.debug(f"full_path_to_file: {full_path_to_file}")

    args = [full_path_to_file, 1.0]
    data = mwi.embedded_connector.helpers.get_data_to_feval_mcode(
        "matlab.ui.internal.URLUtils.getURLToUserFile", *args, nargout=1
    )

    try:
        state = req.app["state"]
        headers = state._get_token_auth_headers()
        url = mwi.embedded_connector.helpers.get_mvm_endpoint(
            state.settings["mwi_server_url"]
        )
        resp_json = await mwi.embedded_connector.send_request(
            url=url,
            method="POST",
            data=data,
            headers=headers,
        )

        logger.debug(f"EC Response URL: {resp_json}")

        resp = resp_json["messages"]["FEvalResponse"][0]

        if not resp["isError"]:
            # No error detected, proceed to fetch the results
            download_url = resp["results"][0]
            logger.debug(f"download_url: {download_url}")
            base_url = req.app["settings"]["base_url"]
            return (
                download_url
                if _is_null_base_url(base_url)
                else f"{base_url}{download_url}"
            )

    except KeyError as key_err:
        logger.error(f"Invalid Key Usage Detected! Check key: {key_err}")
        pass

    except Exception as err:
        logger.error(
            f"Failed to create download url from the Embedded Connector due to err: {err}"
        )
        pass

    # In case of any failures.
    return None


def _get_download_payload_path(req):
    """
    Constructs the file system path to the payload for a download request.

    This function analyzes the incoming request to determine the intended file path
    for download. It takes into account the base URL from the application settings,
    the nature of the request (whether it's a download request), and the operating
    system to format the path correctly. The function supports different path
    formatting for Windows and Unix-like systems due to their differences in file
    system path syntax.

    Note:
        This function is intended to be used internally and starts with an underscore
        to indicate it is a private member of the module.

    Args:
        req: An object representing the incoming request, which includes the relative
             URL from which the file path can be deduced.

    Returns:
        A string representing the file system path to the requested download payload,
        or None if the request is not a download request.
    """
    base_url = req.app["settings"]["base_url"]
    if is_download_request(req):
        from pathlib import Path

        compare_str = (
            "/download" if _is_null_base_url(base_url) else f"{base_url}/download"
        )

        if system.is_windows():
            # On Windows, the URL is of the form : /downloadC:\some\path\to\file.txt
            return str(
                Path((req.rel_url.path).replace("/download", "/download/")).relative_to(
                    f"{compare_str}"
                )
            )
        else:
            # On Posix, the URL is of the form : /download/some/path/to/file.txt
            return "/" + str(Path((req.rel_url.path)).relative_to(f"{compare_str}"))

    return None
