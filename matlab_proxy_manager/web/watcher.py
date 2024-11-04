# Copyright 2024 The MathWorks, Inc.
from aiohttp import web
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from matlab_proxy_manager.utils import logger
from matlab_proxy_manager.storage.file_repository import FileRepository
from matlab_proxy_manager.utils import helpers

log = logger.get()


class FileWatcher(FileSystemEventHandler):
    """
    A class to watch for file system events and update the server state accordingly.
    """

    def __init__(self, app: web.Application, data_dir: str) -> None:
        """
        Initialize the FileWatcher with the application and directory to watch.
        """
        self.app = app
        self.data_dir = data_dir
        super().__init__()

    def on_created(self, event) -> None:
        """
        Handle the event when a file or directory is created.
        """
        try:
            self.update_server_state()
        except Exception:
            log.error("Error handling created event:", exc_info=True)

    def update_server_state(self) -> None:
        """Update the server state from the repository."""
        current_servers = {}
        storage = FileRepository(self.data_dir)
        servers = storage.get_all()
        current_servers = {server.id: server.as_dict() for server in servers.values()}
        self.app["servers"] = current_servers


def start_watcher(app: web.Application):
    """
    Start a file system watcher to monitor changes in the proxy manager data directory.
    """
    path_to_watch = helpers.create_and_get_proxy_manager_data_dir()
    log.debug("Watching dir: %s", path_to_watch)
    event_handler = FileWatcher(app, path_to_watch)
    observer = Observer()
    observer.schedule(event_handler, path_to_watch, recursive=True)
    observer.start()
    app["observer"] = observer
    return observer


def stop_watcher(app):
    """
    Stop the file system watcher associated with the application.
    This function stops and joins the observer thread if it exists in the application.
    """
    if "observer" in app:
        app["observer"].stop()
        app["observer"].join()
