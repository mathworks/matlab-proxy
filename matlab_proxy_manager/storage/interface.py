# Copyright 2024 The MathWorks, Inc.
from typing import Protocol


class IRepository(Protocol):
    """
    Protocol for a repository that manages MATLAB proxy server processes.
    This protocol defines the required methods for adding, retrieving, and deleting
    server process instances to the storage system (files).
    """

    def add(self, server, filename: str):
        """
        Adds a server process to the repository.

        Args:
            server (server.ServerProcess): The server process instance to add.
            filename (str): The filename to associate with the server process.

        Raises:
            NotImplementedError
        """
        raise NotImplementedError("add not implemented")

    def get(self, name: str) -> tuple:
        """
        Retrieves a server process from the repository by its filename.

        Args:
            filename (str): The filename associated with the server process.

        Returns:
            tuple (str, server.ServerProcess): Full file path and the retrieved server process instance.

        Raises:
            NotImplementedError
        """
        raise NotImplementedError("get not implemented")

    def get_all(self):
        """
        Retrieves all server processes from the repository.

        Returns:
            Dict[str, server.ServerProcess]: Dict with filename as key and corresponding server process as value.

        Raises:
            NotImplementedError
        """
        raise NotImplementedError("get_all not implemented")

    def delete(self, filename: str) -> None:
        """
        Deletes a server process from the repository by its filename.

        Args:
            filename (str): The filename associated with the server process to delete.

        Raises:
            NotImplementedError
        """
        raise NotImplementedError("delete not implemented")
