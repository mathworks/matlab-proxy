# Copyright 2024-2025 The MathWorks, Inc.
import asyncio
import os
import secrets
import subprocess
from typing import List, Tuple

import matlab_proxy
import matlab_proxy.util.mwi.environment_variables as mwi_env
import matlab_proxy.util.system as mwi_sys
from matlab_proxy_manager.storage.file_repository import FileRepository
from matlab_proxy_manager.storage.server import ServerProcess
from matlab_proxy_manager.utils import constants, exceptions, helpers, logger

# Used to list all the public-facing APIs exported by this module.
__all__ = ["shutdown", "start_matlab_proxy_for_kernel", "start_matlab_proxy_for_jsp"]

log = logger.get()
shutdown_lock = asyncio.Lock()
log = logger.get(init=True)


async def start_matlab_proxy_for_kernel(
    caller_id: str, parent_id: str, is_shared_matlab: bool, base_url_prefix: str = ""
):
    """
    Starts a MATLAB proxy server specifically for MATLAB Kernel.

    This function is a wrapper around the `start_matlab_proxy` function, with mpm_auth_token
    set to None, for starting the MATLAB proxy server via proxy manager.
    """
    return await _start_matlab_proxy(
        caller_id=caller_id,
        ctx=parent_id,
        is_shared_matlab=is_shared_matlab,
        base_url_prefix=base_url_prefix,
    )


async def start_matlab_proxy_for_jsp(
    parent_id: str,
    is_shared_matlab: bool,
    mpm_auth_token: str,
    base_url_prefix: str = "",
):
    """
    Starts a MATLAB proxy server specifically for Jupyter Server Proxy (JSP) - Open MATLAB launcher.

    This function is a wrapper around the `start_matlab_proxy` function, providing
    a more specific context (mpm_auth_token) for starting the MATLAB proxy server via proxy manager.
    """
    return await _start_matlab_proxy(
        caller_id="jsp",
        ctx=parent_id,
        is_shared_matlab=is_shared_matlab,
        mpm_auth_token=mpm_auth_token,
        base_url_prefix=base_url_prefix,
    )


async def _start_matlab_proxy(**options) -> dict:
    """
    Starts a MATLAB proxy server with the specified options.

    This function validates the provided options, checks for existing server instances,
    and either returns an existing server process or starts a new MATLAB proxy server.
    It ensures that required arguments are present, handles token generation, and manages
    server readiness and error handling.

    Args:
        **options: Arbitrary keyword arguments containing the following keys:
            - caller_id (str): The identifier for the caller (kernel id for kernels, "jsp" for JSP).
            - ctx (str): The context in which the server is being started (parent pid).
            - is_shared_matlab (bool): Flag indicating if the MATLAB proxy is shared.
            - mpm_auth_token (Optional[str]): Authentication token for the MATLAB proxy manager.
            - base_url_prefix (Optional[str]): Custom URL path which gets added to mwi_base_url

    Returns:
        dict: A dictionary representation of the server process, including any errors encountered.

    Raises:
        ValueError: If `caller_id` is "default" and `is_shared_matlab` is False.
    """
    _validate_required_arguments(options)

    caller_id: str = options["caller_id"]
    ctx: str = options["ctx"]
    is_shared_matlab: bool = options.get("is_shared_matlab", True)
    mpm_auth_token = options.get("mpm_auth_token", None) or secrets.token_hex(32)

    if not is_shared_matlab and caller_id == "default":
        raise ValueError(
            "Caller id cannot be default when matlab proxy is not shareable"
        )

    # Cleanup stale entries before starting new instance of matlab proxy server
    helpers._are_orphaned_servers_deleted(ctx)

    client_id = caller_id if not is_shared_matlab else "default"
    matlab_session_dir = f"{ctx}_{client_id}"
    filename = f"{ctx}_{caller_id}"
    proxy_manager_root_dir = helpers.create_and_get_proxy_manager_data_dir()
    existing_matlab_proxy_process = ServerProcess.find_existing_server(
        proxy_manager_root_dir, matlab_session_dir
    )

    if existing_matlab_proxy_process:
        log.debug("Found existing server for aliasing")

        # Create a backend file for this caller for reference tracking
        helpers.create_state_file(
            proxy_manager_root_dir, existing_matlab_proxy_process, filename
        )

        return existing_matlab_proxy_process.as_dict()

    # Create a new matlab proxy server
    try:
        base_url_prefix = options.get("base_url_prefix", "")

        # Prepare matlab proxy command and required environment variables
        matlab_proxy_cmd, matlab_proxy_env = _prepare_cmd_and_env_for_matlab_proxy(
            client_id, base_url_prefix
        )

        log.debug(
            "Starting new matlab proxy server using ctx=%s, client_id=%s, is_shared_matlab=%s",
            ctx,
            client_id,
            is_shared_matlab,
        )
        # Start the matlab proxy process
        process_id, url = await _start_subprocess(matlab_proxy_cmd, matlab_proxy_env)
        log.debug("MATLAB proxy process url: %s", url)

        matlab_proxy_process = ServerProcess(
            server_url=url,
            mwi_base_url=matlab_proxy_env.get(mwi_env.get_env_name_base_url()),
            headers=helpers.convert_mwi_env_vars_to_header_format(
                matlab_proxy_env, "MWI"
            ),
            pid=str(process_id),
            parent_pid=ctx,
            id=matlab_session_dir,
            type="shared" if is_shared_matlab else "isolated",
            mpm_auth_token=mpm_auth_token,
        )

        await _check_for_process_readiness(matlab_proxy_process)

        # Store the newly created server into filesystem
        helpers.create_state_file(
            proxy_manager_root_dir, matlab_proxy_process, filename
        )
        return matlab_proxy_process.as_dict()

    # Return a server process instance with the errors information set
    except exceptions.ProcessStartError as pse:
        return ServerProcess(errors=[str(pse)]).as_dict()
    except exceptions.ServerReadinessError as sre:
        return ServerProcess(errors=[str(sre)]).as_dict()
    except Exception as e:
        log.error("Error starting matlab proxy server: %s", str(e))
        return ServerProcess(errors=[str(e)]).as_dict()


