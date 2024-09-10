# MATLAB Proxy Manager - Storage

This README is intended for MathWorks&reg; developers only.
The storage module is a critical part of the `matlab-proxy-manager`, responsible for managing the persistence of metadata related to MATLAB proxy instances. It employs a repository pattern to provide a clean and consistent interface for performing CRD (Create, Read, Delete) operations on the file system.

## Key Features

### Repository Pattern:

The storage module is designed using the repository pattern, which abstracts the data layer and provides a straightforward API for interacting with stored metadata. This pattern ensures that the underlying data storage mechanism can be modified or replaced with minimal impact on the rest of the application.

### File System-Based Storage:

Currently, the storage operations are performed directly on the file system. Each MATLAB proxy instance's metadata is stored in a separate file, making it easy to manage and access individual instances.

### CRD Operations:

The storage module provides a set of APIs to perform CRD operations:

1. add(...): Create a new metadata file for a MATLAB proxy instance.
2. get(...): Retrieve metadata for a specific instance.
3. get_all(): Retrieve metadata for all instances.
4. delete(...): Remove the metadata file for a specific instance.

Usage
To use the storage APIs, clients can import the relevant module and invoke the provided functions. Here’s an example of how to perform basic CRUD operations:

```python

from matlab_proxy_manager.storage.file_repository import FileRepository

storage = FileRepository(data_dir)

# Add a new MATLAB proxy instance metadata
filename = '1234.info'
server_process = <instance of ServerProcess class>
storage.add(server=server_process, filename=filename)

# Retrieve metadata for a specific instance
filename = f"{parent_pid}_{caller_id}"
full_file_path, server = storage.get(filename)

# Retrieve metadata for all instances
servers = storage.get_all()

# Delete metadata for a specific instance
storage.delete(f"{filename}.info")
```

---

Copyright 2024 The MathWorks, Inc.

---