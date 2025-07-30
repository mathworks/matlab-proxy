# Copyright 2025 The MathWorks, Inc.

from http.cookies import Morsel, SimpleCookie
from typing import Dict

from matlab_proxy.util import mwi

logger = mwi.logger.get()


# For more information about HttpOnly attribute
# of a cookie, check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Set-Cookie#httponly
class HttpOnlyCookieJar:
    """
    A lightweight, HttpOnly, in-memory cookie store.

    Its sole responsibility is to parse and store 'Set-Cookie' headers as Morsel objects and
    store them in the cookie-jar only if they are marked as HttpOnly.
    """

    def __init__(self):
        self._cookie_jar: Dict[str, Morsel] = {}
        logger.debug("Cookie Jar Initialized")

    def _get_cookie_name(self, cookie: SimpleCookie) -> str:
        """
        Returns the name of the cookie.
        """
        return list(cookie.keys())[0]

    def update_from_response_headers(self, headers) -> None:
        """
        Parses 'Set-Cookie' headers from a response and stores the resulting
        cookie objects (Morsels) only if they are HttpOnly cookies.
        """
        for set_cookie_val in headers.getall("Set-Cookie", []):
            cookie = SimpleCookie()
            cookie.load(set_cookie_val)
            cookie_name = self._get_cookie_name(cookie)
            morsel = cookie[cookie_name]

            if morsel["httponly"]:
                self._cookie_jar[cookie_name] = morsel
                logger.debug(
                    f"Stored cookie object for key '{cookie_name}'. Value: '{cookie[cookie_name]}'"
                )

            else:
                logger.warning(
                    f"Cookie {cookie_name} is not a HttpOnly cookie. Skipping it."
                )

    def get_cookies(self):
        """
        Returns a copy of the internal dictionary of stored cookie Morsels.
        """
        return list(self._cookie_jar.values())

    def get_dict(self) -> Dict[str, str]:
        """
        Returns the stored cookies as a simple dictionary of name-to-value strings,
        which is compatible with aiohttp's 'LooseCookies' type.
        """
        loose_cookies = {
            name: morsel.value for name, morsel in self._cookie_jar.items()
        }
        return loose_cookies

    def clear(self):
        """Clears all stored cookies."""
        logger.info("Cookie Jar Cleared")
        self._cookie_jar.clear()
