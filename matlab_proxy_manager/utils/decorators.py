# Copyright 2025 The MathWorks, Inc.

import functools
from typing import Callable

from matlab_proxy_manager.utils.constants import (
    HEADER_MWI_MPM_CONTEXT,
)
from matlab_proxy_manager.utils.helpers import render_error_page


def validate_incoming_request_decorator(endpoint: Callable):
    """Decorator to validate incoming requests.

    This decorator checks if the request contains the required MWI_MPM_CONTEXT header.
    If the header is not found, it returns an error page. Otherwise, it adds the context
    to the request object and proceeds with the endpoint execution.

    Args:
        endpoint (Callable): The endpoint function to be decorated.

    Returns:
        Callable: The wrapped function that validates the request before calling the endpoint.
    """

    @functools.wraps(endpoint)
    async def wrapper(req):
        ctx = req.headers.get(HEADER_MWI_MPM_CONTEXT)
        if not ctx:
            return render_error_page(
                f"Required header: ${HEADER_MWI_MPM_CONTEXT} not found in the request"
            )
        # Add ctx to the request object
        req.ctx = ctx
        return await endpoint(req)

    return wrapper
