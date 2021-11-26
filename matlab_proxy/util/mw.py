# Copyright 2020-2021 The MathWorks, Inc.

import xml.etree.ElementTree as ET
import aiohttp, os, asyncio, select
from matlab_proxy.util.mwi_exceptions import (
    OnlineLicensingError,
    EntitlementError,
    NetworkLicensingError,
    MatlabError,
)
from matlab_proxy.util import mwi_logger
from matlab_proxy.default_configuration import config

logger = mwi_logger.get()


def __get_licensing_url():
    """Private function to query for the licensing URL

    Returns:
        String: Licensing URL
    """
    return f"{config['doc_url']}blob/main/MATLAB_Licensing_Info.md"


async def fetch_entitlements(mhlm_api_endpoint, access_token, matlab_release):
    """Asynchronously fetch entitlements from MHLM endpoint. Used when licensing using MHLM.

    Args:
        mhlm_api_endpoint (String): URL of the API endpoint for fetching entitlements from MHLM.
        access_token (String): An access token which was requested by the fetch_acces_token() method
        matlab_release (String): MATLAB Release version installed in the system.
        mhlm_context: Environment specific info sent to the mhlm_api_endpoint

    Raises:
        OnlineLicensingError: Raised when unable to receive proper response from MHLM servers.
        EntitlementError: Raised when no entitlements are present for a license.

    Returns:
        list: Representing a list of Dicts containing the id, label and license_number.
    """
    # Get entitlements for token
    async with aiohttp.ClientSession() as client_session:
        async with client_session.post(
            mhlm_api_endpoint,
            headers={"content-type": "application/x-www-form-urlencoded"},
            data=aiohttp.FormData(
                {
                    "token": access_token,
                    "release": matlab_release,
                    "coreProduct": "ML",
                    "context": "jupyter",
                    "excludeExpired": "true",
                }
            ),
        ) as res:

            if res.reason != "OK":
                raise OnlineLicensingError(
                    f"Communication with {mhlm_api_endpoint} failed ({res.status}). For more details, see {__get_licensing_url()}."
                )

            root = ET.fromstring(await res.text())
            entitlement_el = root.find("entitlements")

            if entitlement_el is None or len(entitlement_el) == 0:
                raise EntitlementError(
                    f"Your MathWorks account is not linked to a valid license for MATLAB {matlab_release}."
                )

            entitlements = entitlement_el.findall("entitlement")

            return [
                {
                    "id": entitlement.find("id").text,
                    "label": entitlement.find("label").text,
                    "license_number": entitlement.find("license_number").text,
                }
                for entitlement in entitlements
            ]


async def fetch_expand_token(mwa_api_endpoint, identity_token, source_id):
    """Asynchronously fetch tokens from MWA API after MHLM licensing is successful.

    Args:
        mwa_api_endpoint (String): URL of the MWA API endpoint.
        identity_token (String): Identity token received from MHLM servers by the front end.
        source_id (String): Source ID received from MHLM servers by the front end.

    Raises:
        OnlineLicensingError: When unable to contact MWA API endpoint.

    Returns:
        Dict: Containing User and License expiration details.
    """
    async with aiohttp.ClientSession() as client_session:
        async with client_session.post(
            f"{mwa_api_endpoint}/tokens",
            headers={
                "content-type": "application/x-www-form-urlencoded",
                "accept": "application/json",
                "X_MW_WS_callerId": "desktop-jupyter",
            },
            data=aiohttp.FormData(
                {
                    "tokenString": identity_token,
                    "tokenPolicyName": "R2",
                    "sourceId": source_id,
                }
            ),
        ) as res:

            if res.reason != "OK":
                raise OnlineLicensingError(
                    f"Communication with {mwa_api_endpoint} failed ({res.status}). For more details, see {__get_licensing_url()}."
                )

            data = await res.json()

            return {
                "expiry": data["expirationDate"],
                "first_name": data["referenceDetail"]["firstName"],
                "last_name": data["referenceDetail"]["lastName"],
                "display_name": data["referenceDetail"]["displayName"],
                "user_id": data["referenceDetail"]["userId"],
                "profile_id": data["referenceDetail"]["referenceId"],
            }


async def fetch_access_token(mwa_api_endpoint, identity_token, source_id):
    """Asynchronously fetch access token from MWA API endpoint.

    Args:
        mwa_api_endpoint (String): URL of the MWA API endpoint.
        identity_token (String): String representing unique identity
        source_id (String): []

    Raises:
        OnlineLicensingError: When unable to contact MWA API endpoint.

    Returns:
        Dict : Containing the Access token.
    """
    async with aiohttp.ClientSession() as client_session:
        async with client_session.post(
            f"{mwa_api_endpoint}/tokens/access",
            headers={
                "content-type": "application/x-www-form-urlencoded",
                "accept": "application/json",
                "X_MW_WS_callerId": "desktop-jupyter",
            },
            data=aiohttp.FormData(
                {
                    "tokenString": identity_token,
                    "type": "MWAS",
                    "sourceId": source_id,
                }
            ),
        ) as res:

            if res.reason != "OK":
                raise OnlineLicensingError(
                    f"Communication with {mwa_api_endpoint} failed ({res.status}). For more details, see {__get_licensing_url()}."
                )

            data = await res.json()

            return {
                "token": data["accessTokenString"],
            }