def _validate_required_arguments(options):
    # Validates that all required arguments are present in the supplied values
    required_args: List[str] = ["caller_id", "ctx", "is_shared_matlab"]
    missing_args: List[str] = [arg for arg in required_args if arg not in options]

    if missing_args:
        raise ValueError(f"Missing required arguments: {', '.join(missing_args)}")


async def _check_for_process_readiness(matlab_proxy_process: ServerProcess):
    """
    Checks if the MATLAB proxy server is ready.

    Args:
        matlab_proxy_process (ServerProcess): Deserialized matlab-proxy process

    Raises:
        ServerReadinessError: If the MATLAB proxy server is not ready after retries.
    """
    # Check for the matlab proxy server readiness - with retries
    if not helpers.is_server_ready(
        url=matlab_proxy_process.absolute_url, retries=7, backoff_factor=0.5
    ):
        log.error(
            "MATLAB Proxy Server unavailable: matlab-proxy-app failed to start or has timed out."
        )
        matlab_proxy_process.shutdown()
        raise exceptions.ServerReadinessError()


def _prepare_cmd_and_env_for_matlab_proxy(client_id: str, base_url_prefix: str):
    """
    Prepare the command and environment variables for starting the MATLAB proxy.

    Returns:
        Tuple: A tuple containing the MATLAB proxy command and environment variables.
    """
    # Get config from matlab_proxy module if jupyter_matlab_proxy module is not available
    try:
        from jupyter_matlab_proxy import config
    except ImportError:
        from matlab_proxy.default_configuration import config

    # Get the command to start matlab-proxy
    matlab_proxy_cmd: list = [
        matlab_proxy.get_executable_name(),
        "--config",
        config.get("extension_name"),
    ]

    mwi_base_url = _construct_mwi_base_url(base_url_prefix, client_id)
    log.info("MWI_BASE_URL : %s", mwi_base_url)

    input_env: dict = {
        "MWI_AUTH_TOKEN": secrets.token_urlsafe(32),
        "MWI_BASE_URL": mwi_base_url,
    }

    matlab_proxy_env: dict = os.environ.copy()
    matlab_proxy_env.update(input_env)

    return matlab_proxy_cmd, matlab_proxy_env


def _construct_mwi_base_url(base_url_prefix: str, client_id: str):
    # Converts to correct base url (e.g. /jupyter/, default to /jupyter/matlab/default)
    log.debug(
        "base_url_prefix_from_client: %s, client_id: %s", base_url_prefix, client_id
    )

    if base_url_prefix:
        base_url_prefix = base_url_prefix.rstrip("/")
    prefix = constants.MWI_BASE_URL_PREFIX.strip("/")
    client_id = client_id.strip("/")
    return "/".join([base_url_prefix, prefix, client_id])


