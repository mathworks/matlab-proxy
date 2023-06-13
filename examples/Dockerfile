# Copyright (c) 2020-2022 The MathWorks, Inc.
# This Dockerfile showcases how to add matlab-proxy into an existing container image with MATLAB installed.

# matlab-proxy enables access to the MATLAB Desktop from a web browser

# Sample build command:
# docker build  --build-arg IMAGE_WITH_MATLAB=my_custom_image_with_matlab \
#               -f Dockerfile -t my_custom_image_with_matlab_proxy .

# Sample run command:
# docker run --rm -it -p 8888:8888 --shm-shared=512M my_custom_image_with_matlab_proxy

ARG IMAGE_WITH_MATLAB=mathworks/matlab:r2022a

FROM ${IMAGE_WITH_MATLAB}

USER root

# Install dependencies for matlab-proxy
RUN DEBIAN_FRONTEND=noninteractive && \
    apt-get update && apt-get install --no-install-recommends -y \
    python3 \
    python3-pip \
    xvfb \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install matlab-proxy

# Set environment variables used by integration
# MATLAB should then become accessible on http://localhost:8888/matlab/index.html
ENV MWI_APP_PORT=8888
ENV MWI_BASE_URL="/matlab"

USER matlab
ENTRYPOINT ["matlab-proxy-app"]