def range_matlab_connector_ports():
    """Generator of acceptable ports for MATLAB Connector.
        Allowed ports conform to the regex: [3,6]1[5-9][1-9][1-9]

    Yields:
        Int : Representing a Port number.
    """
    for p1 in (3, 6):
        p2 = 1
        for p3 in range(5, 10):
            for p4 in range(1, 10):
                for p5 in range(1, 10):
                    yield int(f"{p1}{p2}{p3}{p4}{p5}")


def parse_nlm_error(logs, conn_str):
    """Parses error logs and returns NLM specific errors

    Args:
        logs (List): An array containing error logs.
        conn_str (String): The connection string of NLM.

    Returns:
        List: Containing NLM specific errors.
    """
    nlm_logs = []
    start = False
    for log in logs:
        if start is False:
            if "License checkout failed" in log:
                start = True
                nlm_logs.append(log)
        else:
            if "Diagnostic Information" in log:
                return NetworkLicensingError(
                    f"License checkout from {conn_str} failed. For more details, see {__get_licensing_url()}.",
                    logs=nlm_logs,
                )
            nlm_logs.append(log)
    return None


def parse_mhlm_error(logs):
    """Parses error logs and returns MHLM specific errors

    Args:
        logs (List): An array containing error logs.

    Returns:
        List: Containing MHLM specific errors.
    """
    mhlm_logs = None
    start = False
    for log in logs:
        if "License Manager Error" in log:
            start = True
            mhlm_logs = [log]

        if start is True:
            mhlm_logs.append(log)

    if mhlm_logs is not None:
        return OnlineLicensingError(
            f"Usage of MathWorks Online Licensing failed. For more details, see {__get_licensing_url()}.",
            logs=mhlm_logs,
        )
    return None


def parse_other_error(logs):
    """Returns a MATLAB specific error.

    Args:
        logs (List): An array containing error logs.

    Returns:
        MatlabError: An instance of MatlabError class with logs.
    """
    return MatlabError(
        "MATLAB returned an unexpected error. For more details, see the log below.",
        logs=logs,
    )


async def create_xvfb_process(xvfb_cmd, pipe, matlab_env={}):
    """Creates the Xvfb process.

    The Xvfb process is run with '-displayfd' flag set. This makes Xvfb choose an available
    display number and write it into the provided write descriptor. ie: pipe[1]

    We read this display number from the read descriptor.
    For this, we have 2 things to consider:
        1. How many bytes to read from the read descriptor. This is handled by the variable number_of_bytes.

        2. For how long to read from the read descriptor. We wait for atmost 10 seconds for Xvfb to write
           the display number using the 'select' package.


    Args:
        xvfb_cmd (List): A list containing the command to run the Xvfb process
        pipe (List): A list containing a pair of file descriptor.
        matlab_env (Dict): A Dict containing environment variables within which the Xvfb process is created.

    Returns:
        List: Containing the Xvfb process object, and display number on which Xvfb process has started.
    """

    # Creates subprocess asynchronously with environment variables defined in matlab_env
    # Pipe errors, if any, to the process object instead of stdout.
    xvfb = await asyncio.create_subprocess_exec(
        *xvfb_cmd, close_fds=False, env=matlab_env, stderr=asyncio.subprocess.PIPE
    )

    read_descriptor, write_descriptor = pipe
    number_of_bytes = 200

    logger.debug("Waiting for XVFB process to initialize and provide Display Number")
    # Waits upto 10 seconds for the read_descriptor to be ready.
    ready_descriptors, _, _ = select.select([read_descriptor], [], [], 10)

    # If read_descriptor is in ready_descriptors, read from it.
    if read_descriptor in ready_descriptors:
        logger.debug("Reading display number from the read descriptor.")
        line = os.read(read_descriptor, number_of_bytes).decode("utf-8")
        # Xvfb process writes the display number and adds a new line character ('\n') at the end. Removing it with .strip()
        display_port = line.strip()

    else:
        # Check for errors and raise exception.
        error = ""
        while not xvfb.stderr.at_eof():
            line = await xvfb.stderr.readline()
            error += line.decode("utf-8")

        await xvfb.wait()
        raise Exception(f"Unable to start the Xvfb process: \n {error}")

    # Close the read and write descriptors.
    os.close(read_descriptor)
    os.close(write_descriptor)

    return xvfb, display_port
