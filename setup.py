# Copyright 2020-2021 The MathWorks, Inc.
import os
from setuptools.command.install import install
import setuptools
import matlab_proxy
from pathlib import Path
from shutil import which
from matlab_proxy.default_configuration import config

npm_install = ["npm", "--prefix", "gui", "install", "gui"]
npm_build = ["npm", "run", "--prefix", "gui", "build"]


class InstallNpm(install):
    def run(self):

        # Ensure npm is present
        if which("npm") is None:
            raise Exception(
                "npm must be installed and on the path during package install!"
            )

        self.spawn(npm_install)
        self.spawn(npm_build)
        target_dir = Path(self.build_lib) / matlab_proxy.__name__ / "gui"
        self.mkpath(str(target_dir))
        self.copy_tree("gui/build", str(target_dir))

        # In order to be accessible in the package, turn the built gui into modules
        (Path(target_dir) / "__init__.py").touch(exist_ok=True)
        for (path, directories, filenames) in os.walk(target_dir):
            for directory in directories:
                (Path(path) / directory / "__init__.py").touch(exist_ok=True)

        super().run()


tests_require = [
    "pytest",
    "pytest-env",
    "pytest-cov",
    "pytest-mock",
    "pytest-aiohttp",
    "requests",
    "psutil",
]

HERE = Path(__file__).parent.resolve()
long_description = (HERE / "README.md").read_text()


setuptools.setup(
    name="matlab-proxy",
    version="0.2.2",
    url=config["doc_url"],
    author="The MathWorks, Inc.",
    author_email="cloud@mathworks.com",
    license="MATHWORKS CLOUD REFERENCE ARCHITECTURE LICENSE",
    description="Python® package enables you to open a MATLAB® desktop in a web browser tab.",
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
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
    python_requires="~=3.6",
    install_requires=["aiohttp>=3.7.4"],
    tests_require=tests_require,
    extras_require={
        "dev": ["aiohttp-devtools", "black", "ruamel.yaml"] + tests_require
    },
    # The entrypoint will be used by multiple packages that have this package as an installation
    # dependency. These packages can use the same API, get_entrypoint_name(), to make their configs discoverable
    entry_points={
        matlab_proxy.get_entrypoint_name(): [
            f"{matlab_proxy.get_default_config_name()} = matlab_proxy.default_configuration:config"
        ],
        "console_scripts": [
            f"{matlab_proxy.get_executable_name()} = matlab_proxy.app:main"
        ],
    },
    include_package_data=True,
    zip_safe=False,
    cmdclass={"install": InstallNpm},
)
