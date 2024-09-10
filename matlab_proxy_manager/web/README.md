# MATLAB Proxy Manager - Web

This README is intended for MathWorks&reg; developers only.
The web module is an important component of the matlab-proxy-manager, responsible for initiating the proxy manager in process mode. This module is specifically designed to be utilized within the Jupyter ecosystem, facilitating seamless integration with Jupyter Server Proxy.

## Key Features
### Process Mode Execution:

The web module contains the code necessary to start the MATLAB proxy manager in process mode. This mode is essential for managing MATLAB sessions within a Jupyter environment, allowing users to interact with MATLAB through a web-based interface.

### Integration with Jupyter Server Proxy:

The web module is accessed exclusively by the Jupyter Server Proxy. It ensures that MATLAB can be launched and managed effectively as part of a Jupyter session, providing a seamless user experience.

### Environment Variable Configuration:

The web module relies on three critical environment variables to function correctly:
1. MWI_MPM_PORT: Specifies the port on which the proxy manager should start. This allows for flexible configuration and ensures that the proxy manager can be accessed on the appropriate network endpoint.
2. MWI_MPM_AUTH_TOKEN: Used for secure communication between the Jupyter Server Proxy and the proxy manager. This token ensures that only authorized requests can interact with the proxy manager, enhancing security.
3. MWI_MPM_PARENT_PID: Provides context for the process, allowing resources to be filtered based on their originating parent process. This is particularly useful for distinguishing resources started by different Jupyter servers.

### Support for Proxy Workflow:

The web module supports the proxy workflow, which is activated when the MATLAB Web Desktop is launched. This workflow ensures that users can access MATLAB's graphical interface through their web browser, maintaining a consistent and interactive experience.

## Usage
The web module is typically invoked by the Jupyter Server Proxy and does not require direct interaction from end-users. However, it is essential to ensure that the necessary environment variables are correctly set before launching the module.

## Design Considerations
1. Security: The use of an authentication token ensures secure communication between components, preventing unauthorized access.
2. Flexibility: By leveraging environment variables, the web module can be easily configured to meet the specific needs of different deployment environments.

---

Copyright 2024 The MathWorks, Inc.

---