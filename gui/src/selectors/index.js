// Copyright 2020-2023 The MathWorks, Inc.

import { createSelector } from 'reselect';

export const selectTutorialHidden = state => state.tutorialHidden;
export const selectServerStatus = state => state.serverStatus;
export const selectMatlabStatus = state => state.serverStatus.matlabStatus;
export const selectWsEnv = state => state.serverStatus.wsEnv;
export const selectSubmittingServerStatus = state => state.serverStatus.isSubmitting;
export const selectHasFetchedServerStatus = state => state.serverStatus.hasFetched;
export const selectLicensingInfo = state => state.serverStatus.licensingInfo;
export const selectServerStatusFetchFailCount = state => state.serverStatus.fetchFailCount;
export const selectLoadUrl = state => state.loadUrl;
export const selectError = state => state.error;
export const selectAuthEnabled = state => state.authInfo.authEnabled;
export const selectAuthToken = state => state.authInfo.authToken;
export const selectIsAuthenticated = state => state.authInfo.authStatus === true;

export const selectTriggerPosition = createSelector(
    state => state.triggerPosition,
    pos => pos === null ? undefined : pos
);

export const selectHasFetchedEnvConfig = createSelector(
    (state) => state.envConfig,
    (config) => (config === null ? false : config)
);

export const selectIsError = createSelector(
    selectError,
    error => error !== null
);

export const selectIsConnectionError = createSelector(
    selectServerStatusFetchFailCount,
    fails => fails >= 5
);

export const selectMatlabUp = createSelector(
    selectMatlabStatus,
    matlabStatus => matlabStatus === 'up'
);

export const selectMatlabStarting = createSelector(
    selectMatlabStatus,
    matlabStatus => matlabStatus === 'starting'
);

export const selectMatlabStopping = createSelector(
    selectMatlabStatus,
    matlabStatus => matlabStatus === 'stopping'
);

export const selectMatlabDown = createSelector(
    selectMatlabStatus,
    matlabStatus => matlabStatus === 'down'
);

export const selectOverlayHidable = createSelector(
    selectMatlabStatus,
    selectIsError,
    selectAuthEnabled,
    selectIsAuthenticated,
    (matlabStatus, isError, authRequired, isAuthenticated) => ((matlabStatus === 'up') && !isError && (!authRequired || isAuthenticated))
);

export const selectOverlayVisibility = createSelector(
    state => state.overlayVisibility,
    selectMatlabUp,
    selectIsError,
    selectAuthEnabled,
    selectIsAuthenticated,
    (visibility, matlabUp, isError, authRequired, isAuthenticated) => (
        (authRequired && !isAuthenticated) || !matlabUp || visibility || isError
    )
);

export const getFetchAbortController = createSelector(
    selectServerStatus,
    serverStatus => serverStatus.fetchAbortController
);

export const selectFetchStatusPeriod = createSelector(
    selectMatlabStatus,
    selectSubmittingServerStatus,
    (matlabStatus, isSubmitting) => {
        if (isSubmitting) {
            return null;
        } else if (matlabStatus === 'up') {
            return 10000;
        }
        return 5000;
    }
);

export const selectLicensingProvided = createSelector(
    selectLicensingInfo,
    licensingInfo => Object.prototype.hasOwnProperty.call(licensingInfo, 'type')
);

export const selectLicensingIsMhlm = createSelector(
    selectLicensingInfo,
    selectLicensingProvided,
    (licensingInfo, licensingProvided) => licensingProvided && licensingInfo.type === 'mhlm'
);

export const selectLicensingMhlmUsername = createSelector(
    selectLicensingInfo,
    selectLicensingIsMhlm,
    (licensingInfo, isMhlm) => isMhlm ? licensingInfo.emailAddress : ''
);

// Selector to check if the license type is mhlm and entitlements property is not empty
export const selectLicensingMhlmHasEntitlements = createSelector(
    selectLicensingIsMhlm,
    selectLicensingInfo,
    (isMhlm, licensingInfo) => isMhlm && licensingInfo.entitlements && licensingInfo.entitlements.length > 0
);

export const selectIsEntitled = createSelector(
    selectLicensingInfo,
    selectLicensingMhlmHasEntitlements,
    (licensingInfo, entitlementIdInfo) => entitlementIdInfo && licensingInfo.entitlementId
);

// TODO Are these overkill? Perhaps just selecting status would be enough
// TODO Could be used for detected intermediate failures, such as server being
// temporarily inaccessible
export const selectMatlabPending = createSelector(
    selectMatlabStatus,
    matlabStatus => matlabStatus === 'starting'
);

export const selectOverlayVisible = createSelector(
    selectOverlayVisibility,
    selectIsError,
    (visibility, isError) => (visibility || isError)
);

export const selectIsInvalidTokenError = createSelector(
    selectAuthEnabled,
    selectIsAuthenticated,
    selectIsError,
    selectError,
    (authEnabled, isAuthenticated, isError, error) => {
        if ((authEnabled && !isAuthenticated) && isError && error.type === "InvalidTokenError") {
            return true
        }
        return false
    }
)

export const selectInformationDetails = createSelector(
    selectMatlabStatus,
    selectIsError,
    selectError,
    selectAuthEnabled,
    selectIsInvalidTokenError,
    (matlabStatus, isError, error, authEnabled, isInvalidTokenError) => {
        // Check for any errors on the front-end 
        // to see if HTTP Requests are timing out.       
        if (isError && error.statusCode === 408) {
            return {
                icon: 'warning',
                alert: 'warning',
                label: 'Unknown',
            }
        }

        if (isError && authEnabled && isInvalidTokenError) {
            return {
                icon: 'warning',
                alert: 'warning',
                label: 'Invalid Token supplied',
            }
        }

        // Check status of MATLAB for errors
        switch (matlabStatus) {
            case 'up':
                return {
                    label: 'Running',
                    icon: 'success',
                    alert: 'success'
                };
            case 'starting':
                return {
                    label: 'Starting. This may take several minutes.',
                    icon: 'info-reverse',
                    alert: 'info',
                    spinner: true
                };

            case 'stopping':
                return {
                    label: 'Stopping',
                    icon: 'info-reverse',
                    alert: 'info',
                    spinner: true
                };
            case 'down':
                const detail = {
                    label: 'Not running',
                    icon: 'info-reverse',
                    alert: 'info'
                };
                if (isError) {
                    detail.icon = 'error';
                    detail.alert = 'danger';
                }
                return detail;
            default:
                throw new Error(`Unknown MATLAB status: "${matlabStatus}".`);
        }

    }
);
