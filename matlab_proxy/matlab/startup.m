% Copyright 2020-2024 The MathWorks, Inc.

if (strlength(getenv('MWI_BASE_URL')) > 0)
    connector.internal.setConfig('contextRoot', getenv('MWI_BASE_URL'));
end
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
