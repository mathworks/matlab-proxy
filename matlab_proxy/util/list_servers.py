# Copyright (c) 2020-2022 The MathWorks, Inc.
# Script to print information about all running matlab-proxy servers for current user on current machine.

import glob
import os

import matlab_proxy.settings as mwi_settings
import matlab_proxy.util as mwi_util


def print_server_info():
    """Print information about all matlab-proxy servers (with version > 0.4.0) running on this machine"""
    home_folder = mwi_settings.get_mwi_config_folder()

    # Look for files in port folders
    ports_folder = home_folder / "ports"
    search_string = str(ports_folder) + "/**/mwi_server.info"

    print_output = str(
        mwi_util.prettify(
            boundary_filler="-",
            text_arr=["Your running servers are:"],
        )
    )
    print_output += "\n"
    search_results = sorted(glob.glob(search_string), key=os.path.getmtime)
    if len(search_results) == 0:
        print_output += "No MATLAB-PROXY Servers are currently running."
    else:
        server_number = 0
        for server in search_results:
            server_number += 1
            with open(server) as f:
                server_info = f.read()
                print_output += str(server_number) + ".  " + str(server_info)

    print_output += str(
        mwi_util.prettify(
            boundary_filler="-",
            text_arr=["Thank you."],
        )
    )

    return print_output
