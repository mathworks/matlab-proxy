# Copyright 2024-2025 The MathWorks, Inc.
import http
import os
import socket
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Generator, Optional, Tuple
from urllib.parse import urlparse

import psutil
import requests
from aiohttp import web
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from matlab_proxy import settings
from matlab_proxy_manager.storage.file_repository import FileRepository
from matlab_proxy_manager.utils import logger

log = logger.get()


def is_server_ready(url: Optional[str], retries: int = 2, backoff_factor=None) -> bool:
    """
    Check if the server at the given URL is ready.

    Args:
        url (str): The URL of the server.

    Returns:
        bool: True if the server is ready, False otherwise.
    """
    try:
        # Validate URL
        parsed_url = urlparse(url)
        if not all([parsed_url.scheme, parsed_url.netloc]):
            log.debug("Invalid URL provided: %s", url)
            return False

        matlab_proxy_index_page_identifier = "MWI_MATLAB_PROXY_IDENTIFIER"
        resp = requests_retry_session(
            retries=retries, backoff_factor=backoff_factor
        ).get(f"{url}", verify=False)
        log.debug("Response status code from server readiness: %s", resp.status_code)
        return (
            resp.status_code == http.HTTPStatus.OK
            and matlab_proxy_index_page_identifier in resp.text
        )
    except Exception as e:
        log.debug("Couldn't reach the server with error: %s", e)
        return False


def requests_retry_session(
    retries=3, backoff_factor=0.1, session=None
) -> requests.Session:
    """
    Create a requests session with retry logic.

    Args:
        retries (int): The number of retries.
        backoff_factor (float): The backoff factor for retries.
        session (requests.Session, optional): An existing requests session.

    Returns:
        requests.Session: The requests session with retry logic.
    """
    session = session or requests.session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        allowed_methods=frozenset(["DELETE", "GET", "POST"]),
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def does_process_exist(pid: Optional[str]) -> bool:
    """
    Checks if the parent process is alive.

    Returns:
        bool: True if the parent process is alive, False otherwise.
    """
    return bool(pid and psutil.pid_exists(int(pid)))


def convert_mwi_env_vars_to_header_format(
    env_vars: Dict[str, str], prefix: str
) -> Dict[str, str]:
    """
    Parse and transform environment variables with a specific prefix.

    Args:
        env_vars (dict): The environment variables.
        prefix (str): The prefix to filter the environment variables.

    Returns:
        dict: The transformed environment variables.
    """
    return {
        key.replace("_", "-"): value
        for key, value in env_vars.items()
        if key.startswith(prefix)
    }


def create_and_get_proxy_manager_data_dir() -> Path:
    """
    Create and get the proxy manager data directory.

    Returns:
        Path: The path to the proxy manager data directory.
    """

    config_dir = settings.get_mwi_config_folder(dev=False)
    data_dir = Path(config_dir, "proxy_manager")
    Path.mkdir(data_dir, parents=True, exist_ok=True)
    return data_dir


async def delete_dangling_servers(app: web.Application) -> None:
    """
    Delete dangling matlab proxy servers that are no longer alive.

    Args:
        app (web.Application): aiohttp web application
    """
    is_delete_successful = _are_orphaned_servers_deleted()
    log.debug("Deleted dangling matlab proxy servers: %s", is_delete_successful)


def _are_orphaned_servers_deleted(predicate: Optional[str] = "") -> bool:
    """
    Get all the files under the proxy manager directory, check the status of the servers,
    and delete orphaned servers and their corresponding files.

    - Checks if the parent PID of each server is still alive. If not, sends a SIGKILL
    to the server and deletes the corresponding file.
    - Checks if the servers in those files are still alive by sending GET requests to
    their absolute URLs. If not, deletes the corresponding file.

    Returns:
        bool: True if any server was deleted, False otherwise.
    """
    data_dir = create_and_get_proxy_manager_data_dir()
    storage = FileRepository(data_dir)
    servers: dict = storage.get_all()

    def _matches_predicate(filename: str) -> bool:
        return filename.split("_")[0] == str(predicate)

    # Checks only a subset of servers (that matches the parent_pid of the caller)
    # to reduce the MATLAB proxy startup time
    if predicate:
        servers = {
            filename: server
            for filename, server in servers.items()
            if _matches_predicate(Path(filename).stem)
        }
        if not servers:
            log.debug("Parent pid not matched, nothing to cleanup")
            return True

    return _delete_server_and_file(storage, servers)


