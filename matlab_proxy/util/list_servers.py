# Copyright (c) 2020-2025 The MathWorks, Inc.
# Script to print information about all running matlab-proxy servers for current user on current machine.

import glob
import os

import matlab_proxy.settings as mwi_settings
import matlab_proxy.util as mwi_util

from datetime import datetime
from rich.console import Console
from rich.table import Table

__NO_SERVERS_MSG = "No MATLAB-PROXY Servers are currently running."


def _extract_version_and_session(title):
    """Extracts session name and MATLAB version from the title."""
    parts = title.split("-")
    if len(parts) < 2:
        return title.replace("MATLAB ", ""), ""
    session_name = parts[0].strip()
    matlab_version = parts[1].strip().replace("MATLAB ", "")
    return matlab_version, session_name


def _get_server_info(server):
    """Helper function to parse info from server file."""
    with open(server) as f:
        # Assumes that the server file contains the address on the first line,
        # the browser_title on the second line, and the timestamp is derived from the file's last modified time.
        address = f.readline().strip()
        browser_title = f.readline().strip()
        matlab_version, session_name = _extract_version_and_session(browser_title)
        timestamp = _get_timestamp(server)
        return timestamp, matlab_version, session_name, address


def _print_server_info_as_table(servers):
    console = Console()
    table = Table(
        title="MATLAB Proxy Servers",
        title_style="cyan",
        title_justify="center",
        caption="No servers found." if not servers else "",
        caption_style="bold red",
        show_header=True,
        header_style="yellow",
        show_lines=True,
        show_edge=True,
    )
    table.add_column("Created On")
    table.add_column("MATLAB\nVersion")
    table.add_column("Session Name")
    table.add_column("Server URL", overflow="fold")

    # Build server information
    for server in servers:
        table.add_row(*_get_server_info(server))

    console.print(table)


def _get_timestamp(filename):
    """Get the last modified timestamp of the file in a human-readable format."""
    timestamp = os.path.getmtime(filename)
    readable_time = datetime.fromtimestamp(timestamp).strftime("%d/%m/%y %H:%M:%S")
    return readable_time


def print_server_info():
    """Print information about all matlab-proxy servers (with version > 0.4.0) running on this machine"""
    home_folder = mwi_settings.get_mwi_config_folder()

    # Look for files in port folders
    ports_folder = home_folder / "ports"
    search_string = str(ports_folder) + "/**/mwi_server.info"
    servers = sorted(glob.glob(search_string), key=os.path.getmtime)

    args = mwi_util.parse_list_cli_args()

    if args["quiet"]:
        for server in servers:
            with open(server) as f:
                server_info = f.readline().strip()
                print(f"{server_info}", end="\n")
    else:
        _print_server_info_as_table(servers)
    return
