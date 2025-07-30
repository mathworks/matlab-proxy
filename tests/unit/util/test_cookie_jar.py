# Copyright 2025 The MathWorks, Inc.

from http.cookies import Morsel, SimpleCookie

from multidict import CIMultiDict

from matlab_proxy.util.cookie_jar import HttpOnlyCookieJar


def test_simple_cookie_jar_initialization():
    """Test SimpleCookieJar initialization."""
    # Arrange
    # Nothing to arrange

    # Act
    cookie_jar = HttpOnlyCookieJar()

    # Assert
    assert cookie_jar._cookie_jar == {}


def test_get_cookie_name():
    """Test getting cookie name from SimpleCookie."""
    # Arrange
    cookie_jar = HttpOnlyCookieJar()
    cookie = SimpleCookie()
    cookie["test_cookie"] = "test_value"

    # Act
    cookie_name = cookie_jar._get_cookie_name(cookie)

    # Assert
    assert cookie_name == "test_cookie"


def test_get_cookie_name_with_multiple_cookies():
    """Test getting cookie name from SimpleCookie with multiple cookies."""
    # Arrange
    cookie_jar = HttpOnlyCookieJar()
    cookie_1, cookie_2 = SimpleCookie(), SimpleCookie()
    cookie_1["first_cookie"] = "first_value"
    cookie_2["second_cookie"] = "second_value"

    # Act
    cookie_name_1 = cookie_jar._get_cookie_name(cookie_1)
    cookie_name_2 = cookie_jar._get_cookie_name(cookie_2)

    # Assert
    assert cookie_name_1 == "first_cookie"
    assert cookie_name_2 == "second_cookie"


def test_update_from_response_headers_single_cookie():
    """Test updating cookie jar from response headers with single cookie."""
    # Arrange
    cookie_jar = HttpOnlyCookieJar()
    headers = CIMultiDict()
    headers.add("Set-Cookie", "JSESSIONID=abc123; Path=/; HttpOnly")

    # Act
    cookie_jar.update_from_response_headers(headers)

    # Assert
    assert "JSESSIONID" in cookie_jar._cookie_jar
    assert cookie_jar._cookie_jar["JSESSIONID"].value == "abc123"


def test_update_from_response_headers_multiple_cookies():
    """Test updating cookie jar from response headers with multiple cookies."""
    # Arrange
    cookie_jar = HttpOnlyCookieJar()
    headers = CIMultiDict()
    headers.add("Set-Cookie", "JSESSIONID=abc123; Path=/; HttpOnly")
    headers.add("Set-Cookie", "snc=1234; Path=/; Secure HttpOnly")

    # Act
    cookie_jar.update_from_response_headers(headers)

    # Assert
    assert "JSESSIONID" in cookie_jar._cookie_jar
    assert "snc" in cookie_jar._cookie_jar
    assert cookie_jar._cookie_jar["JSESSIONID"].value == "abc123"
    assert cookie_jar._cookie_jar["snc"].value == "1234"


def test_update_from_response_headers_no_set_cookie():
    """Test updating cookie jar when no Set-Cookie headers present."""
    # Arrange
    cookie_jar = HttpOnlyCookieJar()
    headers = CIMultiDict()
    headers.add("Content-Type", "application/json")

    # Act
    cookie_jar.update_from_response_headers(headers)

    # Assert
    assert len(cookie_jar._cookie_jar) == 0


def test_update_from_response_headers_overwrite_existing():
    """Test that updating cookie jar overwrites existing cookies with same name."""
    # Arrange
    cookie_jar = HttpOnlyCookieJar()
    headers1 = CIMultiDict()
    headers1.add("Set-Cookie", "JSESSIONID=old_value; Path=/ HttpOnly")
    headers2 = CIMultiDict()
    headers2.add("Set-Cookie", "JSESSIONID=new_value; Path=/ HttpOnly")

    # Act
    cookie_jar.update_from_response_headers(headers1)
    cookie_jar.update_from_response_headers(headers2)

    # Assert
    assert cookie_jar._cookie_jar["JSESSIONID"].value == "new_value"


