# MATLAB Proxy Manager - Library

This README is intended for MathWorks&reg; developers only.
`matlab-proxy-manager` module is designed to be flexible and robust, supporting both direct library calls and process-based workflows. The lib folder contains the code blocks providing the core library APIs that facilitate the management of MATLAB proxy instances.

# Key Features
## API Invocation:

The lib module allows for the invocation of MATLAB proxy processes through a well-defined set of APIs. These APIs are designed to be intuitive and easy to integrate into existing workflows, enabling developers to start, stop, and manage MATLAB proxy instances programmatically.

## Integration with MATLAB Kernel:

The APIs in the lib directory are used by the MATLAB Kernel to manage the lifecycle of MATLAB proxy instances. This includes starting new instances and shutting them down when they are no longer needed.

## Error Handling and Logging:

Comprehensive error handling mechanisms are in place to ensure that any issues encountered during the management of proxy instances are logged and reported. This aids in troubleshooting and ensures the reliability of the system. 

Users are required to set `MWI_MPM_LOG_LEVEL` environment variable to their desired log level (`INFO`, `DEBUG` etc.) to enable logging in `matlab-proxy-manager`.

# Usage
To use the lib APIs, you can import the relevant module in your Python code and invoke the provided functions. Here’s a basic example of how you might start and stop a MATLAB proxy instance:

```python

import matlab_proxy_manager.lib.api as mpm_lib

# Start a MATLAB proxy instance
response = await mpm_lib.start_matlab_proxy_for_kernel(
                caller_id=self.kernel_id,
                parent_id=self.parent_pid,
                is_shared_matlab=True,
            )
return (
    response.get("absolute_url"),
    response.get("mwi_base_url"),
    response.get("headers"),
    response.get("mpm_auth_token"),
)

# Perform operations with the MATLAB instance...

# Shut down the MATLAB proxy instance
await mpm_lib.shutdown(
    self.parent_pid, self.kernel_id, self.mpm_auth_token
)
```

---

Copyright 2024 The MathWorks, Inc.

---
