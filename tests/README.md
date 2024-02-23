# Testing Information for matlab-proxy



This document provides instructions for running the test suite for
the MATLAB Proxy project. The test suite is categorized into unit tests
and integration tests, each serving a different purpose in validating
the functionality of the MATLAB Proxy.

The unit tests are fast-running tests to validate the behaviour of individual
methods. Unit tests ensure small sections of the source code (units of code)
operate correctly.

The integration tests validate if the MATLAB Proxy works well in the
presence of a real MATLAB®. It hits the various http-endpoints of MATLAB Proxy
and checks if the response is as expected.

## Unit Tests

The unit tests are written using the
[Pytest](https://docs.pytest.org/en/latest/) and
[Jest](https://jestjs.io/) frameworks.

To run the Python unit tests in this project, follow these steps:
* From the root directory of this project, run the command
  ```
  python3 -m pip install ".[dev]"
  ```
* Run the command to run the python unit tests
  ```
  python3 -m pytest tests/unit
  ```

To run the node unit tests in this project, follow these steps:
* Change the directory to `gui` from the root of this project and run the command
  ```
  npm install
  ```
* Run the 'build' script in package.json
  ```
  npm run build --if-present
  ```
* Run the command to run the node unit tests
  ```
  npm test
  ```

## Integration Tests

The integration tests are written using [Pytest](https://docs.pytest.org/en/latest/)
Python package.

### Integration test requirements
1. MATLAB (Version >= `R2020b`) on the system path
2. MATLAB Proxy should be unlicensed
3. Run the following commands from the root directory of the project:
    ```
    python3 -m pip install ".[dev]"
    python3 -m playwright install --with-deps
    ```
4. MATLAB Proxy requirements
5. Valid MathWorks Account credentials

### How to run the integration tests
* Set the environment variables TEST_USERNAME and TEST_PASSWORD to be your
  MathWorks Account user credentials.
    - Bash (Linux/macOS):
        ```bash
        export TEST_USERNAME="some-username" && TEST_PASSWORD="some-password"
        ```
    - Powershell (Windows):
        ```powershell
        $env:TEST_USERNAME="some-username"; $env:TEST_PASSWORD="some-password"
        ```
* If you need the tests logs to be available in a file, set MWI_INTEG_TESTS_LOG_FILE_PATH
  to the intended path of the log file.
    - Bash (Linux/macOS):
        ```bash
        export MWI_INTEG_TESTS_LOG_FILE_PATH="Path intended"
        ```
    - Powershell (Windows):
        ```powershell
        $env:MWI_INTEG_TESTS_LOG_FILE_PATH="Path intended"
        ```
* Run the following command from the root directory of the project:
    ```
    python3 -m pytest tests/integration -vs
    ```

----
Copyright 2024 The MathWorks, Inc.

----