// Copyright 2020 The MathWorks, Inc.

import {
    SET_TRIGGER_POSITION,
    SET_TUTORIAL_HIDDEN,
    SET_OVERLAY_VISIBILITY,
    REQUEST_SERVER_STATUS,
    RECEIVE_SERVER_STATUS,
    REQUEST_SET_LICENSING,
    REQUEST_TERMINATE_INTEGRATION,
    REQUEST_STOP_MATLAB,
    REQUEST_START_MATLAB,
    REQUEST_ENV_CONFIG,
    RECEIVE_SET_LICENSING,
    RECEIVE_TERMINATE_INTEGRATION,
    RECEIVE_STOP_MATLAB,
    RECEIVE_START_MATLAB,
    RECEIVE_ERROR,
    RECEIVE_ENV_CONFIG,
} from '../actions';
import { getFetchAbortController, selectMatlabPending, selectHasFetchedEnvConfig } from '../selectors';

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

export function requestServerStatus(fetchAbortController) {
    return {
        type: REQUEST_SERVER_STATUS,
        fetchAbortController
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

export function requestEnvConfig(fetchAbortController) {
    return {
        type: REQUEST_ENV_CONFIG,
        fetchAbortController,
    };
}

export function receiveEnvConfig(config) {
    return {
        type: RECEIVE_ENV_CONFIG,
        config,
    };
}

export function requestSetLicensing(fetchAbortController) {
    return {
        type: REQUEST_SET_LICENSING,
        fetchAbortController
    };
}

export function receiveSetLicensing(status) {
    return {
        type: RECEIVE_SET_LICENSING,
        status
    };
}

export function requestTerminateIntegration(fetchAbortController) {
    return {
        type: REQUEST_TERMINATE_INTEGRATION,
        fetchAbortController
    };
}

export function receiveTerminateIntegration(status) {
    return {
        type: RECEIVE_TERMINATE_INTEGRATION,
        status,
        loadUrl: '../'
    };
}

export function requestStopMatlab(fetchAbortController) {
    return {
        type: REQUEST_STOP_MATLAB,
        fetchAbortController
    };
}

export function receiveStopMatlab(status) {
    return {
        type: RECEIVE_STOP_MATLAB,
        status
    };
}

export function requestStartMatlab(fetchAbortController) {
    return {
        type: REQUEST_START_MATLAB,
        fetchAbortController
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
export function receiveError(error) {
    return {
        type: RECEIVE_ERROR,
        error
    };
}

export function fetchServerStatus() {
    return async function (dispatch, getState) {        

        // Abort any previous request which is in-flight
        getFetchAbortController(getState()).abort();

        // Create new AbortController
        const abortController = new AbortController();

        // Set this request as in-flight
        dispatch(requestServerStatus(abortController));

        try {
            const res = await fetch('./get_status', {
                signal: abortController.signal
            });
            const data = await res.json();
		    dispatch(receiveServerStatus(data));
            
        } catch (e) {
            dispatch(
                receiveError('Communication with server failed.')
            );
        }     

        if(!selectHasFetchedEnvConfig(getState())) {
            return dispatch(fetchEnvConfig())
        }
    }
}

export function fetchEnvConfig() {
    return async function (dispatch, getState) {
        //Abort any previous request which is in-flight
        getFetchAbortController(getState()).abort();

        //Create new AbortController
        const abortController = new AbortController();

        //Set this request as in-flight
        dispatch(requestEnvConfig(abortController));
        
        try {
            const res = await fetch('./get_env_config', {
                signal: abortController.signal,
            });
            const data = await res.json();
            return dispatch(receiveEnvConfig(data));
        } catch (e) {
            dispatch(receiveError('Failed to fetch Env config.'));
        }
    };
}


export function fetchSetLicensing(info) {
    return async function (dispatch, getState) {

        // Abort any previous request which is in-flight
        getFetchAbortController(getState()).abort();

        // Create new AbortController
        const abortController = new AbortController();

        // Set this request as in-flight
        dispatch(requestSetLicensing(abortController));

        try {
            const res = await fetch('./set_licensing_info', {
                method: 'PUT',
                mode: 'same-origin',
                cache: 'no-cache',
                credentials: 'same-origin',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(info),
                signal: abortController.signal
            });
            const data = await res.json();
            return dispatch(receiveSetLicensing(data));
        } catch (e) {
            dispatch( receiveError('Communication with server failed.'));
        }

    }
}

export function fetchUnsetLicensing() {
    return async function (dispatch, getState) {

        // Abort any previous request which is in-flight
        getFetchAbortController(getState()).abort();

        // Create new AbortController
        const abortController = new AbortController();

        // Set this request as in-flight
        dispatch(requestSetLicensing(abortController));

        try {
            const res = await fetch('./set_licensing_info', {
                method: 'DELETE',
                mode: 'same-origin',
                cache: 'no-cache',
                credentials: 'same-origin',
                signal: abortController.signal
            });
            const data = await res.json();
            return dispatch(receiveSetLicensing(data));
        } catch (e) {
            dispatch( receiveError('Communication with server failed.'));
        }

    }
}

export function fetchTerminateIntegration() {
    return async function (dispatch, getState) {

        // Abort any previous request which is in-flight
        getFetchAbortController(getState()).abort();

        // Create new AbortController
        const abortController = new AbortController();

        // Set this request as in-flight
        dispatch(requestTerminateIntegration(abortController));

        try {
            const res = await fetch('./terminate_integration', {
                method: 'DELETE',
                mode: 'same-origin',
                cache: 'no-cache',
                credentials: 'same-origin',
                signal: abortController.signal
            });
            const data = await res.json();
            return dispatch(receiveTerminateIntegration(data));
        } catch (e) {
            dispatch( receiveError('Communication with server failed.'));
        }

    }
}

export function fetchStopMatlab() {
    return async function (dispatch, getState) {

        // Abort any previous request which is in-flight
        getFetchAbortController(getState()).abort();

        // Create new AbortController
        const abortController = new AbortController();

        // Set this request as in-flight
        dispatch(requestStopMatlab(abortController));

        try {
            const res = await fetch('./stop_matlab', {
                method: 'DELETE',
                mode: 'same-origin',
                cache: 'no-cache',
                credentials: 'same-origin',
                signal: abortController.signal
            });
            const data = await res.json();
            return dispatch(receiveStopMatlab(data));
        } catch (e) {
            dispatch( receiveError('Communication with server failed.'));
        }

    }
}

export function fetchStartMatlab() {
    return async function (dispatch, getState) {

        // Abort any previous request which is in-flight
        getFetchAbortController(getState()).abort();

        // Create new AbortController
        const abortController = new AbortController();

        // Set this request as in-flight
        dispatch(requestStartMatlab(abortController));

        try {
            const res = await fetch('./start_matlab', {
                method: 'PUT',
                mode: 'same-origin',
                cache: 'no-cache',
                credentials: 'same-origin',
                signal: abortController.signal,
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({}),
            });
            const data = await res.json();
            return dispatch(receiveStartMatlab(data));
        } catch (e) {
            dispatch( receiveError('Communication with server failed.'));
        }

    }
}