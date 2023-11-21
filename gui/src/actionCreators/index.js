// Copyright 2020-2023 The MathWorks, Inc.

import {
    SET_TRIGGER_POSITION,
    SET_TUTORIAL_HIDDEN,
    SET_OVERLAY_VISIBILITY,
    REQUEST_SERVER_STATUS,
    RECEIVE_SERVER_STATUS,
    REQUEST_SET_LICENSING,
    REQUEST_UPDATE_LICENSING,
    REQUEST_TERMINATE_INTEGRATION,
    REQUEST_STOP_MATLAB,
    REQUEST_START_MATLAB,
    REQUEST_ENV_CONFIG,
    RECEIVE_SET_LICENSING,
    RECEIVE_UPDATE_LICENSING,
    RECEIVE_TERMINATE_INTEGRATION,
    RECEIVE_STOP_MATLAB,
    RECEIVE_START_MATLAB,
    RECEIVE_ERROR,
    RECEIVE_ENV_CONFIG,
    SET_AUTH_STATUS,
    SET_AUTH_TOKEN
} from '../actions';
import { selectMatlabPending } from '../selectors';
import sha256 from 'crypto-js/sha256';

export function setAuthStatus(authInfo) {
    return {
        type: SET_AUTH_STATUS,
        authInfo
    }
}

export function setAuthToken(authInfo) {
    return {
        type: SET_AUTH_TOKEN,
        authInfo
    }
}

export function setTriggerPosition(x, y) {
    return {
        type: SET_TRIGGER_POSITION,
        x,
        y
    };
}

export function setTutorialHidden(hidden) {
    return {
        type: SET_TUTORIAL_HIDDEN,
        hidden
    };
}

export function setOverlayVisibility(visibility) {
    return {
        type: SET_OVERLAY_VISIBILITY,
        visibility
    };
}

export function requestServerStatus() {
    return {
        type: REQUEST_SERVER_STATUS,
    };
}

export function receiveServerStatus(status) {
    return function (dispatch, getState) {
        return dispatch({
            type: RECEIVE_SERVER_STATUS,
            status,
            previousMatlabPending: selectMatlabPending(getState())
        });
    }
}

export function requestEnvConfig() {
    return {
        type: REQUEST_ENV_CONFIG,
    };
}

export function receiveEnvConfig(config) {
    return {
        type: RECEIVE_ENV_CONFIG,
        config,
    };
}

export function requestSetLicensing() {
    return {
        type: REQUEST_SET_LICENSING,
    };
}

export function receiveSetLicensing(status) {
    return {
        type: RECEIVE_SET_LICENSING,
        status
    };
}

export function requestUpdateLicensing() {
    return {
        type: REQUEST_UPDATE_LICENSING,
    };
}

export function receiveUpdateLicensing(status) {
    return {
        type: RECEIVE_UPDATE_LICENSING,
        status
    };
}


export function requestTerminateIntegration() {
    return {
        type: REQUEST_TERMINATE_INTEGRATION,
    };
}

export function receiveTerminateIntegration(status) {
    return {
        type: RECEIVE_TERMINATE_INTEGRATION,
        status,
        loadUrl: '../'
    };
}

export function requestStopMatlab() {
    return {
        type: REQUEST_STOP_MATLAB,
        status: 'stopping'
    };
}

export function receiveStopMatlab(status) {
    return {
        type: RECEIVE_STOP_MATLAB,
        status
    };
}

export function requestStartMatlab() {
    return {
        type: REQUEST_START_MATLAB,
        status: 'starting'
    };
}

export function receiveStartMatlab(status) {
    return {
        type: RECEIVE_START_MATLAB,
        status
    };
}

// TODO Probably no need for multiple actions/action creators for fetch
// failures?
export function receiveError(error, statusCode) {
    return {
        type: RECEIVE_ERROR,
        error,
        statusCode
    }
}

export async function fetchWithTimeout(dispatch, resource, options = {}, timeout = 10000) {
    // Create an abort controller for this request and set a timeout for it to abort.
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), timeout);

    try {
        const response = await fetch(resource, {
            ...options,
            signal: controller.signal
        });
        clearTimeout(id);

        return response;
    } catch (err) {
        const errorText = 'Check your internet connection and verify that the server is running.';
        // If AbortController is aborted, then AbortError exception is raised due to time out.
        if (err.name === "AbortError" || err.name === 'TypeError') {
            dispatch(receiveError(`HTTP Error 408 - Request Timeout. ${errorText}`, 408))
        } else {
            dispatch(receiveError("Communication with server failed.", 500))
        }
    }
}

