# Testing Information for matlab-proxy


This page shows how to run unit and integration tests for matlab-proxy.

The unit tests quickly validate individual
methods. The integration tests check that `matlab-proxy` works well with MATLAB®, by testing HTTP endpoints for correct responses.

## Unit Tests

The unit tests are written using the
[Pytest](https://docs.pytest.org/en/latest/) and
[Jest](https://jestjs.io/) frameworks.

To run the Python unit tests in this project, follow these steps.

1. From the root directory of this project, run:
  ```
  python3 -m pip install ".[dev]"
  ```
2. Run the unit tests:
  ```
  python3 -m pytest tests/unit
  ```

To run the Node unit tests follow these steps.

1. From the project root, change to the `gui` folder and run:
  ```
  npm install
  ```
2. Run the `build` script in `package.json`:
  ```
  npm run build --if-present
  ```
3. Run the Node unit tests:
  ```
  npm test
  ```

## Integration Tests

The integration tests are written using the [Pytest](https://docs.pytest.org/en/latest/)
Python package.

### Integration Test Requirements


1. Ensure that MATLAB R2020b or later is on the system path
2. From the project root folder, run:
    ```
    python3 -m pip install ".[dev]"
    python3 -m playwright install --with-deps
    ```
3. Ensure that your system meets the `matlab-proxy` [Requirements](https://github.com/mathworks/matlab-proxy#requirements)
4. Ensure that you have valid MathWorks account credentials

### Run Integration Tests

Start by licensing `matlab-proxy`. If it is already licensed, skip the first two steps.

1. Start MATLAB Proxy using `matlab-proxy-app`
1. Use the dialog to license MATLAB Proxy using online licensing, network license manager, or an existing license.
1. If you want the tests to be logged in a file, set the variable `MWI_INTEG_TESTS_LOG_FILE_PATH`
  to the path of your log file:

    - Bash (Linux/macOS):
        ```bash
        export MWI_INTEG_TESTS_LOG_FILE_PATH="Desired Path"
        ```
    - Powershell (Windows):
        ```powershell
        $env:MWI_INTEG_TESTS_LOG_FILE_PATH="Desired Path"
        ```
1. From the project root folder, run:
    ```
    python3 -m pytest tests/integration -vs
    ```

----
Copyright 2024 The MathWorks, Inc.

----