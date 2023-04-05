# Copyright (c) 2020-2022 The MathWorks, Inc.

# This file contains functions required to enable token based authentication in the server.

import os
import secrets

from aiohttp import web
from aiohttp_session import get_session, new_session, setup
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from matlab_proxy.util.mwi import environment_variables as mwi_env

from . import logger as mwi_logger

logger = mwi_logger.get()


def decorator_authenticate_access(endpoint):
    """Decorates any endpoint function with token authentication checks."""
    logger.debug("inside decorator_authenticate_access")

    async def authenticate_access(request):
        """
        If Authentication is enabled, this function expects the token to be present either in
            the URL or in the session cookie.
        If token is provided and matches the expected secret, then the request is considered authentic,
            and the token is saved into the session cookie.
        """
        logger.debug(f" inside authenticate_access for request:{request}")
        app_settings = request.app["settings"]
        base_url = app_settings["base_url"]

        if await authenticate_request(request):
            logger.debug(
                f" Request is authenticated, proceed to endpoint:{endpoint}{request}"
            )
            return await endpoint(request)

    return authenticate_access


def is_mwi_token_auth_enabled(app_settings):
    """Returns True/False based on whether the mwi_auth_token_auth is enabled."""
    return app_settings["mwi_is_token_auth_enabled"]


def get_mwi_auth_token_access_str(app_settings):
    """Returns formatted string with mwi token for use with server URL"""
    if is_mwi_token_auth_enabled(app_settings):
        mwi_auth_token_name = app_settings["mwi_auth_token_name"]
        mwi_auth_token = app_settings["mwi_auth_token"]
        return f"?{mwi_auth_token_name}={mwi_auth_token}"

    # Return empty string if token auth is not enabled
    return ""


async def authenticate_request(request):
    """Returns True/False based on whether the server is authenticated."""

    logger.debug(f" inside authenticate_request for request:{request}")
    # Get information from APP
    app_settings = request.app["settings"]
    # Verify that the request contains the authorization token
    if is_mwi_token_auth_enabled(app_settings):
        logger.debug(" Token Authentication is Enabled!!")
        the_secret_token = app_settings["mwi_auth_token"]
        token_name = app_settings["mwi_auth_token_name"]
        base_url = app_settings["base_url"]

        # get token if present in URL
        parsed_url_token = await request.text()

        if parsed_url_token == "":
            logger.debug("No Token found in URL. Checking session cookie...")

            # Check to see if there are cookies?
            session = await get_session(request)
            logger.debug(f"Got session cookie : {session}")

            if token_name in session:
                stored_session_token = session[token_name]
                logger.debug(f"Found token with value: {stored_session_token}")
                # Verify that token contains expected value
                if stored_session_token == the_secret_token:
                    logger.debug("Token validation success!")
                    return True
                else:
                    logger.info("Invalid Token found in session!")
                    logger.debug(f"Expected: {the_secret_token}    ")
                    logger.debug(f"Actual  : {stored_session_token}")
                    return False
            else:
                logger.debug(f"{token_name} not found in session cookie.")
                return False
        else:
            logger.debug(f"Token found in URL with value: {parsed_url_token}")
            # Token is being provided, check it and stash it.
            if parsed_url_token == the_secret_token:
                logger.debug("Token validation success!")
                # Stash token in session for other endpoints
                # Always use `new_session` during login to guard against
                # Session Fixation. See aiohttp-session#281
                session = await new_session(request)
                session[token_name] = the_secret_token
                logger.debug(f"Created session : {session} and saved cookie")
                return True
            else:
                logger.info("Invalid Token found in URL!")
                logger.debug(f"Expected: {the_secret_token}")
                logger.debug(f"Actual  : {parsed_url_token}")
                return False
    else:
        # Token Authentication is not enabled
        logger.debug(" Token Authentication is NOT Enabled!!")
        return True


def generate_mwi_auth_token():
    """
    Generate the MWI Token to be used by the server,
    based on the environment variables that control it.

    Returns None, if Token-Based Authentication is not enabled by user.
    """
    is_mwi_auth_token_enabled = (
        os.getenv(mwi_env.get_env_name_enable_mwi_auth_token(), "false").lower()
        == "true"
    )
    mwi_auth_token = os.getenv(mwi_env.get_env_name_mwi_auth_token(), None)

    if is_mwi_auth_token_enabled:
        if mwi_auth_token and mwi_auth_token.strip():
            # Use the provided MWI token, after stripping leading and trailing whitespaces
            mwi_auth_token = mwi_auth_token.strip()
            logger.debug(f"Using provided mwi_auth_token: {mwi_auth_token.strip()}")
        else:
            # Generate a token
            mwi_auth_token = secrets.token_urlsafe()
    else:
        # Token Authentication must be enabled to provide custom tokens.
        if mwi_auth_token is not None:
            logger.error(
                "Ignoring MWI_AUTH_TOKEN. To enable, set MWI_ENABLE_TOKEN_AUTH to True !!!"
            )
            mwi_auth_token = None

    return mwi_auth_token
