# Copyright 2020-2022 The MathWorks, Inc.

import asyncio
import os
import sys
import time

"""This file launches an asynchrnous infinite loop.
    Used for testing matlab_proxy/util/__init__.py/get_child_processes
"""

process_no = int(sys.argv[1])

loop = asyncio.get_event_loop()


# Runs infinite loop asynchronously
async def inf_loop(process_no):
    process_no += 1
    inf_loop_file_path = os.path.join(os.path.dirname(__file__), "inf_loop.py")
    cmd = [f"python {inf_loop_file_path} {process_no}"]
    _ = await asyncio.create_subprocess_shell(*cmd)
    while True:
        time.sleep(1)


# Allows only one python process
if process_no < 2:
    loop.run_until_complete(inf_loop(process_no))
