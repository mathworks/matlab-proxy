# Copyright 2025 The MathWorks, Inc.


class MockWebSocketClient:
    """Mock class for testing WebSocket client functionality.

    This class simulates a WebSocket client for testing purposes, providing async iteration
    over predefined messages and basic client functionality.

    Args:
        text (str, optional): Text to be returned by text() method. Defaults to None.
        status (int, optional): HTTP status code. Defaults to 200.
        headers (dict, optional): HTTP headers. Defaults to None.
        messages (list, optional): List of messages to be returned during iteration. Defaults to None.
    """

    def __init__(
        self, text=None, status: int = 200, headers=None, messages=None
    ) -> None:
        self._text = text
        self.status = status
        self.headers = headers
        self.messages = messages or []
        self._message_iter = iter(self.messages)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self._message_iter)
        except StopIteration as exc:
            raise StopAsyncIteration from exc

    async def text(self):
        return self._text

    async def __aexit__(self, *args) -> None:
        pass

    async def __aenter__(self):
        return self
