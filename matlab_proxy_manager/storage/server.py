# Copyright 2024-2025 The MathWorks, Inc.
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

import psutil

from matlab_proxy_manager.utils import helpers, logger

log = logger.get()


@dataclass
class ServerProcess:
    """
    Represents a MATLAB server process with various attributes and methods
    to manage its lifecycle.
    """

    server_url: Optional[str] = None
    mwi_base_url: Optional[str] = None
    headers: Optional[dict] = None
    errors: Optional[list] = None
    pid: Optional[str] = None
    parent_pid: Optional[str] = None
    absolute_url: Optional[str] = field(default=None)
    id: Optional[str] = None
    type: Optional[str] = None
    mpm_auth_token: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.absolute_url:
            self.absolute_url = f"{self.server_url}{self.mwi_base_url}"

    def __str__(self) -> str:
        """
        Returns a string representation of the ServerProcess instance.
        """
        return json.dumps(asdict(self))

    def as_dict(self) -> dict:
        """
        Returns a dict representation of the ServerProcess instance.
        """
        return asdict(self)

    @staticmethod
    def instantiate_from_string(data: str) -> "ServerProcess":
        """
        Instantiates a ServerProcess object from a JSON string.

        Args:
            data (str): The JSON string representing a ServerProcess.

        Returns:
            ServerProcess: An instance of ServerProcess.

        Raises:
            ValueError: If the JSON string cannot be parsed or is missing required fields.
        """
        try:
            full_dict = json.loads(data)
            key = list(full_dict.keys())[0]
            server = full_dict[key]
            server_process = ServerProcess(
                server_url=server["server_url"],
                mwi_base_url=server["mwi_base_url"],
                headers=server["headers"],
                errors=server["errors"],
                pid=server["pid"],
                parent_pid=server["parent_pid"],
                absolute_url=server["absolute_url"],
                id=server["id"],
                type=server["type"],
                mpm_auth_token=server["mpm_auth_token"],
            )
            return server_process
        except (json.JSONDecodeError, KeyError) as ex:
            log.debug("Failed to instantiate server from %s: %s", data, ex)
            raise ValueError(
                "Invalid JSON string for ServerProcess instantiation"
            ) from ex

    def shutdown(self):
        """
        Shuts down the MATLAB proxy server by calling the shutdown_integration endpoint.
        """
        log.debug("Shutting down matlab proxy")
        backend_server = self.absolute_url
        url = f"{backend_server}/shutdown_integration"
        try:
            response = helpers.requests_retry_session(retries=1).delete(
                url=url, headers=self.headers
            )
            shutdown_resp = response.json()
            log.debug("Response from shutdown: %s", response.json())
            return shutdown_resp
        except Exception as e:
            log.debug("Exception while shutting down matlab proxy: %s", e)

            # Force kill matlab-proxy and its process tree if termination
            # via shutdown_integration endpoint fails
            try:
                matlab_proxy_process = psutil.Process(int(self.pid))
                self.terminate_process_tree(matlab_proxy_process)
            except Exception as e:
                log.debug("Exception while terminating child processes: %s", e)
            return None

    def terminate_process_tree(self, matlab_proxy_process):
        """
        Terminates the process tree of the MATLAB proxy server.

        This method terminates all child processes of the MATLAB proxy process,
        waits for a short period, and then forcefully kills any remaining processes.
        Finally, it kills the main MATLAB proxy process itself.
        """
        matlab_proxy_child_processes = matlab_proxy_process.children(recursive=True)
        for child_process in matlab_proxy_child_processes:
            child_process.terminate()
        _, alive = psutil.wait_procs(matlab_proxy_child_processes, timeout=5)
        for process in alive:
            # Kill the processes which are alive even after waiting for 5 seconds
            process.kill()
        matlab_proxy_process.kill()
        log.debug("Killed matlab-proxy process with PID: %s", self.pid)

    def is_server_alive(self) -> bool:
        """
        Checks if the server process is alive and ready.

        Returns:
            bool: True if the server process is alive and ready, False otherwise.
        """
        return helpers.does_process_exist(self.pid) and helpers.is_server_ready(
            self.absolute_url, retries=0
        )

    @staticmethod
    def find_existing_server(data_dir, key: str) -> Optional["ServerProcess"]:
        """
        Finds an existing server process by reading the server configuration from a file.

        Args:
            data_dir (str): The directory where server configuration files are stored.
            key (str): The key corresponding to the specific server configuration.

        Returns:
            Optional[ServerProcess]: An instance of ServerProcess if a valid configuration is found,
            otherwise None.
        """
        key_dir = Path(data_dir, key)
        server_process = None

        # Return early if the directory is not found
        if not key_dir.is_dir():
            return server_process

        files = list(key_dir.iterdir())
        if not files:
            return server_process

        try:
            with open(files[0], "r", encoding="utf-8") as file:
                data = file.read().strip()
                if data:
                    server_process = ServerProcess.instantiate_from_string(data)
        except (OSError, ValueError) as ex:
            log.debug("Exception while checking for existing server: %s", ex)

        return server_process
