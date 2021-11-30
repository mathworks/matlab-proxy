# MATLAB Proxy
[![GitHub Workflow Status](https://img.shields.io/github/workflow/status/mathworks/matlab-proxy/Testing%20MATLAB%20Proxy?logo=github)](https://github.com/mathworks/matlab-proxy/actions) [![PyPI badge](https://img.shields.io/pypi/v/matlab-proxy.svg?logo=pypi)](https://pypi.python.org/pypi/matlab-proxy) [![codecov](https://codecov.io/gh/mathworks/matlab-proxy/branch/main/graph/badge.svg?token=ZW3SESKCSS)](https://codecov.io/gh/mathworks/matlab-proxy)

Copyright (c) 2021 The MathWorks, Inc. All rights reserved.

----
`matlab-proxy` is a Python® package which enables you to launch MATLAB® and access it from a web browser.

Installation of this package creates an executable `matlab-proxy-app`, which launches MATLAB and provides a URL to access it. 
 
The MATLAB Proxy is under active development. For support or to report issues, see the [Feedback](#feedback) section.

----
## Requirements
* Linux® operating system

* MATLAB® R2020b or later is installed and on the system PATH.
  ```bash
  # Confirm MATLAB is on the PATH
  which matlab
  ```
* The dependencies required to run MATLAB.
  Refer to the Dockerfiles in the [matlab-deps](https://github.com/mathworks-ref-arch/container-images/tree/master/matlab-deps) repository for the desired version of MATLAB.
* X Virtual Frame Buffer (Xvfb)
  Install it on your linux machine using:
  ```bash
  # On a Debian/Ubuntu based system:
  sudo apt install Xvfb
  ```
  ```bash
  # On a RHEL based system:
  sudo yum install Xvfb
  ```
* Python versions: **3.6** | **3.7** | **3.8** | **3.9** 
* [Browser Requirements](https://www.mathworks.com/support/requirements/browser-requirements.html)

## Installation

### PyPI
This repository can be installed directly from the Python Package Index.
```bash
python -m pip install matlab-proxy
```

### Building From Sources
Building from sources requires Node.js® version 13 or higher. [Click here to install Node.js](https://nodejs.org/en/)

```bash
git clone https://github.com/mathworks/matlab-proxy.git

cd matlab-proxy

python -m pip install .
```

Installing the package creates an executable called `matlab-proxy-app`, which is placed onto your system PATH by `pip`, usually in: `$HOME/.local/bin/`
```bash
# Confirm it is on the PATH
which matlab-proxy-app
```

## Usage

Once the `matlab-proxy` package is installed.

* Open a Linux terminal and launch the application with
  ```bash
  env MWI_BASE_URL="/matlab" matlab-proxy-app
  ```
  `MWI_BASE_URL` is an environment variable which controls the link on which MATLAB can be accessed.
  For a detailed listing of all environment variables. See [Advanced-Usage.md](./Advanced-Usage.md)

  Running the above command will print text out on your terminal, which will contain the URL to access MATLAB. For example:
  ```
  MATLAB can be accessed on 
  http://localhost:44549/matlab/index.html
  ```

* Open the the link above in a web browser. If prompted to do so, enter credentials for a MathWorks account associated with a MATLAB license. If you are using a network license manager, then change to the _Network License Manager_ tab and enter the license server address instead. To determine the appropriate method for your license type, consult [MATLAB Licensing Info](./MATLAB-Licensing-Info.md).
<p align="center">
  <img width="400" src="https://github.com/mathworks/matlab-proxy/raw/main/img/licensing_GUI.png">
</p>

* Wait for the MATLAB session to start. *This can take several minutes*.
<p align="center">
  <img width="800" src="https://github.com/mathworks/matlab-proxy/raw/main/img/MATLAB_Desktop.png">
</p>

* To manage the MATLAB session, click the tools icon shown below.
<p align="center">
  <img width="100" src="https://github.com/mathworks/matlab-proxy/raw/main/img/tools_icon.png">
</p>

* Clicking the tools icon opens a status panel with buttons like the ones below:
<p align="center">
  <img width="800" src="https://github.com/mathworks/matlab-proxy/raw/main/img/status_panel.png">
</p>

The following options are available in the status panel (some options are only available in a specific context):

| Option |  Description |
| ---- | ---- |
| Start MATLAB Session | Start your MATLAB session. Available if MATLAB is stopped.|
| Restart MATLAB Session | Restart your MATLAB session. Available if MATLAB is running or starting.|
| Stop MATLAB Session | Stop your MATLAB session. Use this option if you want to free up RAM and CPU resources. Available if MATLAB is running or starting.|
| Sign Out | Sign out of MATLAB. Use this to stop MATLAB and sign in with an alternative account. Available if using online licensing.|
| Unset License Server Address | Unset network license manager server address. Use this to stop MATLAB and enter new licensing information. Available if using network license manager.|
| Feedback | Send feedback about the MATLAB Proxy. This action opens your default email application.|
| Help | Open a help pop-up for a detailed description of the options.|

## Examples
* For usage in a Docker container, see this [Dockerfile](./examples/Dockerfile) and its [README](./examples/README.md).
* For usage in a Jupyter environment, see [jupyter-matlab-proxy](https://github.com/mathworks/jupyter-matlab-proxy).

## Limitations
This package supports the same subset of MATLAB features and commands as MATLAB® Online, except there is no support for Simulink® Online.
[Click here for a full list of Specifications and Limitations for MATLAB Online](https://www.mathworks.com/products/matlab-online/limitations.html). 


## Feedback

We encourage you to try this repository with your environment and provide feedback. 
If you encounter a technical issue or have an enhancement request, create an issue [here](https://github.com/mathworks/matlab-proxy/issues)