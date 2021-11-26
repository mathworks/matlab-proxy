# Copyright 2020-2021 The MathWorks, Inc.
import matlab_proxy

# Configure matlab_proxy
config = {
    # Link the documentation url here. This will show up on the website UI
    # where users can create issue's or make enhancement requests
    "doc_url": "https://github.com/mathworks/matlab-proxy/",
    # Use a single word for extension_name
    # It will be used as a flag when launching the integration.
    # NOTE: This name must be used when setting the entrypoint for matlab_proxy in setup.py
    "extension_name": matlab_proxy.get_default_config_name(),
    # This value will be used in various places on the website UI.
    # Ensure that this is not more than 3 words.
    "extension_name_short_description": "MATLAB Desktop",
}
