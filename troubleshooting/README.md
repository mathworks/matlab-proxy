# Troubleshooting guide for MATLAB proxy
Use the `troubleshooting.py` script to check your environment for required dependencies.

## Table of Contents  
1. [Requirements](#requirements)
2. [Running the Script](#running-the-script)
3. [Collecting Logs](#collecting-logs)

# Requirements
* Python


# Running the Script
From the folder where this repository is cloned, you can run the following command to gather troubleshooting output:
```bash
$ python ./troubleshooting/troubleshooting.py
```
# Collecting Logs
If you collect matlab-proxy logs using the **MWI_LOG_FILE** environment variable, we recommend that you provide the same variable when executing the troubleshooting script. This allows the script to gather the relevant logs for analysis.

An example command to do that in linux would be:
```bash 
$ MWI_LOG_FILE=/tmp/log.file python ./troubleshooting/troubleshooting.py
``` 

----

Copyright 2021-2023 The MathWorks, Inc.

----
