# Copyright 2024-2025 The MathWorks, Inc.
import asyncio
import os
import secrets
import subprocess
from typing import List, Optional, Tuple

import matlab_proxy
import matlab_proxy.util.system as mwi_sys
from matlab_proxy_manager.storage.file_repository import FileRepository
from matlab_proxy_manager.storage.server import ServerProcess
from matlab_proxy_manager.utils import constants, helpers, logger

# Used to list all the public-facing APIs exported by this module.
__all__ = ["shutdown", "start_matlab_proxy_for_kernel", "start_matlab_proxy_for_jsp"]

log = logger.get()
shutdown_lock = asyncio.Lock()
log = logger.get(init=True)


async def start_matlab_proxy_for_kernel(
    caller_id: str, parent_id: str, is_shared_matlab: bool
):
    """
    Starts a MATLAB proxy server specifically for MATLAB Kernel.

    This function is a wrapper around the `start_matlab_proxy` function, with mpm_auth_token
    set to None, for starting the MATLAB proxy server via proxy manager.
    """
    return await _start_matlab_proxy(
        caller_id=caller_id, ctx=parent_id, is_shared_matlab=is_shared_matlab
    )


async def start_matlab_proxy_for_jsp(
    parent_id: str, is_shared_matlab: bool, mpm_auth_token: str
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
    )


async def _start_matlab_proxy(**options) -> Optional[dict]:
    """
    Start a MATLAB proxy server.

    This function starts a MATLAB proxy server based on the provided context and caller ID.
    It handles the creation of new servers and the reuse of existing ones.

    Args (keyword arguments):
        - caller_id (str): The identifier for the caller (kernel id for kernels, "jsp" for JSP).
        - ctx (str): The context in which the server is being started (parent pid).
        - is_shared_matlab (bool, optional): Whether to start a shared MATLAB proxy instance.
        Defaults to False.
        - mpm_auth_token (str, optional): The MATLAB proxy manager token. If not provided,
        a new token is generated. Defaults to None.

    Returns:
        ServerProcess: The process representing the MATLAB proxy server.

    Raises:
        ValueError: If `caller_id` is "default" and `is_shared_matlab` is False.
    """
    # Validate arguments
    required_args: List[str] = ["caller_id", "ctx", "is_shared_matlab"]
    missing_args: List[str] = [arg for arg in required_args if arg not in options]

    if missing_args:
        raise ValueError(f"Missing required arguments: {', '.join(missing_args)}")

    caller_id: str = options["caller_id"]
    ctx: str = options["ctx"]
    is_shared_matlab: bool = options.get("is_shared_matlab", True)
    mpm_auth_token: Optional[str] = options.get("mpm_auth_token", None)

    if not is_shared_matlab and caller_id == "default":
        raise ValueError(
            "Caller id cannot be default when matlab proxy is not shareable"
        )

    mpm_auth_token = mpm_auth_token or secrets.token_hex(32)

    # Cleanup stale entries before starting new instance of matlab proxy server
    helpers._are_orphaned_servers_deleted(ctx)

    ident = caller_id if not is_shared_matlab else "default"
    key = f"{ctx}_{ident}"
    log.debug("Starting matlab proxy using %s, %s, %s", ctx, ident, is_shared_matlab)

    data_dir = helpers.create_and_get_proxy_manager_data_dir()
    server_process = ServerProcess.find_existing_server(data_dir, key)

    if server_process:
        log.debug("Found existing server for aliasing")

        # Create a backend file for this caller for reference tracking
        helpers.create_state_file(data_dir, server_process, f"{ctx}_{caller_id}")

    # Create a new matlab proxy server
    else:
        server_process = await _start_subprocess_and_check_for_readiness(
            ident, ctx, key, is_shared_matlab, mpm_auth_token
        )

        # Store the newly created server into filesystem
        if server_process:
            helpers.create_state_file(data_dir, server_process, f"{ctx}_{caller_id}")

    return server_process.as_dict() if server_process else None