async def _start_subprocess(cmd: list, env: dict) -> Tuple[int, str]:
    """
    Initializes and starts a subprocess using the specified command and provided environment.

    Args:
        cmd (list): The command to execute the subprocess.
        env (dict): The environment variables to set for the subprocess.

    Returns:
        Optional[Tuple[int, str]]: A tuple containing the process ID, the URL
        of the server, or None if the process fails to start.
    """

    process = None
    url = None

    # Get a free port and corresponding bound socket
    with helpers.find_free_port() as (port, _):
        log.debug("Allocated port %s", port)

        env.update(
            {
                "MWI_APP_PORT": port,
            }
        )

        # Using loopback address so that DNS resolution doesn't add latency in Windows
        url = f"http://127.0.0.1:{port}"
        process = await _initialize_process_based_on_os_type(cmd, env)
        process_pid = process.pid
        log.debug(
            "MATLAB proxy info: pid = %s, returncode = %s",
            process_pid,
            process.returncode,
        )
        return process_pid, url


async def _initialize_process_based_on_os_type(cmd, env):
    """
    Initializes and starts a subprocess based on the operating system.

    This function attempts to create a subprocess using the provided command and
    environment variables. It handles both POSIX and Windows systems differently.

    Args:
        cmd (list): The command to execute the subprocess.
        env (dict): The environment variables to set for the subprocess.

    Returns:
        subprocess.Popen or asyncio.subprocess.Process: The process object for the started subprocess.

    Raises:
        exceptions.ProcessStartError: If the subprocess fails to start.
    """
    try:
        if mwi_sys.is_posix():
            log.debug("Starting matlab proxy subprocess for posix")
            return await asyncio.create_subprocess_exec(
                *cmd,
                env=env,
                # kernel sporadically ends up cleaning the child matlab-proxy process during the
                # restart workflow. This is a workaround to handle that race condition which leads
                # to starting matlab-proxy in a new process group and is not counted for deletion.
                # https://github.com/ipython/ipykernel/blob/main/ipykernel/kernelbase.py#L1283
                start_new_session=True,
            )
        else:
            log.debug("Starting matlab proxy subprocess for windows")
            return subprocess.Popen(
                cmd,
                env=env,
            )
    except Exception as e:
        log.error("Failed to create matlab-proxy subprocess: %s", e)
        raise exceptions.ProcessStartError(extra_info=str(e)) from e


async def shutdown(parent_pid: str, caller_id: str, mpm_auth_token: str):
    """
    Shutdown the MATLAB proxy server if the provided authentication token is valid.

    This function attempts to shut down the MATLAB proxy server identified by the
    given context and ID, provided the correct authentication token is supplied.
    It ensures that the shutdown process is thread-safe using an asyncio lock.

    Args:
        parent_pid (str): The context identifier for the server.
        caller_id (str): The unique identifier for the server.
        mpm_auth_token (str): The authentication token for proxy manager and client communication.

    Returns:
        Optional[None]: Returns None if the shutdown process is successful or if
                        required arguments are missing.

    Raises:
        FileNotFoundError: If the state file for the server does not exist.
        ValueError: If the authentication token is invalid.
        Exception: If any other error occurs during the shutdown process.
    """
    if not parent_pid or not caller_id or not mpm_auth_token:
        log.debug(
            "Required arguments (parent_pid | caller_id | mpm_auth_token) for shutdown missing"
        )
        return

    filename = f"{parent_pid}_{caller_id}"
    try:
        data_dir = helpers.create_and_get_proxy_manager_data_dir()
        storage = FileRepository(data_dir)
        full_file_path, server = storage.get(filename)

        if not server:
            log.debug("State file for this server not found, filename: %s", filename)
            return

        if mpm_auth_token != server.mpm_auth_token:
            raise ValueError("Invalid authentication token")

        # Using asyncio lock to ensure thread-safe shutdown: clicking shutdown
        # all on Kernel UI sends shutdown request in parallel which could lead
        # to a scenario where the kernels' shutdown just cleans the files from
        # filesystem and doesn't shut down the backend matlab proxy server.
        async with shutdown_lock:
            if helpers.is_only_reference(full_file_path):
                server.shutdown()

            # Delete the file for this server
            storage.delete(f"{filename}.info")
    except FileNotFoundError as e:
        log.error("State file for server %s not found: %s", filename, e)
        return
    except ValueError as e:
        log.error("Authentication error for server %s: %s", filename, e)
        return
    except Exception as e:
        log.error("Error during shutdown of server %s: %s", filename, e)
        raise
