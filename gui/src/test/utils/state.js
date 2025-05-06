// Copyright 2023-2025 The MathWorks, Inc.

// A common state variable meant to represent redux state to be used by different tests.
const state = {
    overlayVisibility: true,
    triggerPosition: {
        x: 12,
        y: 12
    },
    tutorialHidden: true,
    loadUrl: '/',
    error: null,
    warnings: [],
    serverStatus: {
        wsEnv: 'integ',
        isSubmitting: true,
        hasFetched: false,
        isFetchingServerStatus: false,
        licensingInfo: {
            type: 'mhlm',
            emailAddress: 'abc@mathworks.com',
            entitlements: [
                { id: '1234567', label: null, license_number: '7654321' },
                {
                    id: '2345678',
                    label: 'MATLAB - Staff Use',
                    license_number: '87654432'
                }
            ],
            entitlementId: null
        },
        fetchFailCount: 2
    },
    envConfig: {
        doc_url: 'https://github.com/mathworks/matlab-proxy/',
        extension_name: 'default_configuration_matlab_proxy',
        extension_name_short_description: 'MATLAB Desktop',
        should_show_shutdown_button: true
    },
    matlab: {
        status: 'up',
        versionOnPath: 'R2023b',
        supportedVersions: ['R2020b', 'R2023b'],
        busyStatus: 'idle',
    },
    authentication: {
        enabled: false,
        status: false,
        token: null
    },
    sessionStatus: {
        isActiveClient: true,
        hasClientInitialized: false,
        wasEverActive: false,
        isConcurrencyEnabled: false,
        clientId: null
    },
    idleTimeoutDuration: null
};
export default state;
