// Copyright 2024-2025 The MathWorks, Inc.

import state from './state';

// File containing responses for different endpoints

export const createStatusResponse = {
    matlab: {
        status: state.matlab.status,
        busyStatus: state.matlab.busyStatus,
        version: state.matlab.versionOnPath
    },
    licensing: state.serverStatus.licensingInfo,
    loadUrl: state.loadUrl,
    error: state.error,
    warnings: state.warnings,
    wsEnv: state.serverStatus.wsEnv,
    clientId: 'abcd',
    isActiveClient: true
};

export const authenticateResponse = {
    status: state.authentication.status,
    error: null
};

export const getEnvConfigResponse = {
    doc_url: state.envConfig.doc_url,
    extension_name: state.envConfig.extension_name,
    extension_name_short_description: state.envConfig.extension_name_short_description,
    authentication: state.authentication,
    matlab: {
        version: state.matlab.versionOnPath,
        supportedVersions: state.matlab.supportedVersions
    },
    idleTimeoutDuration: state.idleTimeoutDuration
};