def test_get_cookies():
    """Test getting all cookies as list of Morsel objects."""
    # Arrange
    cookie_jar = HttpOnlyCookieJar()
    headers = CIMultiDict()
    headers.add("Set-Cookie", "JSESSIONID=abc123; Path=/ HttpOnly")
    headers.add("Set-Cookie", "snc=1234; Path=/ HttpOnly")
    cookie_jar.update_from_response_headers(headers)

    # Act
    cookies = cookie_jar.get_cookies()

    # Assert
    assert len(cookies) == 2
    assert all(isinstance(cookie, Morsel) for cookie in cookies)
    values = [cookie.value for cookie in cookies]
    assert "abc123" in values
    assert "1234" in values


def test_get_cookies_empty_jar():
    """Test getting cookies from empty jar."""
    # Arrange
    cookie_jar = HttpOnlyCookieJar()

    # Act
    cookies = cookie_jar.get_cookies()

    # Assert
    assert cookies == []


def test_get_dict():
    """Test getting cookies as dictionary."""
    # Arrange
    cookie_jar = HttpOnlyCookieJar()
    headers = CIMultiDict()
    headers.add("Set-Cookie", "JSESSIONID=abc123; Path=/ HttpOnly")
    headers.add("Set-Cookie", "snc=1234; Path=/ HttpOnly")
    cookie_jar.update_from_response_headers(headers)

    # Act
    cookie_dict = cookie_jar.get_dict()

    # Assert
    assert isinstance(cookie_dict, dict)
    assert cookie_dict["JSESSIONID"] == "abc123"
    assert cookie_dict["snc"] == "1234"


def test_get_dict_empty_jar():
    """Test getting dictionary from empty jar."""
    # Arrange
    cookie_jar = HttpOnlyCookieJar()

    # Act
    cookie_dict = cookie_jar.get_dict()

    # Assert
    assert cookie_dict == {}


def test_clear():
    """Test clearing all cookies from jar."""
    # Arrange
    cookie_jar = HttpOnlyCookieJar()
    headers = CIMultiDict()
    headers.add("Set-Cookie", "JSESSIONID=abc123; Path=/ HttpOnly")
    headers.add("Set-Cookie", "snc=1234; Path=/ HttpOnly")
    cookie_jar.update_from_response_headers(headers)

    # Act
    cookie_jar.clear()

    # Assert
    assert len(cookie_jar._cookie_jar) == 0
    assert cookie_jar.get_dict() == {}
    assert cookie_jar.get_cookies() == []


def test_clear_empty_jar():
    """Test clearing already empty jar."""
    # Arrange
    cookie_jar = HttpOnlyCookieJar()

    # Act
    cookie_jar.clear()

    # Assert
    assert len(cookie_jar._cookie_jar) == 0


def test_cookie_attributes_preserved():
    """Test that cookie attributes are preserved when stored."""
    # Arrange
    cookie_jar = HttpOnlyCookieJar()
    headers = CIMultiDict()
    headers.add(
        "Set-Cookie", "JSESSIONID=abc123; Path=/; HttpOnly; Secure; Max-Age=3600"
    )

    # Act
    cookie_jar.update_from_response_headers(headers)

    # Assert
    morsel = cookie_jar._cookie_jar["JSESSIONID"]
    assert morsel.value == "abc123"
    assert morsel["path"] == "/"
    assert morsel["httponly"] is True
    assert morsel["secure"] is True
    assert morsel["max-age"] == "3600"


def test_cookie_jar_insert_httponly_cookies():
    """Test that only HttpOnly cookies are added to the cookie jar."""
    # Arrange
    cookie_jar = HttpOnlyCookieJar()
    headers = CIMultiDict()
    # JSessionID cookie with HttpOnly flag. This cookie should be added to the cookie jar.
    headers.add(
        "Set-Cookie", "JSESSIONID=abc123; Path=/; HttpOnly; Secure; Max-Age=3600"
    )
    # SNC cookie without HttpOnly. This cookie should not be added to the cookie jar
    headers.add("Set-Cookie", "SNC=abc123; Path=/; Secure; Max-Age=3600")

    # Act
    cookie_jar.update_from_response_headers(headers)

    # Assert
    assert len(cookie_jar._cookie_jar) == 1
    morsel = cookie_jar._cookie_jar["JSESSIONID"]
    assert morsel.value == "abc123"
    assert morsel["path"] == "/"
    assert morsel["httponly"] is True
    assert morsel["secure"] is True
    assert morsel["max-age"] == "3600"
