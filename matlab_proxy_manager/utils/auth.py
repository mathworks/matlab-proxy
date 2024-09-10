# Copyright 2024 The MathWorks, Inc.
from hmac import compare_digest

from aiohttp import web

from matlab_proxy_manager.utils import logger
from matlab_proxy_manager.utils.constants import HEADER_MWI_MPM_AUTH_TOKEN

log = logger.get()


async def authenticate_request(request):
    """Authenticates incoming request by verifying whether the expected token is in the request.

    The MWI-MPM-AUTH-TOKEN must be present in the request's headers.

    Returns True/False based on whether the request is authenticated.
    """

    log.debug("<======== Authenticate request: %s", request)
    return await _is_valid_token_in_headers(request)


def authenticate_access_decorator(endpoint):
    """This decorator verifies that the request to an endpoint exposed by matlab-proxy-manager
    contains the correct mpm auth token before servicing an endpoint."""

    async def protect_endpoint(request):
        """Passes request to the endpoint after validating the token

        Args:
            request (HTTPRequest) : Web Request to endpoint

        Raises:
            web.HTTPForbidden: Thrown when validation of token fails
        """
        if await authenticate_request(request):
            # request is authentic, proceed to execute the endpoint
            return await endpoint(request)
        raise web.HTTPForbidden(reason="Unauthorized access!")

    return protect_endpoint


async def _is_valid_token_in_headers(request):
    """Checks the request headers for mpm auth token

    Args:
        request (HTTPRequest) : Used to access app settings

    Returns:
        Boolean : True if valid token is found, else False
    """
    headers = request.headers
    if HEADER_MWI_MPM_AUTH_TOKEN in headers:
        return await _is_valid_token(headers[HEADER_MWI_MPM_AUTH_TOKEN], request)

    log.debug("Header: %s not found in request headers", HEADER_MWI_MPM_AUTH_TOKEN)
    return False


async def _is_valid_token(token, request):
    """Checks if token contains expected value.

    Args:
        token (str): Token string to validate
        request (HTTPRequest) : Used to access app settings

    Returns:
        _type_: True if token is valid, false otherwise.
    """
    # Check if the token provided in the request matches the original token
    # equivalent to a == b, but protects against timing attacks
    saved_token = request.app["auth_token"]
    is_valid = compare_digest(token, saved_token)
    log.debug("Token validation %s ", "successful." if is_valid else "failed.")
    return is_valid
