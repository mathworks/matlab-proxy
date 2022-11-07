# Copyright (c) 2020-2022 The MathWorks, Inc.
from matlab_proxy.util import system


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


def __get_matlab_proxy_base_ddux_value():
    """Returns the DDUX value for MATLAB use when launched its by matlab-proxy

    Returns:
        str : DDUX value for MATLAB use.
    """
    return f"MATLAB_PROXY:BASE:V1"


def get_mwi_ddux_value(extension_name):
    """Returns DDUX value for matlab-proxy based on the context from which
    it is being launched from.

    Args:
        extension_name (str): The name of the extension/environment

    Returns:
        str: DDUX value for matlab-proxy based on the environment.
    """
    matlab_proxy_ddux_value = __get_matlab_proxy_base_ddux_value()

    if extension_name == get_default_config_name():
        return matlab_proxy_ddux_value
    else:
        variant = extension_name.upper().strip()
        variant = variant.replace(" ", "_").replace("-", "_")
        mwi_ddux_value = matlab_proxy_ddux_value.replace("BASE", variant)
        return mwi_ddux_value