def _delete_server_and_file(storage, servers) -> bool:
    is_server_deleted = False
    for filename, server in servers.items():
        if not server.is_server_alive():
            log.debug("Server is not alive, cleaning up files")
            try:
                storage.delete(os.path.basename(filename))
            except Exception as ex:
                log.debug("Failed to delete file: %s", ex)
            is_server_deleted = True
        elif not does_process_exist(server.parent_pid):
            log.debug("Server's parent is gone, shutting down matlab proxy")
            try:
                server.shutdown()
            except Exception as ex:
                log.debug("Failed to shutdown the matlab proxy server: %s", ex)
            finally:
                # Ensures files are cleaned up even if shutdown fails
                storage.delete(os.path.basename(filename))
                is_server_deleted = True

    return is_server_deleted


def poll_for_server_deletion() -> None:
    """
    Poll for server deletion for a specified timeout period.

    This function continuously checks if orphaned servers are deleted within a
    specified timeout period. If servers are deleted, it breaks out of the loop.

    Logs the status of server deletion attempts.
    """
    timeout_in_seconds: int = 2
    log.debug("Interrupt/termination signal caught, cleaning up resources")
    start_time = time.time()

    while time.time() - start_time < timeout_in_seconds:
        is_server_deleted = _are_orphaned_servers_deleted()
        if is_server_deleted:
            log.debug("Servers deleted, breaking out of loop")
            break
        log.debug("Servers not deleted, waiting")
        # Sleep for a short interval before polling again
        time.sleep(0.5)


@contextmanager
def find_free_port() -> Generator[Tuple[str, socket.socket], None, None]:
    """
    Context manager for finding a free port on the system.

    This function creates a socket, binds it to an available port, and yields
    the port number along with the socket object. The socket is automatically
    closed when exiting the context.

    Yields:
        Tuple[str, socket.socket]: A tuple containing:
            - str: The free port number as a string.
            - socket.socket: The socket object.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    port = str(s.getsockname()[1])
    try:
        yield port, s
    finally:
        try:
            s.close()
        except OSError as ex:
            # Socket already closed, log and ignore the exception
            log.debug("Failed to close socket: %s", ex)


def pre_load_from_state_file(data_dir: str) -> Dict[str, str]:
    """
    Pre-load server states from the state files in the specified data directory.

    Args:
        data_dir (Path): The directory containing the state files.

    Returns:
        Dict[str, Dict]: A dictionary with server IDs as keys and server states as values.
    """
    storage = FileRepository(data_dir)
    servers = storage.get_all()
    return {server.id: server.as_dict() for server in servers.values()}


def is_only_reference(file_path: str) -> bool:
    """
    Check if the specified file is the only file in its directory.

    Args:
        file_path (str): The path to the file.

    Returns:
        bool: True if the file is the only file in its directory, False otherwise.
    """
    parent_dir = Path(file_path).parent.absolute()
    files = os.listdir(parent_dir)
    return len(files) == 1 and files[0] == os.path.basename(file_path)


def create_state_file(data_dir, server_process, filename: str):
    """
    Create a state file in the specified data directory.

    This function creates a state file for the given server process in the specified
    data directory. It logs the process and handles any exceptions that might occur.

    Args:
        data_dir: The directory where the state file will be created.
        server_process (ServerProcess): The server process for which the state file is created.
        filename (str): The name of the state file to be created.

    Raises:
        IOError: If there is an error creating the state file or adding the server
        process to the repository.
    """
    try:
        storage = FileRepository(data_dir)
        storage.add(server=server_process, filename=filename)
        log.debug("State file %s created in %s", filename, data_dir)
    except Exception as e:
        log.error(
            "Failed to create state file %s in %s, error: %s", filename, data_dir, e
        )
        raise IOError(
            f"Failed to create state file {filename} in {data_dir}, error: {e}"
        ) from e
