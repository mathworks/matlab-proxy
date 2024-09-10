# MATLAB Proxy Manager

----
This README is intended for MathWorks&reg; developers only.
`matlab-proxy-manager` is part of the `matlab-proxy` package and it helps in managing the lifecycle and proxying of MATLAB proxy processes.

It provides a seamless integration with Jupyter environments, allowing MATLAB to be accessed and controlled via a proxy.

Upon installation, this package introduces an executable `matlab-proxy-manager-app`, which is utilized by the Jupyter Server Proxy to initiate `matlab-proxy-manager`.

----

**Table of Contents**
- [Project Structure](#structure)
- [Installation](#installation)
  - [PyPI](#pypi)
  - [Building From Sources](#building-from-sources)
- [Usage](#usage)
- [Security](#security)

## Structure
`matlab-proxy-manager` is organized into several key sub-folders:

1. lib: 

    * This directory contains the library APIs that facilitate the invocation of MATLAB proxy processes. It supports API calls, enabling the MATLAB Kernel to manage proxy instances effectively. For detailed information, refer to the README within the lib folder.

2. storage: 
    * The file system serves as the source of truth for `matlab-proxy-manager`, storing metadata about each MATLAB proxy server in dedicated files. A new file is generated whenever a proxy instance is launched and is removed upon termination of the instance or deletion of the Kernel that initiated it.

3. web: 
    * This component handles proxy workflows through HTTP/WebSocket requests, which are part of the executable process spawned by clients using the `matlab-proxy-manager-app`. For specific requirements and constraints, consult the README located in the web folder.

4. utils: 
    * A collection of helper functions utilized across various parts of the project, ensuring modularity and code reuse.

## Installation

### PyPI
`matlab-proxy-manager` is included in the `matlab-proxy` repository and can be easily installed from the Python Package Index:

```bash
python -m pip install matlab-proxy
```

### Building From Sources
Building from sources requires Node.js® version 16 or higher. [Click here to install Node.js](https://nodejs.org/en/)

```bash
git clone https://github.com/mathworks/matlab-proxy.git

cd matlab-proxy

python -m pip install .
```

Installing the package creates an executable called `matlab-proxy-app`, which is placed onto your system PATH by `pip`, usually in: `$HOME/.local/bin/`
```bash
# Verify its presence on the PATH
which matlab-proxy-manager-app
```

## Usage
`matlab-proxy-manager` can be deployed in two modes:

1. Library Mode: Import the relevant module within your client code to invoke public APIs directly.

    Example:

    ```python
    import matlab_proxy_manager.lib.api as mpm_lib
    response = await mpm_lib.start_matlab_proxy_for_kernel(...)
    await mpm_lib.shutdown(...)
    ```

2. Process Mode: This mode is primarily managed by Jupyter-Server-Proxy for proxy workflows involving web-based MATLAB desktop access.

## Security
Security is paramount in matlab-proxy-manager. Communication between the Kernel, proxy manager, and Jupyter Server Proxy is secured using authentication tokens. These tokens are mandatory for API invocations and proxy workflows. They are passed via environment variables when the proxy manager is initiated by the Jupyter Server Proxy and are included in the arguments during Kernel API calls.

---

Copyright 2024 The MathWorks, Inc.

---
