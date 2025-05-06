% Copyright 2020-2025 The MathWorks, Inc.

evalc('connector.internal.Worker.start');

% Add-on explorer is not supported in this environment.
% The following settings instructs it to display appropriate error messages when used.
matlab_settings = settings;
if ~matlab_settings.matlab.addons.explorer.hasSetting('isExplorerSupported')
    matlab_settings.matlab.addons.explorer.addSetting('isExplorerSupported', 'PersonalValue', true);
end
matlab_settings.matlab.addons.explorer.isExplorerSupported.TemporaryValue = false;

clear
clc