export function fetchServerStatus() {
    return async function (dispatch, getState) {

        dispatch(requestServerStatus());
        const response = await fetchWithTimeout(dispatch, './get_status', {}, 10000);
        const data = await response.json();
        dispatch(receiveServerStatus(data));

    }
}

export function fetchEnvConfig() {
    return async function (dispatch, getState) {

        dispatch(requestEnvConfig());
        const response = await fetchWithTimeout(dispatch, './get_env_config', {}, 10000);
        const data = await response.json();
        dispatch(receiveEnvConfig(data));
    };
}

export function updateAuthStatus(token) {
    // make response consistent with rest of reducers (data)
    return async function (dispatch, getState) {

        const tokenHash = sha256(token)
        const options = {
            method: 'POST',
            headers: {
                'mwi_auth_token': tokenHash
            },
        };
        const response = await fetchWithTimeout(dispatch, './authenticate', options, 15000);
        const data = await response.json()

        dispatch(setAuthStatus(data))
    }
}

export function getAuthToken() {
    // make response consistent with rest of reducers (data)
    return async function (dispatch, getState) {

        const options = {
            method: 'GET'
        };
        const response = await fetchWithTimeout(dispatch, './get_auth_token', options, 10000);
        const data = await response.json()
        dispatch(setAuthToken(data))
    }
}

export function fetchSetLicensing(info) {
    return async function (dispatch, getState) {

        const options = {
            method: 'PUT',
            mode: 'same-origin',
            cache: 'no-cache',
            credentials: 'same-origin',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(info),
        }

        dispatch(requestSetLicensing());
        const response = await fetchWithTimeout(dispatch, './set_licensing_info', options, 15000);
        const data = await response.json();
        dispatch(receiveSetLicensing(data));

    }
}

export function fetchUpdateLicensing(info) {
    return async function (dispatch, getState) {

        const options = {
            method: 'PUT',
            mode: 'same-origin',
            cache: 'no-cache',
            credentials: 'same-origin',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(info),
        }

        dispatch(requestUpdateLicensing());
        const response = await fetchWithTimeout(dispatch, './update_entitlement', options, 1500);
        const data = await response.json();
        dispatch(receiveUpdateLicensing(data));
    }
}

export function fetchUnsetLicensing() {
    return async function (dispatch, getState) {

        const options = {
            method: 'DELETE',
            mode: 'same-origin',
            cache: 'no-cache',
            credentials: 'same-origin',
        }

        dispatch(requestSetLicensing());
        const response = await fetchWithTimeout(dispatch, './set_licensing_info', options, 15000);
        const data = await response.json();
        dispatch(receiveSetLicensing(data));

    }
}

export function fetchTerminateIntegration() {
    return async function (dispatch, getState) {

        const options = {
            method: 'DELETE',
            mode: 'same-origin',
            cache: 'no-cache',
            credentials: 'same-origin',
        }

        dispatch(requestTerminateIntegration());
        const response = await fetchWithTimeout(dispatch, './terminate_integration', options, 15000);
        const data = await response.json();
        dispatch(receiveTerminateIntegration(data));

    }
}

export function fetchStopMatlab() {
    return async function (dispatch, getState) {

        const options = {
            method: 'DELETE',
            mode: 'same-origin',
            cache: 'no-cache',
            credentials: 'same-origin',
        }

        dispatch(requestStopMatlab());
        const response = await fetchWithTimeout(dispatch, './stop_matlab', options, 30000);
        const data = await response.json();
        dispatch(receiveStopMatlab(data));

    }
}

export function fetchStartMatlab() {
    return async function (dispatch, getState) {

        const options = {
            method: 'PUT',
            mode: 'same-origin',
            cache: 'no-cache',
            credentials: 'same-origin',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({}),
        }

        dispatch(requestStartMatlab());
        const response = await fetchWithTimeout(dispatch, './start_matlab', options, 15000);
        const data = await response.json();
        dispatch(receiveStartMatlab(data));

    }
}
