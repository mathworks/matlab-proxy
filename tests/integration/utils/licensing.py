# Copyright 2024 The MathWorks, Inc.
import os
import logging
from playwright.sync_api import Page, Error, sync_playwright, expect
from tests.integration.utils import integration_tests_utils as utils
from tests.utils.logging_util import create_integ_test_logger

# Configure logging
_logger = create_integ_test_logger(__name__)

TIMEOUTS = {
    # Time in milliseconds
    "MHLM_VISIBLE": 60 * 1000,
    "TEXTBOX_VISIBLE": 5 * 1000,
    "MATLAB_STARTS": 3 * 60 * 1000,
}


POLL_INTERVAL = 1000


def _get_matlab_proxy_url():
    # import integration_tests_utils as utils
    import matlab_proxy.util

    mwi_app_port = utils.get_random_free_port()
    mwi_base_url = "/matlab-test"

    input_env = {
        "MWI_APP_PORT": mwi_app_port,
        "MWI_BASE_URL": mwi_base_url,
    }

    loop = matlab_proxy.util.get_event_loop()
    # Run matlab-proxy in the background in an event loop
    proc = loop.run_until_complete(utils.start_matlab_proxy_app(input_env=input_env))

    utils.wait_server_info_ready(mwi_app_port)
    matlab_proxy_url = utils.get_connection_string(mwi_app_port)
    return matlab_proxy_url, proc, loop


def license_matlab_proxy():
    import requests

    matlab_proxy_url, proc, loop = _get_matlab_proxy_url()

    utils.poll_web_service(
        matlab_proxy_url,
        step=5,
        timeout=120,
        ignore_exceptions=(
            requests.exceptions.ConnectionError,
            requests.exceptions.SSLError,
        ),
    )

    licensing_with_online_licensing(matlab_proxy_url)
    utils.wait_matlab_proxy_ready(matlab_proxy_url)
    proc.terminate()
    loop.run_until_complete(proc.wait())


def licensing_with_online_licensing(matlab_proxy_url):
    """
    Use Playwright UI automation to license matlab-proxy.
    Uses TEST_USERNAME and TEST_PASSWORD from environment variables.

    Args:
        matlab_proxy_url (string): URL to access matlab-proxy
    """
    from playwright.sync_api import sync_playwright, expect

    # These are MathWorks Account credentials to license MATLAB
    # Throws 'KeyError' if the following environment variables are not set
    TEST_USERNAME = os.environ["TEST_USERNAME"]
    TEST_PASSWORD = os.environ["TEST_PASSWORD"]

    playwright, browser, page = _launch_browser()
    page.goto(matlab_proxy_url)

    # Find the MHLM licensing window in matlab-proxy
    login_iframe = _wait_for_login_iframe(page)

    # Fills in the username textbox
    email_text_box = _fill_in_username(TEST_USERNAME, login_iframe)
    email_text_box.press("Enter")

    # Fills in the password textbox
    password_text_box = _fill_in_password(TEST_PASSWORD, login_iframe)
    password_text_box.press("Enter")

    # Verifies if licensing is successful by checking the status information
    _verify_licensing(page)
    _close_resources(playwright, browser)


def _verify_licensing(page):
    status_info = page.get_by_text("Status Information")
    expect(
        status_info,
        "Verify if Licensing is successful. This might fail if incorrect credentials are provided",
    ).to_be_visible(timeout=TIMEOUTS["MHLM_VISIBLE"])


def _wait_for_login_iframe(matlab_proxy_page):
    """Waits for the MHLM/Online Licensing form to appear."""
    mhlm_div = matlab_proxy_page.locator("#MHLM")
    expect(
        mhlm_div,
        "Wait for MHLM licensing window to appear. This might fail if the MATLAB is already licensed",
    ).to_be_visible(timeout=TIMEOUTS["MHLM_VISIBLE"])

    # The login iframe is present within the MHLM Div
    login_iframe = mhlm_div.frame_locator("#loginframe")
    return login_iframe


def _launch_browser(headless: bool = True) -> tuple:
    """Launches the browser and returns the browser and page objects."""
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=headless)
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()
    return playwright, browser, page


def _close_resources(playwright, browser):
    """Closes the browser and playwright resources properly."""
    browser.close()
    playwright.stop()


def _fill_in_username(username, login_iframe):
    """Inputs the provided username string into the MHLM login form."""
    email_text_box = login_iframe.locator("#userId")
    expect(
        email_text_box,
        "Wait for email ID textbox to appear",
    ).to_be_visible(timeout=TIMEOUTS["TEXTBOX_VISIBLE"])
    email_text_box.fill(username)
    return email_text_box


def _fill_in_password(password, login_iframe):
    """Inputs the provided password string into the MHLM login form."""
    password_text_box = login_iframe.locator("#password")
    expect(password_text_box, "Wait for password textbox to appear").to_be_visible(
        timeout=TIMEOUTS["TEXTBOX_VISIBLE"]
    )
    password_text_box.fill(password)
    return password_text_box
