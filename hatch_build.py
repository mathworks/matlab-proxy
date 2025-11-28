# Copyright 2025 The MathWorks, Inc.

import os
import subprocess
from pathlib import Path
from shutil import which
from typing import Any, Dict

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

MIN_NPM_VERSION = "11.6"


def _ensure_npm_compatibility(npm_path: str) -> None:
    """
    Raises :
        OSError: If npm version is incompatible.
    """
    # Verify npm version is v11.6 or newer
    result = subprocess.run(
        [npm_path, "--version"], capture_output=True, text=True, check=True
    )
    version_str = result.stdout.strip()
    version_parts = version_str.lstrip("v").split(".")
    major, minor = int(version_parts[0]), int(version_parts[1])
    min_major, min_minor = map(int, MIN_NPM_VERSION.split("."))
    if (major, minor) < (min_major, min_minor):
        raise OSError(
            f"npm version {version_str} is not supported. Please upgrade to v{min_major}.{min_minor} or newer."
        )
    return


def _get_npm() -> Path:
    """
    Returns:
      path to npm executable,
    Raises:
     OsError: if not found or incompatible.
    """
    npm_path = which("npm")
    if npm_path is None:
        raise OSError(
            "npm is not installed or not found in PATH. Please install Node.js and npm to proceed."
        )
    _ensure_npm_compatibility(npm_path)
    return Path(npm_path)


def _finalize_target_dir(target_dir: Path) -> None:
    """Prepares target directory to be read as python modules and leaves build marker file."""
    # Create __init__.py files to make directories into Python modules
    (target_dir / "__init__.py").touch(exist_ok=True)
    for root, dirs, _ in os.walk(target_dir):
        for directory in dirs:
            (Path(root) / directory / "__init__.py").touch(exist_ok=True)


class CustomBuildHook(BuildHookInterface):
    #  Identifier that connects this Python hook class to pyproject.toml configuration
    PLUGIN_NAME = "custom"

    def initialize(self, version: str, build_data: Dict[str, Any]) -> None:
        """Run npm install and build, then copy files to package."""

        project_root = Path.cwd()
        src_dir = project_root / "gui"
        target_dir = project_root / "matlab_proxy" / "gui"

        if os.environ.get("MWI_SKIP_NPM_BUILD"):
            print(
                "Skipping npm build process as MWI_SKIP_NPM_BUILD environment variable is set."
            )
            return

        npm_path = _get_npm()

        try:
            os.chdir(src_dir)

            # Adding retries to npm install to avoid transient rate limiting issues
            npm_install_cmd = [npm_path, "install", "--fetch-retries", "10"]
            # "npm install" creates: node_modules, package-lock.json
            subprocess.run(npm_install_cmd, check=True)
            print("npm installation completed successfully.")

            # "npm build" runs "vite build" which writes the results to the target directory
            npm_build_cmd = [npm_path, "run", "build"]
            subprocess.run(npm_build_cmd, check=True)
            _finalize_target_dir(target_dir=target_dir)
            print("npm build completed successfully.")
        finally:
            # Reset working directory
            os.chdir(project_root)

        print("Build hook step completed!")
