# Troubleshooting guide for MATLAB proxy
Runs basic environment checks to determine if required dependencies are met or not.


## Table of Contents  
1. [Requirements](#requirements)
2. [Script invocation](#script-invocation)
3. [Collecting matlab-proxy logs](#collecting-matlab-proxy-logs)

# Requirements
* Python


# Script invocation
From the folder where this repository is cloned, you can run the following command to gather troubleshooting output:
`python ./troubleshooting/troubleshooting.py`

# Collecting MATLAB proxy logs
If you are logging MATLAB proxy information into a log file using the **MWI_LOG_FILE** environment variable when initializing the matlab-proxy-app, we recommend that you also provide the same environment variable when executing the troubleshooting script. This ensures that the script can detect and gather the relevant logs for analysis.

An example command to do that in linux would be:
`MWI_LOG_FILE=/tmp/log.file python ./troubleshooting/troubleshooting.py` 

----

Copyright 2021-2023 The MathWorks, Inc.

----



