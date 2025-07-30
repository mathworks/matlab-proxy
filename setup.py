# Copyright 2020-2025 The MathWorks, Inc.
import os
from pathlib import Path
from shutil import which

import setuptools
from setuptools.command.install import install

import matlab_proxy
import matlab_proxy_manager
from matlab_proxy.default_configuration import config


class InstallNpm(install):
    def run(self):
        # Ensure npm is present
        npm_path = which("npm")
        if not npm_path:
            raise Exception(
                "npm must be installed and on the path during package install!"
            )

        npm_install = [npm_path, "install"]
        npm_build = [npm_path, "run", "build"]

        pwd = Path(os.getcwd())
        gui_path = pwd / "gui"

        # Change to directory where GUI files are present
        os.chdir(gui_path)

        # Install dependencies and build GUI files
        self.spawn(npm_install)
        self.spawn(npm_build)

        # Change back to matlab_proxy root folder
        os.chdir(pwd)

        # Copy the built GUI files and move them inside matlab_proxy
        target_dir = Path(self.build_lib) / matlab_proxy.__name__ / "gui"
        self.mkpath(str(target_dir))
        self.copy_tree("gui/build", str(target_dir))

        # In order to be accessible in the package, turn the built gui into modules
        (Path(target_dir) / "__init__.py").touch(exist_ok=True)
        for path, directories, filenames in os.walk(target_dir):
            for directory in directories:
                (Path(path) / directory / "__init__.py").touch(exist_ok=True)

        super().run()


# Testing dependencies
# Note: pytest-asyncio is pinned to 0.24.0 for event loop compatibility
TESTS_REQUIRES = [
    "pytest",
    "pytest-env",
    "pytest-cov",
    "pytest-timeout",
    "pytest-mock",
    "pytest-aiohttp",
    "pytest-timeout",
    "psutil",
    "urllib3",
    "pytest-playwright",
    "pytest-asyncio==0.24.0",
]

INSTALL_REQUIRES = [
    "aiohttp>=3.7.4",
    "aiohttp_session[secure]",
    "importlib-metadata",
    "importlib-resources",
    "psutil",
    "watchdog",
    "requests",
]

HERE = Path(__file__).parent.resolve()
long_description = (HERE / "README.md").read_text()

setuptools.setup(
    name="matlab-proxy",
    version="0.26.0",
    url=config["doc_url"],
    author="The MathWorks, Inc.",
    author_email="cloud@mathworks.com",
    license="MATHWORKS CLOUD REFERENCE ARCHITECTURE LICENSE",
    description="Python® package enables you to launch MATLAB® and access it from a web browser.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=setuptools.find_packages(exclude=["devel", "tests", "anaconda"]),
    keywords=[
        "Proxy",
        "MATLAB Proxy",
        "MATLAB",
        "MATLAB Javascript Desktop",
        "MATLAB Web Desktop",
        "Remote MATLAB Web Access",
    ],
    classifiers=[
        "Intended Audience :: Developers",
        "Natural Language :: English",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires="~=3.8",
    install_requires=INSTALL_REQUIRES,
    tests_require=TESTS_REQUIRES,
    extras_require={"dev": ["aiohttp-devtools", "black", "ruff"] + TESTS_REQUIRES},
    # The entrypoint will be used by multiple packages that have this package as an installation
    # dependency. These packages can use the same API, get_entrypoint_name(), to make their configs discoverable
    entry_points={
        matlab_proxy.get_entrypoint_name(): [
            f"{matlab_proxy.get_default_config_name()} = matlab_proxy.default_configuration:config"
        ],
        "console_scripts": [
            f"{matlab_proxy.get_executable_name()} = matlab_proxy.app:main",
            f"{matlab_proxy.get_executable_name()}-list-servers = matlab_proxy.util.list_servers:print_server_info",
            f"{matlab_proxy_manager.get_executable_name()} = matlab_proxy_manager.web.app:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
    cmdclass={"install": InstallNpm},
)
