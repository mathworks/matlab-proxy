# Copyright 2024 The MathWorks, Inc.
import glob
import json
import os
from pathlib import Path
from typing import Optional

from matlab_proxy_manager.utils import logger

from .interface import IRepository

log = logger.get()


class FileRepository(IRepository):
    """
    A repository for managing MATLAB proxy server processes using the file system.
    """

    def __init__(self, data_dir) -> None:
        super().__init__()
        self.data_dir = data_dir
        self.encoding = "utf-8"

    def get_all(self):
        """Retrieves all server processes from the repository.

        Returns:
            A dictionary mapping file paths to server process instances.
        """
        from matlab_proxy_manager.storage.server import ServerProcess

        servers = {}

        # Read all the files in data_dir
        all_files = glob.glob(f"{self.data_dir}/**/*.info", recursive=True)

        for file in all_files:
            try:
                with open(file, "r", encoding=self.encoding) as f:
                    data = f.read().strip()

                    # Convert the content of each file to ServerProcess
                    if data:
                        server_process = ServerProcess.instantiate_from_string(data)
                        servers[file] = server_process
            except Exception as ex:
                log.debug("ServerProcess instantiation failed for %s: %s", file, ex)
        return servers

    def get(self, name) -> tuple:
        """
        Retrieves a server process from the repository by its filename.

        Args:
            name (str): The name of the server process file.

        Returns:
            Tuple[Optional[str], Optional[ServerProcess]]: A tuple containing the file path
            and the server process instance.
        """
        from matlab_proxy_manager.storage.server import ServerProcess

        server_process = None
        full_file_path: Optional[str] = None
        current_files = glob.glob(f"{self.data_dir}/**/{name}.info", recursive=True)
        if current_files:
            full_file_path = current_files[0]
            with open(full_file_path, "r", encoding=self.encoding) as f:
                try:
                    data = f.read().strip()
                    if data:
                        server_process = ServerProcess.instantiate_from_string(data)
                except Exception as ex:
                    log.debug(
                        "ServerProcess instantiation failed for %s: %s",
                        full_file_path,
                        ex,
                    )

        return full_file_path, server_process

    def add(self, server, filename: str) -> None:
        """
        Adds a server process to the repository.
        Creates a directory like <ctx>_default|<kernel_id> and then creates a file as
        default|<kernel_id>.info in that dir

        Args:
            server (ServerProcess): The server process instance to add.
            filename (str): The filename to associate with the server process.
        """
        # Creates a child dir under the data_dir
        server_dir = Path(f"{self.data_dir}", f"{server.id}")
        Path.mkdir(server_dir, parents=True, exist_ok=True)
        server_dict = {}

        server_file = Path(server_dir, f"{filename}.info")
        with open(server_file, "w", encoding=self.encoding) as f:
            server_dict[server.id] = server.as_dict()
            file_content = json.dumps(server_dict)
            f.write(file_content)

    def delete(self, filename: str) -> None:
        """
        Deletes a server process from the repository by its filename.

        Args:
            filename (str): The filename associated with the server process to delete.
        """
        # <path to proxy manager dir>/<parent_pid>_<name>/<name>.info
        full_file_path, parent_dir = FileRepository._find_file_and_get_parent(
            self.data_dir, filename
        )
        if full_file_path:
            Path(full_file_path).unlink(missing_ok=True)
            log.debug("Deleted file: %s", filename)

            # delete the sub-directory (<parent_pid>_<id>) only if it is empty
            if parent_dir and not len(os.listdir(parent_dir)):
                os.rmdir(parent_dir)
                log.debug("Deleted dir: %s", parent_dir)

    @staticmethod
    def _find_file_and_get_parent(data_dir: str, filename: str):
        """
        Finds the file and its parent directory in the given data directory.

        Args:
            data_dir (str): The base directory to search within.
            filename (str): The filename to search for.

        Returns:
            Tuple[Optional[str], Optional[str]]: A tuple containing the full file path and the parent directory.
        """
        for dirpath, _, filenames in os.walk(data_dir):
            # Check if target file is in the current directory's files
            if filename in filenames:
                full_path = os.path.join(dirpath, filename)
                parent_dir = os.path.dirname(full_path)
                return full_path, parent_dir

        # Return None if the file was not found
        return None, None
