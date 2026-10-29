# Copyright 2020-2026 The MathWorks, Inc.

# This file contains functions required to enable token based authentication in the server.

import os
import secrets
import time
from hashlib import sha256
from hmac import compare_digest
from urllib.parse import parse_qs

from aiohttp import web
from aiohttp_session import get_session, new_session

from matlab_proxy.constants import SESSION_COOKIE_RENEWAL_WINDOW_SECONDS
from matlab_proxy.util.mwi import environment_variables as mwi_env
from matlab_proxy.util.mwi import logger as mwi_logger

logger = mwi_logger.get()

## Module Public Methods:


def generate_mwi_auth_token_and_hash():
    """
    Generate the MWI Token and a hash for that token to be used by the server,
    based on the environment variables that control it.

    Token Auth is enabled by default, unless MWI_ENABLE_TOKEN_AUTH is explicitly set to False.

    If MWI_ENABLE_TOKEN_AUTH is set, and MWI_AUTH_TOKEN is unset, then generate a token
    else if MWI_AUTH_TOKEN is set, use that token for authentication.

    Returns the Token and its hash to be used for authentication if enabled.
    Returns None, if Token-Based Authentication is not enabled by user.
    """
    env_name_enable_mwi_token_auth = mwi_env.get_env_name_enable_mwi_auth_token()
    env_name_mwi_auth_token = mwi_env.get_env_name_mwi_auth_token()
    enable_token_auth = os.getenv(env_name_enable_mwi_token_auth, "").lower()
    auth_token = os.getenv(env_name_mwi_auth_token, "")

    if enable_token_auth == "false":
        if auth_token:
            logger.warning(
                f"Ignoring {env_name_mwi_auth_token}, as {env_name_enable_mwi_token_auth} explicitly set to false"
            )
        return _format_token_as_dictionary(None)

    if auth_token:
        auth_token = auth_token.strip()
        logger.debug(f"Using provided {env_name_mwi_auth_token}.")
        return _format_token_as_dictionary(auth_token)

    # default catch-all for when the env variables are not set or above conditions are not met.
    # This path will be executed if MWI_ENABLE_TOKEN_AUTH is set to true/Any value (default workflow)
    generated_token = secrets.token_urlsafe()
    logger.debug("Using auto-generated token.")
    return _format_token_as_dictionary(generated_token)


def get_mwi_auth_token_access_str(app_settings):
    """Returns formatted string with mwi token for use with server URL"""
    if app_settings["mwi_is_token_auth_enabled"]:
        mwi_auth_token_name = app_settings["mwi_auth_token_name_for_http"]
        mwi_auth_token = app_settings["mwi_auth_token"]
        return f"?{mwi_auth_token_name}={mwi_auth_token}"

    # Return empty string if token auth is not enabled
    return ""


async def authenticate_request(request):
    """Authenticates incoming request by verifying whether the expected token is in the request.

    The mwi_auth_token must be present either in:
    a. session cookie
    b. request's query parameters
    c. or the request's headers.

    Returns True/False based on whether the request is authenticated.
    Returns True when authentication is disabled.
    """

    logger.trace(f"<======== Authenticate request: {request}")

    if _is_mwi_token_auth_enabled(request):
        logger.trace("Authentication is Enabled.")
        is_authenticated = (
            await _is_valid_token_in_session_cookie(request)
            or await _is_valid_token_in_headers(request)
            or await _is_valid_token_in_url_query(request)
        )
        if is_authenticated:
            logger.trace("Authentication successful. ========>")
        else:
            logger.error("Token Authentication failed. ========>")

        return is_authenticated

    logger.debug("Token Authentication disabled.========>")
    return True


async def renew_session_cookie_if_valid(request):
    """Renew a valid cookie without requiring the request to be authenticated."""
    logger.debug(
        f"Session cookie renewal check: method={request.method}, path={request.path}."
    )

    if not _is_mwi_token_auth_enabled(request):
        logger.debug(
            "Session cookie renewal not applicable: token authentication is disabled."
        )
        return

    session = await get_session(request)
    token_name = await _get_token_name(request)
    if token_name not in session:
        logger.debug(
            "Session cookie renewal not applicable: "
            "no authenticated session cookie was found."
        )
        return

    if not await _is_valid_token(session[token_name], request):
        logger.debug(
            "Session cookie renewal not applicable: "
            "the session cookie failed authentication."
        )
        return

    await _renew_session_cookie_if_needed(request, session)


def authenticate_access_decorator(endpoint):
    """This decorator verifies that the request to an endpoint exposed by matlab-proxy
    contains the correct MWI_AUTH_TOKEN before servicing an endpoint."""

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
        else:
            raise web.HTTPForbidden(reason="Unauthorized access to matlab-proxy.")

    return protect_endpoint


## Module Private Methods:


async def _get_token_name(request):
    """Gets the name of the token from settings.

    Args:
        request (HTTPRequest) : Used to get to app settings

    Returns:
        str : token name
    """
    app_settings = request.app["settings"]
    return app_settings["mwi_auth_token_name_for_env"]


def _get_token_name_for_http(request):
    """Gets the name of the token from settings.

    Args:
        request (HTTPRequest) : Used to get to app settings

    Returns:
        str : token name
    """
    app_settings = request.app["settings"]
    return app_settings["mwi_auth_token_name_for_http"]