async def _start_subprocess_and_check_for_readiness(
    server_id: str, ctx: str, key: str, is_shared_matlab: bool, mpm_auth_token: str
) -> Optional[ServerProcess]:
    """
    Starts a MATLAB proxy server.

    This function performs the following steps:
    1. Prepares the command and environment variables required to start the MATLAB proxy server.
    2. Initializes the MATLAB proxy process.
    3. Checks if the MATLAB proxy server is ready.
    4. Creates and returns a ServerProcess instance if the server is ready.

    Returns:
        Optional[ServerProcess]: An instance of ServerProcess if the server is successfully started,
        otherwise None.
    """
    log.debug("Starting new matlab proxy server")

    # Prepare matlab proxy command and required environment variables
    matlab_proxy_cmd, matlab_proxy_env = _prepare_cmd_and_env_for_matlab_proxy()

    # Start the matlab proxy process
    result = await _start_subprocess(matlab_proxy_cmd, matlab_proxy_env, server_id)
    if not result:
        log.error("Could not start matlab proxy")
        return None

    process_id, url, mwi_base_url = result

    log.debug("Matlab proxy process info: %s, %s", url, mwi_base_url)
    matlab_proxy_process = ServerProcess(
        server_url=url,
        mwi_base_url=mwi_base_url,
        headers=helpers.convert_mwi_env_vars_to_header_format(matlab_proxy_env, "MWI"),
        pid=str(process_id),
        parent_pid=ctx,
        id=key,
        type="shared" if is_shared_matlab else "named",
        mpm_auth_token=mpm_auth_token,
    )

    # Check for the matlab proxy server readiness
    if not helpers.is_server_ready(
        url=matlab_proxy_process.absolute_url, retries=7, backoff_factor=0.5
    ):
        log.error(
            "MATLAB Proxy Server unavailable: matlab-proxy-app failed to start or has timed out."
        )
        matlab_proxy_process.shutdown()
        matlab_proxy_process = None

    return matlab_proxy_process


def _prepare_cmd_and_env_for_matlab_proxy():
    """
    Prepare the command and environment variables for starting the MATLAB proxy.

    Returns:
        Tuple: A tuple containing the MATLAB proxy command and environment variables.
    """
    from jupyter_matlab_proxy import config

    # Get the command to start matlab-proxy
    matlab_proxy_cmd: list = [
        matlab_proxy.get_executable_name(),
        "--config",
        config.get("extension_name"),
    ]

    input_env: dict = {
        "MWI_AUTH_TOKEN": secrets.token_urlsafe(32),
    }

    matlab_proxy_env: dict = os.environ.copy()
    matlab_proxy_env.update(input_env)

    return matlab_proxy_cmd, matlab_proxy_env


async def _start_subprocess(cmd, env, server_id) -> Optional[Tuple[int, str, str]]:
    """
    Initializes and starts a subprocess using the specified command and provided environment.

    Returns:
        Optional[int]: The process ID if the process is successfully created, otherwise None.
    """
    process = None
    mwi_base_url: str = f"{constants.MWI_BASE_URL_PREFIX}{server_id}"

    # Get a free port and corresponding bound socket
    with helpers.find_free_port() as (port, _):
        env.update(
            {
                "MWI_APP_PORT": port,
                "MWI_BASE_URL": mwi_base_url,
            }
        )

        # Using loopback address so that DNS resolution doesn't add latency in Windows
        url: str = f"http://127.0.0.1:{port}"

        process = await _initialize_process_based_on_os_type(cmd, env)

    if not process:
        log.error("Matlab proxy process not created due to some error")
        return None

    process_pid = process.pid
    log.debug("MATLAB proxy info: pid = %s, rc = %s", process_pid, process.returncode)
    return process_pid, url, mwi_base_url


async def _initialize_process_based_on_os_type(cmd, env):
    """
    Initializes and starts a subprocess based on the operating system.

    This function attempts to create a subprocess using the provided command and
    environment variables. It handles both POSIX and Windows systems differently.

    Args:
        cmd (List[str]): The command to execute in the subprocess.
        env (Dict[str, str]): The environment variables for the subprocess.

    Returns:
        Union[Process, None, Popen[bytes]]: The created subprocess object if successful,
        or None if an error occurs during subprocess creation.

    Raises:
        Exception: If there's an error creating the subprocess (caught and logged).
    """
    if mwi_sys.is_posix():
        log.debug("Starting matlab proxy subprocess for posix")
        try:
            return await asyncio.create_subprocess_exec(
                *cmd,
                env=env,
                # kernel sporadically ends up cleaning the child matlab-proxy process during the
                # restart workflow. This is a workaround to handle that race condition which leads
                # to starting matlab-proxy in a new process group and is not counted for deletion.
                # https://github.com/ipython/ipykernel/blob/main/ipykernel/kernelbase.py#L1283
                start_new_session=True,
            )
        except Exception as e:
            log.error("Failed to create posix subprocess: %s", e)
            return None
    else:
        try:
            log.debug("Starting matlab proxy subprocess for windows")
            return subprocess.Popen(
                cmd,
                env=env,
            )
        except Exception as e:
            log.error("Failed to create windows subprocess: %s", e)
            return None


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

    try:
        data_dir = helpers.create_and_get_proxy_manager_data_dir()
        storage = FileRepository(data_dir)
        filename = f"{parent_pid}_{caller_id}"
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
