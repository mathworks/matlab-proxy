% Copyright 2024 The MathWorks, Inc.

% Note:
% Any extra variable we are creating begins with `mwiInternal` to prevent
% potential conflicts with variables created by user code evaluated using evalc.
% Since evalc("user code") is executed in the base workspace, it might create
% variables that could overwrite our internal variables. To avoid polluting the
% user's workspace when MATLAB starts, we ensure to clear any internal variable
% that we create in the base workspace. We do not need to be concerned about
% variables in the function's workspace.

if ~isempty(getenv('MWI_MATLAB_STARTUP_SCRIPT')) && ~all(isspace(getenv('MWI_MATLAB_STARTUP_SCRIPT')))
    try
        % Evaluate the code from the environment variable and capture the output
        mwiInternalResults = evalc(getenv('MWI_MATLAB_STARTUP_SCRIPT'));
        % Write the results to the file
        logOutputOrError(mwiInternalResults);
        clear mwiInternalResults;
    catch mwiInternalException
        % Log the error message to the file
        logOutputOrError(" ", mwiInternalException);
        clear mwiInternalResults mwiInternalException;
        error("Unable to run the startup code you specified. For details of the error, see the output file at " + fullfile(getenv('MATLAB_LOG_DIR'), "startup_code_output.txt"));
    end

end

function logOutputOrError(userCodeResults, mwiInternalException)
    %   Logs the results of the user code execution if successful, otherwise logs the
    %   error information. It then closes the file handle.
    %
    %   Inputs:
    %       userCodeResults       - String containing the output from the user code.
    %       mwiInternalException  - (Optional) MException object containing error details.
    filePath = fullfile(getenv('MATLAB_LOG_DIR'), "startup_code_output.txt");
    [fileHandle, ~] = fopen(filePath, 'w');
    if nargin < 2
        % Log the successful output of the user code
        fprintf(fileHandle, " ");
        fprintf(fileHandle, userCodeResults);
    else
        % Log the error information
        fprintf(fileHandle, 'An error occurred in the following code:\n');
        fprintf(fileHandle, getenv('MWI_MATLAB_STARTUP_SCRIPT'));
        fprintf(fileHandle, '\n\nMessage: %s\n', mwiInternalException.message);
        fprintf(fileHandle, '\nError Identifier: %s\n', mwiInternalException.identifier);
    end
    % Close the file handle
    fclose(fileHandle);
end