async def _get_token(request):
    """Gets the value of secret token from settings.

    Args:
        request (HTTPRequest) : Used to get to app settings

    Returns:
        str : token value
    """
    app_settings = request.app["settings"]
    return app_settings[await _get_token_name(request)]


async def _get_token_hash(request):
    """Gets the hashed value of secret token from settings.

    Args:
        request (HTTPRequest) : Used to get to app settings

    Returns:
        str : token hash
    """
    app_settings = request.app["settings"]
    return app_settings["mwi_auth_token_hash"]


async def _store_token_hash_into_session(request):
    """Stores the token hash into the session cookie."""
    # Always use `new_session` during login to guard against
    # Session Fixation. See aiohttp-session#281
    session = await new_session(request)

    # Stash token hash in session for other endpoints
    session[await _get_token_name(request)] = await _get_token_hash(request)
    logger.trace(f"Created session and saved cookie.")


def _should_renew_session_cookie(session):
    """Return whether a session cookie is within one hour of expiring."""
    if session.max_age is None:
        return False

    session_age = time.time() - session.created
    renewal_threshold = session.max_age - SESSION_COOKIE_RENEWAL_WINDOW_SECONDS
    should_renew = session_age >= renewal_threshold

    if should_renew:
        logger.debug(
            "Session cookie renewal required: "
            f"age={session_age:.1f}s, threshold={renewal_threshold:.1f}s, "
            f"max_age={session.max_age}s."
        )
    else:
        remaining_time = renewal_threshold - session_age
        logger.debug(
            f"Session cookie renewal not required: renewal in {remaining_time:.1f}s."
        )

    return should_renew


async def _renew_session_cookie_if_needed(request, session):
    """Replace an aging session while preserving its authenticated state."""
    if not _should_renew_session_cookie(session):
        return

    previous_created = session.created
    token_name = await _get_token_name(request)

    # Reassigning the validated token marks the session as changed and resets
    # its creation time. aiohttp-session then writes a fresh encrypted cookie.
    session[token_name] = session[token_name]
    logger.debug(
        "Session cookie renewal prepared: "
        f"previous_created={previous_created}, "
        f"renewed_created={session.created}, "
        f"entries={len(session)}, "
        f"empty={session.empty}, "
        f"max_age={session.max_age}s."
    )


def _is_mwi_token_auth_enabled(request):
    """Returns True/False based on whether the mwi_auth_token_auth is enabled in app settings

    Args:
        request (HTTPRequest) : Used to get access to app settings
    """
    app_settings = request.app["settings"]
    return app_settings["mwi_is_token_auth_enabled"]


async def _is_valid_token(token, request):
    """Checks if token contains expected value.

    Args:
        token (str): Token string to validate
        request (HTTPRequest) : Used to access app settings

    Returns:
        _type_: True is token is valid, false otherwise.
    """
    # Check if the token provided in the request matches the hash or the original token
    # equivalent to a == b, but protects against timing attacks
    is_valid = compare_digest(token, await _get_token_hash(request)) or compare_digest(
        token, await _get_token(request)
    )
    logger.trace("Token validation " + ("successful." if is_valid else "failed."))
    return is_valid


async def _is_valid_token_in_session_cookie(request):
    """Checks the session cookie for auth token

    Args:
        request (HTTPRequest) : Used to access app settings

    Returns:
        Boolean : True if valid token is found
    """
    logger.trace("Checking for token in session cookie...")
    session = await get_session(request)
    logger.trace(f"Got session cookie.")
    token_name = await _get_token_name(request)
    if token_name in session:
        stored_session_token = session[token_name]
        logger.trace(f"Found token in session cookie, validating...")
        return await _is_valid_token(stored_session_token, request)

    logger.trace("Token not found in session cookie.")
    return False


async def _is_valid_token_in_url_query(request):
    """Checks the url_query parameter for auth token

    Args:
        request (HTTPRequest) : Used to access app settings

    Returns:
        Boolean : True if valid token is found
    """
    logger.trace("Checking for token in url query...")
    query_string = request.query_string
    logger.trace(f"url query parameters found:{query_string}")
    if query_string:
        token_name = _get_token_name_for_http(request)
        parsed_token = parse_qs(request.query_string).get(token_name)
        if parsed_token:
            parsed_token = parsed_token[0]
            logger.trace("parsed_token from url query string.")
            return await _is_valid_token(parsed_token, request)

    logger.trace("Token not found in url query.")
    return False


async def _is_valid_token_in_headers(request):
    """Checks the request headers for auth token
    Additionally, save token into session cookie when a token is found.
    This is done to avoid the front end from having to send the token in every header.

    Args:
        request (HTTPRequest) : Used to access app settings

    Returns:
        Boolean : True if valid token is found
    """
    logger.trace("Checking for token in request headers...")
    headers = request.headers
    token_name = _get_token_name_for_http(request)
    if token_name in headers:
        logger.trace(f"Token found in headers: {token_name}")
        is_valid_token = await _is_valid_token(headers[token_name], request)
        if is_valid_token:
            await _store_token_hash_into_session(request)
        return is_valid_token

    logger.trace("Token not found in request headers.")
    return False


def _generate_hash(message):
    """Util function to generate a sha256 hash for a message

    Args:
        message (str): message to be hashed

    Returns:
        str: sha256 hash for a given message
    """
    return sha256(message.encode()).hexdigest() if message is not None else None


def _format_token_as_dictionary(token):
    return {"token": token, "token_hash": _generate_hash(token)}
