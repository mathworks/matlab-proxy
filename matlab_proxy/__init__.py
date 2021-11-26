# Copyright 2020-2021 The MathWorks, Inc.


def get_entrypoint_name():
    """Returns the entry_point name which will be registered when installing the package.

    Returns:
        str: entry_point name which will be used to register when installing this package.
    """
    return "matlab_proxy_configs"


def get_default_config_name():
    """Returns the default config name which will be used to launch the integration

    Returns:
        Str: default config name
    """
    return "default_configuration_matlab_proxy"


def get_executable_name():
    """Returns the executable name used to launch the integration

    Returns:
        str: Name of the executable
    """
    return "matlab-proxy-app"
