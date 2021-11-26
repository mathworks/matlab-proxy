# Copyright 2021 The MathWorks, Inc.
# Enables access to the MATLAB Desktop from a web browser

# Based on the publicly available MATLAB image
FROM mathworks/matlab:r2021b

USER root

# The container already has python3 (v3.8.5) installed
# Install dependencies for matlab-proxy
RUN DEBIAN_FRONTEND=noninteractive && \
    apt-get update && apt-get install --no-install-recommends -y \
    && apt-get install --no-install-recommends -y \
    python3 \
    python3-pip \
    xvfb \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install matlab-proxy

# Set environment variables used by integration
# MATLAB should then become accessible on http://localhost:8888/matlab/index.html
ENV MWI_APP_PORT=8888
ENV MWI_BASE_URL="/matlab"

USER matlab
ENTRYPOINT ["matlab-proxy-app"]
