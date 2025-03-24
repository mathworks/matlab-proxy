# Copyright 2025 The MathWorks, Inc.
"""A common fixture that could be used by various test classes to disable authentication"""

import pytest


@pytest.fixture
def patch_authenticate_access_decorator(mocker):
    """
    Fixture to patch the authenticate_access decorator for testing purposes.

    This fixture mocks the 'authenticate_request' function from the
    'token_auth' module to always return True,
    effectively bypassing authentication for tests.
    """
    return mocker.patch(
        "matlab_proxy.util.mwi.token_auth.authenticate_request",
        return_value=True,
    )
