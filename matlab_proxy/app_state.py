# Copyright (c) 2020-2022 The MathWorks, Inc.

import asyncio
import errno
import json
import logging
import os
import socket
import sys
import time
from collections import deque
from datetime import datetime, timedelta, timezone

import aiohttp

from matlab_proxy import util
from matlab_proxy.util import mw, mwi, system, windows
from matlab_proxy.util.mwi import environment_variables as mwi_env
from matlab_proxy.util.mwi import token_auth
from matlab_proxy.util.mwi.exceptions import (
    EmbeddedConnectorError,
    EntitlementError,
    InternalError,
    LicensingError,
    MatlabError,
    MatlabInstallError,
    OnlineLicensingError,
    XvfbError,
    log_error,
)

logger = mwi.logger.get()


class AppState:
    """A Class which represents the state of the App.
    This class handles state of MATLAB, MATLAB Licensing and Xvfb.
    """

    def __init__(self, settings):
        """Parameterized constructor for the AppState class.
        Initializes member variables and checks for an existing MATLAB installation.

        Args:
            settings (Dict): Represents the settings required for managing MATLAB, Licensing and Xvfb.
        """
        self.settings = settings
        self.processes = {"matlab": None, "xvfb": None}

        # The port on which MATLAB(launched by this matlab-proxy process) starts on.
        self.matlab_port = None

        # The directory in which the instance of MATLAB (launched by this matlab-proxy process) will write logs to.
        self.mwi_logs_dir = None

        # Dictionary of all files used to manage the MATLAB session.
        self.matlab_session_files = {
            # The file created by this instance of matlab-proxy to signal to other matlab-proxy processes
            # that this self.matlab_port will be used by this instance.
            "mwi_proxy_lock_file": None,
            # The file created and written by MATLAB's Embedded connector to signal readiness.
            "matlab_ready_file": None,
        }

        # Dictionary of all files used to manage the server session.
        self.mwi_server_session_files = {
            # This file will contain the access URL to the server, this will include any tokens required by the server for access.
            "mwi_server_info_file": None,
        }

        self.licensing = None
        self.tasks = {}
        self.logs = {
            "matlab": deque(maxlen=200),
        }
        self.error = None
        # Start in an error state if MATLAB is not present
        if not self.is_matlab_present():
            self.error = MatlabInstallError("'matlab' executable not found in PATH")
            logger.error("'matlab' executable not found in PATH")
            return

    def __get_cached_licensing_file(self):
        """Get the cached licensing file

        Returns:
            Path : Path object to cached licensing file
        """
        return self.settings["matlab_config_file"]

    def __delete_cached_licensing_file(self):
        """Deletes the cached licensing file"""
        try:
            logger.info(f"Deleting any cached licensing files!")
            os.remove(self.__get_cached_licensing_file())
        except FileNotFoundError:
            # The file being absent is acceptable.
            pass

    def __reset_and_delete_cached_licensing(self):
        """Reset licensing variable of the class and removes the cached licensing file."""
        logger.info(f"Resetting cached licensing information...")
        self.licensing = None
        self.__delete_cached_licensing_file()

    async def __update_and_persist_licensing(self):
        """Update entitlements from mhlm servers and persist licensing

        Returns:
            Boolean: True when entitlements were updated and persisted successfully. False otherwise.
        """
        successful_update = await self.update_entitlements()
        if successful_update:
            self.persist_licensing()
        else:
            self.__reset_and_delete_cached_licensing()
        return successful_update

    async def init_licensing(self):
        """Initialize licensing from environment variable or cached file.

        Greater precedence is given to value specified in environment variable MLM_LICENSE_FILE
            If specified, this function will delete previously cached licensing information.
            This enforces a clear understanding of what was used to initialize licensing.
            The contents of the environment variable are NEVER cached.
        """

        # Default value
        self.licensing = None

        # NLM Connection String set in environment
        if self.settings["nlm_conn_str"] is not None:
            nlm_licensing_str = self.settings["nlm_conn_str"]
            logger.debug(f"Found NLM:[{nlm_licensing_str}] set in environment")
            logger.debug(f"Using NLM string to connect ... ")
            self.licensing = {
                "type": "nlm",
                "conn_str": nlm_licensing_str,
            }
            self.__delete_cached_licensing_file()

        # If NLM connection string is not present, then look for persistent LNU info
        elif self.__get_cached_licensing_file().exists():
            with open(self.__get_cached_licensing_file(), "r") as f:
                logger.debug("Found cached licensing information...")
                try:
                    # Load can throw if the file is empty for some reason.
                    licensing = json.loads(f.read())
                    if licensing["type"] == "nlm":
                        # Note: Only NLM settings entered in browser were cached.
                        self.licensing = {
                            "type": "nlm",
                            "conn_str": licensing["conn_str"],
                        }
                    elif licensing["type"] == "mhlm":
                        self.licensing = {
                            "type": "mhlm",
                            "identity_token": licensing["identity_token"],
                            "source_id": licensing["source_id"],
                            "expiry": licensing["expiry"],
                            "email_addr": licensing["email_addr"],
                            "first_name": licensing["first_name"],
                            "last_name": licensing["last_name"],
                            "display_name": licensing["display_name"],
                            "user_id": licensing["user_id"],
                            "profile_id": licensing["profile_id"],
                            "entitlements": [],
                            "entitlement_id": licensing.get("entitlement_id"),
                        }

                        expiry_window = datetime.strptime(
                            self.licensing["expiry"], "%Y-%m-%dT%H:%M:%S.%f%z"
                        ) - timedelta(hours=1)

                        if expiry_window > datetime.now(timezone.utc):
                            successful_update = (
                                await self.__update_and_persist_licensing()
                            )
                            if successful_update:
                                logger.debug("Successful re-use of cached information.")
                        else:
                            self.__reset_and_delete_cached_licensing()
                    else:
                        # Somethings wrong, licensing is neither NLM or MHLM
                        self.__reset_and_delete_cached_licensing()
                except Exception as e:
                    self.__reset_and_delete_cached_licensing()

    async def get_matlab_state(self):
        """Determine the state of MATLAB to be down/starting/up.

        Returns:
            String: Status of MATLAB. Returns either up, down or starting.
        """

        matlab = self.processes["matlab"]
        xvfb = self.processes["xvfb"]

        if system.is_linux():
            if xvfb is None or xvfb.returncode is not None:
                return "down"

            if matlab is None or matlab.returncode is not None:
                return "down"

        elif system.is_mac():
            if matlab is None or matlab.returncode is not None:
                return "down"
        else:
            if matlab is None or not matlab.is_running():
                return "down"

        # If execution reaches this else block, it implies that:
        # 1) MATLAB process has started.
        # 2) Embedded connector has not started yet.

        # So, even if the embedded connector's status is 'down', we'll
        # return as 'starting' because the MATLAB process itself has been created
        # and matlab-proxy is waiting for the embedded connector to start serving content.
        status = await mwi.embedded_connector.request.get_state(
            self.settings["mwi_server_url"]
        )
        if status == "down":
            status = "starting"
            # Update time stamp when MATLAB state is "starting". Only for Windows systems
            # The variable self.starting_state_timestamp is created by the matlab_stderr_reader() task
            # and is updated here.
            if not system.is_posix() and not self.starting_state_timestamp:
                self.starting_state_timestamp = time.time()

        return status

    async def set_licensing_nlm(self, conn_str):
        """Set the licensing type to NLM and the connection string."""

        # TODO Validate connection string
        self.licensing = {"type": "nlm", "conn_str": conn_str}
        self.persist_licensing()

    async def set_licensing_mhlm(
        self,
        identity_token,
        email_addr,
        source_id,
        entitlements=[],
        entitlement_id=None,
    ):
        """Set the licensing type to MHLM and the details.

        Args:
            identity_token (String): Identity token of the user.
            email_addr (String): Email address of the user.
            source_id (String): Unique random string generated for the user.
            entitlements (list, optional): Eligible Entitlements of the user. Defaults to [].
            entitlement_id (String, optional): ID of an entitlement. Defaults to None.
        """

        try:
            token_data = await mw.fetch_expand_token(
                self.settings["mwa_api_endpoint"], identity_token, source_id
            )

            self.licensing = {
                "type": "mhlm",
                "identity_token": identity_token,
                "source_id": source_id,
                "expiry": token_data["expiry"],
                "email_addr": email_addr,
                "first_name": token_data["first_name"],
                "last_name": token_data["last_name"],
                "display_name": token_data["display_name"],
                "user_id": token_data["user_id"],
                "profile_id": token_data["profile_id"],
                "entitlements": entitlements,
                "entitlement_id": entitlement_id,
            }

            successful_update = await self.__update_and_persist_licensing()
            if successful_update:
                logger.debug("Login successful, persisting login information.")

        except OnlineLicensingError as e:
            self.error = e
            self.licensing = {
                "type": "mhlm",
                "email_addr": email_addr,
            }
            log_error(logger, e)

    def unset_licensing(self):
        """Unset the licensing."""

        self.licensing = None

        # If the error was due to licensing, clear it
        if isinstance(self.error, LicensingError):
            self.error = None

    def is_licensed(self):
        """Is MATLAB licensing configured?

        Returns:
            Boolean: True if MATLAB is Licensed. False otherwise.
        """

        if self.licensing is not None:
            if self.licensing["type"] == "nlm":
                if self.licensing["conn_str"] is not None:
                    return True
            elif self.licensing["type"] == "mhlm":
                if (
                    self.licensing.get("identity_token") is not None
                    and self.licensing.get("source_id") is not None
                    and self.licensing.get("expiry") is not None
                    and self.licensing.get("entitlement_id") is not None
                ):
                    return True
        return False

    def is_matlab_present(self):
        """Is MATLAB install accessible?

        Returns:
            Boolean: True if MATLAB is present in the system. False otherwise.
        """

        return self.settings["matlab_path"] is not None

    async def update_entitlements(self):
        """Speaks to MW and updates MHLM entitlements

        Raises:
            InternalError: When licensing is None or when licensing type is not MHLM.

        Returns:
            Boolean: True if update was successful
        """
        if self.licensing is None or self.licensing["type"] != "mhlm":
            raise InternalError(
                "MHLM licensing must be configured to update entitlements!"
            )

        try:
            # Fetch an access token
            access_token_data = await mw.fetch_access_token(
                self.settings["mwa_api_endpoint"],
                self.licensing["identity_token"],
                self.licensing["source_id"],
            )

            # Fetch entitlements
            entitlements = await mw.fetch_entitlements(
                self.settings["mhlm_api_endpoint"],
                access_token_data["token"],
                self.settings["matlab_version"],
            )

        except OnlineLicensingError as e:
            self.error = e
            log_error(logger, e)
            return False
        except EntitlementError as e:
            self.error = e
            log_error(logger, e)
            self.licensing["identity_token"] = None
            self.licensing["source_id"] = None
            self.licensing["expiry"] = None
            self.licensing["first_name"] = None
            self.licensing["last_name"] = None
            self.licensing["display_name"] = None
            self.licensing["user_id"] = None
            self.licensing["profile_id"] = None
            self.licensing["entitlements"] = []
            self.licensing["entitlement_id"] = None
            return False

        self.licensing["entitlements"] = entitlements

        # If there is only one non-expired entitlement, set it as active
        # TODO Also, for now, set the first entitlement as active if there are multiple
        self.licensing["entitlement_id"] = entitlements[0]["id"]

        # Successful update
        return True

    def persist_licensing(self):
        """Saves licensing information to file"""
        if self.licensing is None:
            self.__delete_cached_licensing_file()

        elif self.licensing["type"] in ["mhlm", "nlm"]:
            logger.debug("Saving licensing information...")
            cached_licensing_file = self.__get_cached_licensing_file()
            cached_licensing_file.parent.mkdir(parents=True, exist_ok=True)
            with open(cached_licensing_file, "w") as f:
                f.write(json.dumps(self.licensing))

    def prepare_lock_files_for_MATLAB_launch(self):
        """Finds and reserves a free port for MATLAB Embedded Connector in the allowed range.
        Creates the lock file to prevent any other matlab-proxy process to use the reserved port of this
        process.

        Raises:
            e: socket.error if the exception raised is other than port already occupied.
        """

        # NOTE It is not guranteed that the port will remain free!
        # FIXME Because of https://github.com/http-party/node-http-proxy/issues/1342 the
        # node application in development mode always uses port 31515 to bypass the
        # reverse proxy. Once this is addressed, remove this special case.
        if (
            mwi_env.is_development_mode_enabled()
            and not mwi_env.is_testing_mode_enabled()
        ):
            return 31515
        else:
            # TODO If MATLAB Connector is enhanced to allow any port, then the
            # following can be used to get an unused port instead of the for loop and
            # try-except.
            # s.bind(("", 0))
            # self.matlab_port = s.getsockname()[1]

            for port in mw.range_matlab_connector_ports():
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.bind(("", port))

                    mwi_logs_root_dir = self.settings["mwi_logs_root_dir"]

                    # The mwi_proxy.lock file indicates to any other matlab-proxy processes
                    # that this self.matlab_port number is taken up by this process.
                    mwi_proxy_lock_file = mwi_logs_root_dir / (
                        self.settings["mwi_proxy_lock_file_name"] + "." + str(port)
                    )

                    # Check if the mwi_proxy_lock_file exists.
                    # Implies there was a competing matlab-proxy process which found the same port before this process
                    if mwi_proxy_lock_file.exists():
                        logger.debug(
                            f"Skipping port number {port} for MATLAB as lock file already exists at {mwi_proxy_lock_file}"
                        )
                        s.close()

                    else:
                        # Use the app_port number to identify the server as that is user visible
                        mwi_logs_dir = mwi_logs_root_dir / str(
                            self.settings["app_port"]
                        )

                        # Create a folder to hold the matlab_ready_file that will be created by MATLAB to signal readiness.
                        # This is the same folder to which MATLAB will write logs to.
                        mwi_logs_dir.mkdir(parents=True, exist_ok=True)

                        # Create the lock file first to minimize the critical section.
                        mwi_proxy_lock_file.touch()
                        logger.info(
                            f"Communicating with MATLAB on port:{port}, lock file: {mwi_proxy_lock_file}"
                        )

                        # Created by MATLAB when it is ready to service requests.
                        matlab_ready_file = mwi_logs_dir / "connector.securePort"

                        # Update member variables of AppState class
                        # Store the port number on which MATLAB will be launched for this matlab-proxy process.
                        self.matlab_port = port
                        self.mwi_logs_dir = mwi_logs_dir
                        self.matlab_session_files[
                            "mwi_proxy_lock_file"
                        ] = mwi_proxy_lock_file
                        self.matlab_session_files[
                            "matlab_ready_file"
                        ] = matlab_ready_file
                        s.close()

                        logger.debug(
                            f"matlab_session_files:{self.matlab_session_files}"
                        )
                        return

                # For windows container's (when testing in github workflows) PermissionError and in linux, OSError is
                # thrown when trying to bind a used port from a previous test instead of the expected socket.error
                except (OSError, PermissionError) as e:
                    pass

                except socket.error as e:
                    if e.errno != errno.EADDRINUSE:
                        raise e

    def create_server_info_file(self):
        mwi_logs_root_dir = self.settings["mwi_logs_root_dir"]
        # Use the app_port number to identify the server as that is user visible
        mwi_logs_dir = mwi_logs_root_dir / str(self.settings["app_port"])
        # Create a folder to hold the matlab_ready_file that will be created by MATLAB to signal readiness.
        # This is the same folder to which MATLAB will write logs to.
        mwi_logs_dir.mkdir(parents=True, exist_ok=True)

        mwi_server_info_file = mwi_logs_dir / "mwi_server.info"
        mwi_auth_token_str = token_auth.get_mwi_auth_token_access_str(self.settings)
        with open(mwi_server_info_file, "w") as fh:
            fh.write(self.settings["mwi_server_url"] + mwi_auth_token_str + "\n")
        self.mwi_server_session_files["mwi_server_info_file"] = mwi_server_info_file
        logger.debug(f"Server info stored into: {mwi_server_info_file}")

        # By default mwi_server_url usually points to 0.0.0.0 as the hostname, but this does not work well
        # on some browsers. Specifically on Safari (MacOS)
        logger.info(
            util.prettify(
                boundary_filler="=",
                text_arr=[
                    f"MATLAB can be accessed at:",
                    self.settings["mwi_server_url"].replace("0.0.0.0", "localhost")
                    + mwi_auth_token_str,
                ],
            )
        )

    def clean_up_mwi_server_session(self):
        # Clean up mwi_server_session_files
        try:
            for session_file in self.mwi_server_session_files.items():
                if session_file[1] is not None:
                    logger.info(f"Deleting:{session_file[1]}")
                    session_file[1].unlink()
        except FileNotFoundError:
            # Files may not exist if cleanup is called before they are created
            pass

    async def __setup_env_for_matlab(self) -> dict:
        """Configure the environment variables required for launching MATLAB by matlab-proxy.

        Returns:
            [dict]: Containing keys as the Env variable names and values are its corresponding values.
        """
        matlab_env = os.environ.copy()
        # Env setup related to licensing
        if self.licensing["type"] == "mhlm":
            try:
                # Request an access token
                access_token_data = await mw.fetch_access_token(
                    self.settings["mwa_api_endpoint"],
                    self.licensing["identity_token"],
                    self.licensing["source_id"],
                )
                matlab_env["MLM_WEB_LICENSE"] = "true"
                matlab_env["MLM_WEB_USER_CRED"] = access_token_data["token"]
                matlab_env["MLM_WEB_ID"] = self.licensing["entitlement_id"]
                matlab_env["MW_LOGIN_EMAIL_ADDRESS"] = self.licensing["email_addr"]
                matlab_env["MW_LOGIN_FIRST_NAME"] = self.licensing["first_name"]
                matlab_env["MW_LOGIN_LAST_NAME"] = self.licensing["last_name"]
                matlab_env["MW_LOGIN_DISPLAY_NAME"] = self.licensing["display_name"]
                matlab_env["MW_LOGIN_USER_ID"] = self.licensing["user_id"]
                matlab_env["MW_LOGIN_PROFILE_ID"] = self.licensing["profile_id"]

                matlab_env["MHLM_CONTEXT"] = (
                    "MATLAB_JAVASCRIPT_DESKTOP"
                    if os.getenv(mwi_env.get_env_name_mhlm_context()) is None
                    else os.getenv(mwi_env.get_env_name_mhlm_context())
                )
            except OnlineLicensingError as e:
                raise e

        elif self.licensing["type"] == "nlm":
            matlab_env["MLM_LICENSE_FILE"] = self.licensing["conn_str"]

        # Env setup related to MATLAB
        matlab_env["MW_CRASH_MODE"] = "native"
        matlab_env["MATLAB_WORKER_CONFIG_ENABLE_LOCAL_PARCLUSTER"] = "true"
        matlab_env["PCT_ENABLED"] = "true"
        matlab_env["HTTP_MATLAB_CLIENT_GATEWAY_PUBLIC_PORT"] = "1"
        matlab_env["MW_DOCROOT"] = os.path.join("ui", "webgui", "src")
        matlab_env["MWAPIKEY"] = self.settings["mwapikey"]

        # For r2020b, r2021a
        matlab_env["MW_CD_ANYWHERE_ENABLED"] = "true"
        # For >= r2021b
        matlab_env["MW_CD_ANYWHERE_DISABLED"] = "false"

        # DDUX info for MATLAB
        matlab_env["MW_CONTEXT_TAGS"] = self.settings.get("mw_context_tags")

        if system.is_linux():
            # Adding DISPLAY key which is only available after starting Xvfb successfully.
            matlab_env["DISPLAY"] = self.settings["matlab_display"]

        # MW_CONNECTOR_SECURE_PORT and MATLAB_LOG_DIR keys to matlab_env as they are available after
        # reserving port and preparing lockfiles for MATLAB
        matlab_env["MW_CONNECTOR_SECURE_PORT"] = str(self.matlab_port)

        # The matlab ready file is written into this location(self.mwi_logs_dir) by MATLAB
        # The mwi_logs_dir is where MATLAB will write any subsequent logs
        matlab_env["MATLAB_LOG_DIR"] = str(self.mwi_logs_dir)

        # Env setup related to logging
        # Very verbose logging in debug mode
        if logger.isEnabledFor(logging.getLevelName("DEBUG")):
            matlab_env["MW_DIAGNOSTIC_DEST"] = "stdout"
            matlab_env[
                "MW_DIAGNOSTIC_SPEC"
            ] = "connector::http::server=all;connector::lifecycle=all"

        # TODO Introduce a warmup flag to enable this?
        # matlab_env["CONNECTOR_CONFIGURABLE_WARMUP_TASKS"] = "warmup_hgweb"
        # matlab_env["CONNECTOR_WARMUP"] = "true"

        return matlab_env

    async def __start_xvfb_process(self):
        """Private method to start the xvfb process. Will set appropriate
        errors to self.error and return None when any exceptions are raised.

        Returns:
            (asyncio.subprocess.Process) : When Xvfb process is created successfully else None.
        """

        # Start Xvfb process and update display number in settings
        create_xvfb_cmd = self.settings["create_xvfb_cmd"]
        xvfb_cmd, dpipe = create_xvfb_cmd()

        try:
            xvfb, display_port = await mw.create_xvfb_process(xvfb_cmd, dpipe)
            self.settings["matlab_display"] = ":" + str(display_port)

            logger.debug(f"Started Xvfb with PID={xvfb.pid} on DISPLAY={display_port}")

            return xvfb

        # If something went wrong ie. exception is raised in launching Xvfb process, capture error for logging
        # and for showing the error on the frontend.

        # FileNotFoundError: is thrown if Xvfb is not found on System Path.
        # XvfbError: is thrown if something went wrong when launching Xvfb process.
        except (FileNotFoundError, XvfbError) as err:
            self.error = XvfbError(
                """Unable to start the Xvfb process. Ensure Xvfb is installed and is available on the System Path. See https://github.com/mathworks/matlab-proxy#requirements for information on Xvfb"""
            )
            # Log the error on the console.
            log_error(logger, self.error)

        # If something else went wrong log the error and exit
        except Exception as err:
            self.error = err
            # Log the error on the console.
            log_error(logger, err)

        return None

    async def __start_matlab_process(self, matlab_env):
        """Starts the matlab process depending on the operating system. If an exception is raised,
        will update self.error and return None else will return the process object.

        Returns:
            (asyncio.subprocess.Process | psutil.Process): If process creation is successful, else return None.
        """
        if system.is_posix():
            import pty

            _, slave = pty.openpty()

            # In posix systems 'matlab' variable is of type asyncio.subprocess.Process()
            matlab = await asyncio.create_subprocess_exec(
                *self.settings["matlab_cmd"],
                env=matlab_env,
                stdin=slave,
                stderr=asyncio.subprocess.PIPE,
            )

            return matlab

        else:
            try:
                # In Windows systems 'matlab' variable is of type psutil.Process()
                matlab = await windows.start_matlab(
                    self.settings["matlab_cmd"], matlab_env
                )

                return matlab

            except Exception as err:
                self.error = err
                log_error(logger, err)

        # If something went wrong in starting matlab, return None
        return None

    async def start_matlab(self, restart_matlab=False):
        """Start MATLAB.

        Args:
            restart_matlab (bool, optional): Whether to restart MATLAB. Defaults to False.

        Raises:
            Exception: When MATLAB is already running and restart is False.
            Exception: When MATLAB is not licensed.
        """

        # FIXME
        if await self.get_matlab_state() != "down" and restart_matlab is False:
            raise Exception("MATLAB already running/starting!")

        # FIXME
        if not self.is_licensed():
            raise Exception("MATLAB is not licensed!")

        if not self.is_matlab_present():
            self.error = MatlabInstallError("'matlab' executable not found in PATH")
            logger.error("'matlab' executable not found in PATH")
            self.logs["matlab"].clear()
            return

        # Ensure that previous processes are stopped
        await self.stop_matlab()

        # Clear MATLAB errors and logging
        self.error = None
        self.logs["matlab"].clear()

        # Start Xvfb process if in a posix system
        if system.is_linux():
            xvfb = await self.__start_xvfb_process()

            # xvfb variable would be None if creation of the process failed.
            # Halt MATLAB process startup by returning early.
            if xvfb is None:
                return

            self.processes["xvfb"] = xvfb

        try:
            # Finds and reserves a free port, then prepare lock files for the MATLAB process.
            self.prepare_lock_files_for_MATLAB_launch()

            # Configure the environment MATLAB needs to start
            matlab_env = await self.__setup_env_for_matlab()

            logger.debug(
                "Prepared lock files and configured the environment for MATLAB startup"
            )

        # If there's something wrong with setting up lock files or env setup for starting matlab, capture the error for logging
        # and to pass to the front-end. Halt MATLAB process startup by returning early
        except Exception as err:
            self.error = err
            log_error(logger, err)
            # stop_matlab() does the teardown work by removing any residual files and processes created till now
            # which is Xvfb process creation and preparing lock files for the MATLAB process.
            await self.stop_matlab()
            return

        # Start MATLAB Process
        logger.debug(f"Starting MATLAB on port {self.matlab_port}")

        matlab = await self.__start_matlab_process(matlab_env)

        # matlab variable would be None if creation of the process failed.
        if matlab is None:
            # call self.stop_matlab().This does the teardown work by removing any residual files and processes created till now.
            # Force quitting matlab as something went wrong in starting the matlab process itself.
            await self.stop_matlab(force_quit=True)
            return

        logger.debug(f"Started MATLAB (PID={matlab.pid})")
        self.processes["matlab"] = matlab

        async def matlab_stderr_reader():
            matlab = self.processes["matlab"]
            logger.info("matlab_stderr_reader() task: Starting task...")

            if system.is_posix():
                while not matlab.stderr.at_eof():
                    logger.debug(
                        "matlab_stderr_reader() task: Waiting to read data from stderr pipe..."
                    )
                    line = await matlab.stderr.readline()
                    if line is None:
                        logger.debug(
                            "matlab_stderr_reader() task: Received data from stderr pipe appending to logs..."
                        )
                        break
                    self.logs["matlab"].append(line)
                await self.handle_matlab_output()

            else:
                # starting state time stamp.
                # This is used to keep track of when the MATLAB process' state
                # has changed to 'starting'.
                # If there is some problem with lauching the Embedded Connector,
                # MATLAB will continue to be in a 'starting' state indefinitely.
                # Used only on Windows system.
                self.starting_state_timestamp = None

                # The maximum amount of time in seconds the Embedded Connector can take
                # for lauching, before the matlab-proxy server concludes that something is wrong.
                self.embedded_connector_max_starting_duration = 120

                # In Windows systems, errors are raised as UI windows and cannot be captured programmatically.
                # So, check for how long the Embedded Connector is not up and then raise a generic error.
                while True:
                    # If the Embedded connector is up, everything is ok, sleep for 10 seconds.
                    if await self.get_matlab_state() == "up":
                        logger.debug(
                            "matlab_stderr_reader() task: MATLAB is up, not checking for any errors. Sleeping for 10 seconds..."
                        )
                        # Setting starting_state_timestamp to None
                        # If something goes wrong or MATLAB process is restarted
                        # self.get_matlab_state() will update the variable to the appropriate timestamp.
                        self.starting_state_timestamp = None
                        await asyncio.sleep(10)
                        continue

                    # If starting_state_timestamp is not yet set, it means MATLAB process has
                    # not yet started. So, wait for MATLAB to start and for starting_state_timestamp to be set.
                    if not self.starting_state_timestamp:
                        await asyncio.sleep(1)
                        continue

                    time_diff = time.time() - self.starting_state_timestamp
                    if time_diff > self.embedded_connector_max_starting_duration:
                        # If execution reaches here, it means that the MATLAB has been up but the Embedded Connector is not
                        # responding for more than embedded_connector_max_starting_duration seconds. So, create/raise a generic error
                        logger.error(
                            f"matlab_stderr_reader() task: MATLAB has been in a 'starting' state for more than {self.embedded_connector_max_starting_duration}!"
                        )
                        self.error = MatlabError(
                            f"MATLAB has been in a starting state for more than {self.embedded_connector_max_starting_duration} seconds. Use Windows Remote Desktop to check for any errors"
                        )

                    else:
                        logger.debug(
                            f"matlab_stderr_reader() task: MATLAB has been in a 'starting' state for {time_diff} seconds. Sleeping for 1 second..."
                        )
                        await asyncio.sleep(1)

        loop = util.get_event_loop()

        self.tasks["matlab_stderr_reader"] = loop.create_task(matlab_stderr_reader())

    """
    async def __send_terminate_integration_request(self):
        Private method to programmatically shutdown the matlab-proxy server.
        Sends a HTTP request to the server to shut itself down gracefully.

        # Clean up session files which determine various states of the server &/ MATLAB.
        # Do this first as stopping MATLAB/Xvfb take longer and may fail
        try:
            for session_file in self.matlab_session_files.items():
                if session_file[1] is not None:
                    logger.info(f"Deleting:{session_file[1]}")
                    session_file[1].unlink()
        except FileNotFoundError:
            # Files won't exist when stop_matlab is called for the first time.
            pass

        # Cancel the asyncio task which reads MATLAB process' stderr
        if "matlab_stderr_reader" in self.tasks:
            try:
                self.tasks["matlab_stderr_reader"].cancel()
            except asyncio.CancelledError:
                pass
        If the request fails, the server process exits with error code 1.
        
        url = self.settings["mwi_server_url"] + "/terminate_integration"

        try:
            async with aiohttp.ClientSession() as client_session:
                async with client_session.delete(url) as res:
                    pass

        matlab = self.processes["matlab"]
        if matlab is not None and matlab.returncode is None:
            try:
                logger.info(
                    f"Calling terminate on MATLAB process with PID: {matlab.pid}!"
                )
                matlab.terminate()
                await matlab.wait()
            except:
                logger.info(
                    f"Exception occured during termination of MATLAB process with PID: {matlab.pid}!"
                )
                pass

        xvfb = self.processes["xvfb"]
        logger.debug(f"Attempting XVFB Termination Xvfb)")
        if xvfb is not None and xvfb.returncode is None:
            logger.info(f"Terminating Xvfb (PID={xvfb.pid})")
            xvfb.terminate()
            await xvfb.wait()

        except aiohttp.client_exceptions.ServerDisconnectedError:
            logger.error("Server has already disconnected...")

        # If even the terminate integration request fails, exit with error code 1.
        except Exception as err:
            logger.error("Failed to send terminate integration request:\n", err)
            sys.exit(1)"""

    async def __send_stop_request_to_matlab(self):
        """Private method to send a HTTP request to MATLAB to shutdown gracefully

        Raises:
            Exception: EmbeddedConnectorError if the request fails.
        """

        try:
            data = mwi.embedded_connector.helpers.get_data_to_eval_mcode("exit")
            url = mwi.embedded_connector.helpers.get_mvm_endpoint(
                self.settings["mwi_server_url"]
            )

            resp_json = await mwi.embedded_connector.send_request(
                url=url, method="POST", data=data, headers=None
            )

            if resp_json["messages"]["EvalResponse"][0]["isError"]:
                raise EmbeddedConnectorError(
                    "Failed to send HTTP request to Embedded connector"
                )

        except Exception as err:
            raise err

    async def stop_matlab(self, force_quit=False):
        """Terminate MATLAB."""
        # Clean up session files which determine various states of the server &/ MATLAB.
        # Do this first as stopping MATLAB/Xvfb takes longer and may fail
        try:
            for _, session_file in self.matlab_session_files.items():
                if session_file is not None:
                    logger.info(f"Deleting:{session_file}")
                    session_file.unlink()
        except FileNotFoundError:
            # Files won't exist when stop_matlab is called for the first time.
            pass

        # In posix systems, variable matlab is an instance of asyncio.subprocess.Process()
        # In windows systems, variable matlab is an isntance of psutil.Process()
        matlab = self.processes["matlab"]

        waiters = []
        if matlab is not None:
            # Sending a request to embedded connector works sporadically on posix systems.
            # So, terminating the process when force_quit is set to True.
            if system.is_posix() and matlab.returncode is None:
                if force_quit:
                    logger.debug("Forcing the MATLAB process to terminate...")
                    matlab.terminate()
                    waiters.append(matlab.wait())
                else:
                    logger.debug("Sending HTTP request to stop the MATLAB process...")
                    try:
                        # Send HTTP request
                        await self.__send_stop_request_to_matlab()

                        # Wait for matlab to shutdown gracefully
                        await matlab.wait()
                        assert (
                            matlab.returncode == 0
                        ), "Failed to gracefully shutdown MATLAB via the embedded connector"

                        logger.debug("Stopped the MATLAB process gracefully")

                    except Exception as err:
                        log_error(logger, err)
                        logger.info(
                            "Failed to stop MATLAB gracefully. Attempting to terminate the process."
                        )
                        try:
                            matlab.terminate()
                            await matlab.wait()
                        except:
                            pass

            else:
                if not system.is_posix() and matlab.is_running():
                    # If in a windows system, send request to embedded connector
                    # to stop matlab.
                    logger.debug("Sending HTTP request to stop the MATLAB process...")

                    try:
                        # Send HTTP request
                        await self.__send_stop_request_to_matlab()

                        # Wait for matlab to shutdown gracefully
                        matlab.wait()
                        assert (
                            not matlab.is_running()
                        ), "Failed to gracefully shutdown MATLAB via the embedded connector"

                        logger.debug("Stopped the MATLAB process gracefully")

                    except Exception as err:
                        log_error(logger, err)
                        logger.info(
                            "Failed to stop MATLAB gracefully. Attempting to terminate the process."
                        )
                        try:
                            matlab.terminate()
                            matlab.wait()
                        except:
                            pass

        logger.info("Stopped (any running)MATLAB process.")

        # Terminating Xvfb
        if system.is_posix():
            xvfb = self.processes["xvfb"]
            if xvfb is not None and xvfb.returncode is None:
                logger.info(f"Terminating Xvfb (PID={xvfb.pid})")
                xvfb.terminate()
                waiters.append(xvfb.wait())

        if len(waiters) > 0:
            logger.debug("Waiting for MATLAB/Xvfb to terminate")
            for waiter in waiters:
                await waiter

        stderr_reader_task = self.tasks.get("matlab_stderr_reader")
        if stderr_reader_task is not None:
            try:
                stderr_reader_task.cancel()
                await stderr_reader_task
            except asyncio.CancelledError:
                pass

            self.tasks.pop("matlab_stderr_reader")

            logger.info("matlab_stderr_reader() task: Stopped successfully.")

        # Clear logs if MATLAB stopped intentionally
        logger.debug("Clearing logs!")
        self.logs["matlab"].clear()
        logger.debug("Cleared any logs created by the MATLAB process.")

        logger.debug("Completed Shutdown!!!")

    async def handle_matlab_output(self):
        """Parse MATLAB output from stdout and raise errors if any."""
        matlab = self.processes["matlab"]

        # Wait for MATLAB process to exit
        logger.info("Waiting for MATLAB to exit...")
        await matlab.wait()

        rc = self.processes["matlab"].returncode
        logger.info(
            f"MATLAB has shutdown with {'exit' if rc == 0 else 'error'} code: {rc}"
        )

        # Look for errors if MATLAB was not intentionally stopped and had an error code
        if len(self.logs["matlab"]) > 0 and rc != 0:
            err = None
            logs = [log.decode().rstrip() for log in self.logs["matlab"]]

            def parsed_errs():
                if self.licensing["type"] == "nlm":
                    yield mw.parse_nlm_error(logs, self.licensing["conn_str"])
                if self.licensing["type"] == "mhlm":
                    yield mw.parse_mhlm_error(logs)
                yield mw.parse_other_error(logs)

            for err in parsed_errs():
                if err is not None:
                    break

            if err is not None:
                self.error = err
                log_error(logger, err)
