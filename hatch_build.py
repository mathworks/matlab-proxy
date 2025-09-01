# Copyright 2025 The MathWorks, Inc.

import os
import subprocess
from pathlib import Path
from shutil import copytree, which
from typing import Any, Dict

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    #  Identifier that connects this Python hook class to pyproject.toml configuration
    PLUGIN_NAME = "custom"

    def initialize(self, version: str, build_data: Dict[str, Any]) -> None:
        """Run npm install and build, then copy files to package."""

        # Ensure npm is present
        npm_path = which("npm")
        if not npm_path:
            raise Exception(
                "npm must be installed and on the path during package build!"
            )

        # Adding retries to npm install to avoid transient rate limiting issues
        npm_install = [npm_path, "install", "--fetch-retries", "10"]
        npm_build = [npm_path, "run", "build"]

        pwd = Path.cwd()
        gui_path = pwd / "gui"
        gui_build_path = gui_path / "build"

        if not gui_path.exists():
            raise Exception(f"GUI directory not found: {gui_path}")

        # Cleanup the build folder to ensure latest artifacts are generated
        if gui_build_path.exists():
            import shutil

            shutil.rmtree(gui_build_path)

        # Change to directory where GUI files are present
        original_cwd = str(pwd)
        os.chdir(gui_path)

        try:
            # Install dependencies and build GUI files
            subprocess.run(npm_install, check=True)
            subprocess.run(npm_build, check=True)
        finally:
            os.chdir(original_cwd)

        if not gui_build_path.exists():
            raise Exception(f"GUI build directory not found: {gui_build_path}")

        # Copy built files to a temporary location that will be included in wheel
        temp_gui_path = pwd / "matlab_proxy" / "gui"
        temp_gui_path.mkdir(parents=True, exist_ok=True)

        # Cleanup pre-existing gui files
        if temp_gui_path.exists():
            import shutil

            shutil.rmtree(temp_gui_path)

        copytree(gui_build_path, temp_gui_path)

        # Create __init__.py files to make directories into Python modules
        (temp_gui_path / "__init__.py").touch(exist_ok=True)
        for root, dirs, _ in os.walk(temp_gui_path):
            for directory in dirs:
                (Path(root) / directory / "__init__.py").touch(exist_ok=True)
        print("Build hook step completed!")
