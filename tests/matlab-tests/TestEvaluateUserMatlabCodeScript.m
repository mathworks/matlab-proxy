% Copyright 2024-2025 The MathWorks, Inc.

classdef TestEvaluateUserMatlabCodeScript < matlab.unittest.TestCase
% TestEvaluateUserMatlabCodeScript contains unit tests for the complete function

    properties
        OriginalMWI_MATLAB_STARTUP_SCRIPT
        LogDir
        LogFile
        TestPaths
    end

    methods (TestClassSetup)
        function addFunctionPath(testCase)
            testCase.TestPaths = cellfun(@(relative_path)(fullfile(pwd, relative_path)), {"../../matlab_proxy/matlab/", "../../tests/matlab-tests/"}, 'UniformOutput', false);
            cellfun(@addpath, testCase.TestPaths)
        end
    end

    methods (TestClassTeardown)
        function removeFunctionPath(testCase)
            cellfun(@rmpath, testCase.TestPaths)
        end
    end

    methods (TestMethodSetup)
        function setupEnvironmentVariables(testCase)
            testCase.OriginalMWI_MATLAB_STARTUP_SCRIPT = getenv('MWI_MATLAB_STARTUP_SCRIPT');
            testCase.LogDir = tempname;
            mkdir(testCase.LogDir);

            % Check if the directory is writable by attempting to create a test file
            testFile = fullfile(testCase.LogDir, 'test_write_permission.txt');
            fid = fopen(testFile, 'w');
            if fid == -1
                error('The temporary directory is not writable.');
            else
                fclose(fid);
                delete(testFile);
            end

            setenv('MATLAB_LOG_DIR', testCase.LogDir);
            testCase.LogFile = fullfile(testCase.LogDir, "startup_code_output.txt");
        end
    end

    methods (TestMethodTeardown)
        function restoreEnvironmentVariables(testCase)
            setenv('MWI_MATLAB_STARTUP_SCRIPT', testCase.OriginalMWI_MATLAB_STARTUP_SCRIPT);
            rmdir(testCase.LogDir, 's');
        end
    end

    methods (Test)
        function testSuccessfulStartupCodeExecution(testCase)
        % Test successful start up code functionality

            setenv('MWI_MATLAB_STARTUP_SCRIPT', 'disp(42)');
            % Verify the log file contains the expected output
            evaluateUserMatlabCode();
            text = fileread(testCase.LogFile);
            testCase.verifyTrue(contains(text, '42'));
        end

        function testInvalidScript(testCase)
        % Test with an invalid code

            setenv('MWI_MATLAB_STARTUP_SCRIPT', 'a+1');

            % Use try-catch to handle the error and allow the test to continue
            try
                evaluateUserMatlabCode();
            catch
                % Expected to catch an error, proceed to verify the log file
                disp("Checking the error log file");
            end

            % Verify the error log file
            testCase.verifyTrue(isfile(testCase.LogFile));
            logContent = fileread(testCase.LogFile);
            testCase.verifyTrue(contains(logContent, 'An error occurred in the following code:'));
            testCase.verifyTrue(contains(logContent, 'MATLAB:UndefinedFunction'));
        end

        function testVariableCreationInBaseWorkspace(testCase)
            % Test that a variable created in the startup script exists in the workspace
            setenv('MWI_MATLAB_STARTUP_SCRIPT', 'myStartupVar = 10;');
            evaluateUserMatlabCode();
            % Check variable existence and value
            varExists = eval("exist('myStartupVar', 'var')");
            assert(varExists == 1, 'myStartupVar should exist in workspace');
            varValue = eval("myStartupVar");
            assert(varValue == 10, 'myStartupVar should have value 10');
        end
    end
end
