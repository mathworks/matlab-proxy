// Copyright 2020-2025 The MathWorks, Inc.

import React, { useState, useCallback, useEffect, useMemo, useRef } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { useInterval, useTimeoutFn } from 'react-use';
import './App.css';
import Confirmation from '../Confirmation';
import OverlayTrigger from '../OverlayTrigger';
import Overlay from '../Overlay';
import MatlabJsd from '../MatlabJsd';
import LicensingGatherer from '../LicensingGatherer';
import Controls from '../Controls';
import Information from '../Information';
import Help from '../Help';
import Error from '../Error';
import ShutdownWarning from '../ShutdownWarning';
import {
    selectOverlayVisible,
    selectFetchStatusPeriod,
    selectHasFetchedServerStatus,
    selectLicensingProvided,
    selectMatlabUp,
    selectError,
    selectLoadUrl,
    selectIsConnectionError,
    selectHasFetchedEnvConfig,
    selectAuthEnabled,
    selectIsAuthenticated,
    selectLicensingMhlmHasEntitlements,
    selectIsEntitled,
    selectLicensingInfo,
    selectIsConcurrent,
    selectWasEverActive,
    selectIsConcurrencyEnabled,
    selectIsActiveClient,
    selectIdleTimeoutDurationInMS,
    selectIsMatlabBusy,
    selectMatlabStarting,
    selectIsIdleTimeoutEnabled,
    selectMatlabStopping,
    selectBrowserTitle,
    selectIntegrationName
} from '../../selectors';

import {
    setOverlayVisibility,
    fetchServerStatus,
    fetchEnvConfig,
    updateAuthStatus,
    fetchShutdownIntegration
} from '../../actionCreators';
import blurredBackground from './MATLAB-env-blur.png';
import EntitlementSelector from '../EntitlementSelector';
import { BUFFER_TIMEOUT_DURATION, MWI_AUTH_TOKEN_NAME_FOR_HTTP } from '../../constants';

function App() {
    const dispatch = useDispatch();

    const overlayVisible = useSelector(selectOverlayVisible);
    const fetchStatusPeriod = useSelector(selectFetchStatusPeriod);
    const hasFetchedServerStatus = useSelector(selectHasFetchedServerStatus);
    const hasFetchedEnvConfig = useSelector(selectHasFetchedEnvConfig);
    const licensingProvided = useSelector(selectLicensingProvided);
    const hasEntitlements = useSelector(selectLicensingMhlmHasEntitlements);
    const isEntitled = useSelector(selectIsEntitled);
    const matlabUp = useSelector(selectMatlabUp);
    const error = useSelector(selectError);
    const loadUrl = useSelector(selectLoadUrl);
    const isConnectionError = useSelector(selectIsConnectionError);
    const isAuthenticated = useSelector(selectIsAuthenticated);
    const authEnabled = useSelector(selectAuthEnabled);
    const licensingInfo = useSelector(selectLicensingInfo);
    const isSessionConcurrent = useSelector(selectIsConcurrent);
    const isActiveClient = useSelector(selectIsActiveClient);
    const isConcurrencyEnabled = useSelector(selectIsConcurrencyEnabled);
    const wasEverActive = useSelector(selectWasEverActive);
    const integrationName = useSelector(selectIntegrationName);
    const browserTitle = useSelector(selectBrowserTitle);

    // Timeout duration is specified in seconds, but useTimeoutFn accepts timeout values in ms.
    const idleTimeoutDurationInMS = useSelector(selectIdleTimeoutDurationInMS);
    const isMatlabBusy = useSelector(selectIsMatlabBusy);
    const isMatlabStarting = useSelector(selectMatlabStarting);
    const isMatlabStopping = useSelector(selectMatlabStopping);
    const isIdleTimeoutEnabled = useSelector(selectIsIdleTimeoutEnabled);

    // Keep track of whether timers have expired.
    const [idleTimerHasExpired, setIdleTimerHasExpired] = useState(false);
    const [bufferTimerHasExpired, setBufferTimerHasExpired] = useState(false);

    // Track events only if timeout is enabled and the client is active.
    const shouldListenForEvents = isIdleTimeoutEnabled && isActiveClient;


    // callback that will fire once the IDLE timer expires
    function terminationFn() {
        // Reset the timer if MATLAB is either starting or stopping or is busy
        if (isMatlabStarting || isMatlabStopping || isMatlabBusy) {
            idleTimerReset();
            console.log('Resetting IDLE timer as MATLAB is either starting, stopping or busy');
        } else if (!shouldListenForEvents) {
            idleTimerCancel();
            console.log('The IDLE timer has been cancelled.');
        } else {
            dispatch(setOverlayVisibility(true));
            setIdleTimerHasExpired(true);
            console.log('The IDLE timer has expired due to inactivity. Will display Shutdown Warning to the user.');
            console.log('The additional BUFFER timer has started.');
        }
    }

    const [, idleTimerCancel, idleTimerReset] = useTimeoutFn(terminationFn, idleTimeoutDurationInMS);

    useEffect(() => {
        if (isIdleTimeoutEnabled) {
            idleTimerReset();
        } else {
            idleTimerCancel();
        }

        // cleanup function to ensure idle timer gets cancelled once the component unmounts
        return () => { idleTimerCancel(); };
    }, [idleTimerCancel, idleTimerReset, isIdleTimeoutEnabled]);

    // BUFFER timer which runs for a BUFFER_TIMER_DURATION more seconds once the IDLE timer has expired to allow the ShutdownWarning
    // dialog box to appear on the screen, such that the user is informed of an impending termination.
    const [, bufferTimerCancel, bufferTimerReset] = useTimeoutFn(() => {
        dispatch(fetchShutdownIntegration());
        setBufferTimerHasExpired(true);
    }, BUFFER_TIMEOUT_DURATION * 1000);

    useEffect(() => {
        if (idleTimerHasExpired) {
            // Start BUFFER timer after IDLE timer has expired
            bufferTimerReset();
        } else {
            bufferTimerCancel();
        }

        // cleanup function to ensure BUFFER timer gets cancelled once the component unmounts
        return () => { bufferTimerCancel(); };
    }, [bufferTimerCancel, bufferTimerReset, idleTimerHasExpired]);

    const baseUrl = useMemo(() => {
        const url = document.URL;
        return url.split(window.location.origin)[1].split('index.html')[0];
    }, []);

    const parseQueryParams = (url) => {
        const queryParams = new URLSearchParams(url.search);
        return queryParams;
    };

    const fullyQualifiedUrl = useMemo(() => {
        // Returns the Fully Qualified URL used to load the page.
        const url = document.URL;
        const baseUrlStr = url.split('/index.html')[0];
        return baseUrlStr;
    }, []);

    const htmlToRenderMATLAB = () => {
        let theHtmlToRenderMATLAB = 'index-jsd-cr.html';

        // Add mre query parameter
        theHtmlToRenderMATLAB += `?mre=${encodeURIComponent(fullyQualifiedUrl)}`;

        return theHtmlToRenderMATLAB;
    };

    const toggleOverlayVisible = useCallback(
        () => dispatch(setOverlayVisibility(!overlayVisible)),
        [overlayVisible, dispatch]
    );

    const [dialogModel, setDialogModel] = useState(null);
    const [isTerminated, setIsTerminated] = useState(false);

    // sessionDialog stores the state of concurrent session based on which either matlab gets rendered or the concurrent session dialog gets rendered
    let sessionDialog = null;
    let dialog;
    if (dialogModel) {
        const closeHandler = () => setDialogModel(null);
        const dismissAllHandler = () => {
            closeHandler();
            toggleOverlayVisible(false);
        };
        switch (dialogModel.type) {
            case 'confirmation': {
                const confirm = () => {
                    dispatch(dialogModel.callback());
                    setDialogModel(null);
                };
                dialog = (
                    <Confirmation
                        confirm={confirm}
                        cancel={closeHandler}>
                        {dialogModel.message || ''}
                    </Confirmation>
                );
                break;
            }
            case 'help':
                dialog = (
                    <Help
                        closeHandler={closeHandler}
                        dismissAllHandler={dismissAllHandler}
                    />);
                break;
            default:
                throw new Error(`Unknown dialog type: ${dialogModel.type}.`);
        }
    }
    if (isConnectionError) {
        dialog = (
            <Error
                message={`Either this ${integrationName} terminated or the session ended`}
            >
                <p>Attempt to <a href="../">return to a parent app</a></p>
            </Error>
        );
    } else if (error && error.type === 'MatlabInstallError') {
        dialog = <Error message={error.message} />;
        // check user authentication before giving them the option to transfer the session.
    } else if ((!authEnabled || isAuthenticated) && isSessionConcurrent && isConcurrencyEnabled) {
        // Transfer the session to this tab
        // setting the query parameter of requestTransferSession to true
        const transferSessionOnClick = () => {
            dispatch(fetchServerStatus(true));
            sessionDialog = null;
        };
        const endSession = () => {
            setIsTerminated(true);
        };
        if (isTerminated) {
            sessionDialog = <Error message="Your session has been terminated. Refresh the page to restart the session." />;
        } else {
            sessionDialog = (
                <Confirmation
                    confirm={transferSessionOnClick}
                    cancel={endSession}
                    title='MATLAB is currently open in another window'
                    cancelButton={wasEverActive
                        ? ('Cancel')
                        : ('Continue in existing window')}
                    confirmButton={wasEverActive
                        ? ('Confirm')
                        : ('Continue in this window')}>
                    {wasEverActive
                        ? 'You have been disconnected because MATLAB is open in another window. Click on Confirm to continue using MATLAB here.'
                        : <div>MATLAB is open in another window and cannot be opened in a second window or tab at the same time.<br></br>Would you like to continue in this window?</div>}
                </Confirmation>
            );
        }
    }

    useEffect(() => {
        const handlePageHide = (event) => {
            // Performs actions before the component unloads
            if (isConcurrencyEnabled && !isSessionConcurrent && hasFetchedServerStatus) {
                // A POST request to clear the active client when the tab/browser is closed
                navigator.sendBeacon('./clear_client_id');
            }
            event.preventDefault();
            event.returnValue = '';
        };
        window.addEventListener('pagehide', handlePageHide);
        return () => {
            window.removeEventListener('pagehide', handlePageHide);
        };
    }, [isConcurrencyEnabled, isSessionConcurrent, hasFetchedServerStatus]);

    useEffect(() => {
        // Initial fetch environment configuration
        if (!hasFetchedEnvConfig) {
            dispatch(fetchEnvConfig());
        }
    }, [dispatch, hasFetchedEnvConfig]);

    useEffect(() => {
        // Initial fetch server status
        if (hasFetchedEnvConfig && !hasFetchedServerStatus) {
            dispatch(fetchServerStatus());
        }
    }, [dispatch, hasFetchedServerStatus, hasFetchedEnvConfig]);

    // Periodic fetch server status
    useInterval(() => {
        if (hasFetchedServerStatus) {
            dispatch(fetchServerStatus());
        }
    }, fetchStatusPeriod);

    // Load URL
    useEffect(() => {
        if (loadUrl !== null) {
            window.location.href = loadUrl;
        }
    }, [loadUrl]);

    useEffect(() => {
        // Send authenticate request only after env config is fetched,
        // fixes https://github.com/mathworks/matlab-proxy/issues/37
        if (hasFetchedEnvConfig) {
            const queryParams = parseQueryParams(window.location);
            const token = queryParams.get(MWI_AUTH_TOKEN_NAME_FOR_HTTP);
            document.title = `${browserTitle}`;
            if (token) {
                dispatch(updateAuthStatus(token));
            }
            window.history.replaceState(null, '', `${baseUrl}index.html`);
        }
    }, [dispatch, baseUrl, hasFetchedEnvConfig]);

    // Display one of:
    // * Confirmation
    // * Help
    // * Error
    // * License gatherer
    // * License selector
    // * Status Information
    let overlayContent;

    // show an impending shutdown warning if IDLE timeout is enabled and the IDLE timer has expired.
    // it should have the highest precedence, and should draw above all other windows.
    if (isIdleTimeoutEnabled && idleTimerHasExpired) {
        if (bufferTimerHasExpired) {
            const msg = `The ${integrationName} has shutdown due to inactivity`;
            overlayContent = <Error message={msg}> </Error>;
            console.log(`BUFFER timer has also expired, proceeding with shutting down ${integrationName}`);
        } else {
            overlayContent = <ShutdownWarning
                bufferTimeout={BUFFER_TIMEOUT_DURATION}
                resumeCallback={() => {
                    // Restart IDLE timer
                    idleTimerReset();
                    setIdleTimerHasExpired(false);

                    // Cancel BUFFER timer
                    bufferTimerCancel();
                    setBufferTimerHasExpired(false);
                    console.log('Reset IDLE timer and cancelled BUFFER timer after user resumed activity.');
                }} />;
        }
    } else if (dialog) {
        overlayContent = dialog;
    } else if ((!licensingProvided) && hasFetchedServerStatus && (!authEnabled || isAuthenticated)) {
        // Give precedence to token auth over licensing info ie. once after token auth is done, show licensing if not provided.
        overlayContent = <LicensingGatherer role="licensing" aria-describedby="license-window" />;
    } else if (hasEntitlements && !isEntitled) {
        // Show license selector if the user has entitlements and is not currently entitled
        overlayContent = <EntitlementSelector options={licensingInfo.entitlements} />;
    } else if (!dialog) {
        // in all other cases, we will either ask for the token,
        overlayContent = (
            <Information closeHandler={toggleOverlayVisible}>
                <Controls callback={args => setDialogModel(args)} />
            </Information>
        );
    }

    const overlay = overlayVisible
        ? (
            <Overlay>
                {overlayContent}
            </Overlay>
        )
        : null;

    // FIXME Until https://github.com/http-party/node-http-proxy/issues/1342
    // is addressed, use a direct URL in development mode. Once that is
    // fixed, the request will be served by the fake MATLAB Embedded Connector
    // process in development mode

    // MW Internal Comment: See g2992889 for a discussion on why a FQDN is required in the MRE parameter.
    const matlabUrl = process.env.NODE_ENV === 'development'
        ? 'http://localhost:31515/index-jsd-cr.html'
        : `./${htmlToRenderMATLAB()}`;

    // handler for user events (mouse clicks, key presses etc.)
    const handleUserInteraction = useCallback(() => {
        idleTimerReset();
    }, [idleTimerReset]);

    const MatlabJsdIframeRef = useRef(null);
    let matlabJsd = null;
    if (matlabUp) {
        matlabJsd = (!authEnabled || isAuthenticated)
            ? (<MatlabJsd handleUserInteraction={handleUserInteraction} url={matlabUrl} iFrameRef={MatlabJsdIframeRef} shouldListenForEvents={shouldListenForEvents} />)
            : <img style={{ objectFit: 'fill' }} src={blurredBackground} alt='Blurred MATLAB environment' />;
    }

    const overlayTrigger = overlayVisible
        ? null
        : <OverlayTrigger />;

    return (
        // If we use div instead of React.Fragment then the editor screen becomes white / doesn't fully render.
        // Have noticed this behavior both in windows and Linux.
        // If session dialog is not 'null' then render the transfer dialog or error dialog otherwise render the normal MATLAB.
        <React.Fragment>
            {sessionDialog
                ? (
                    <Overlay>
                        {sessionDialog}
                    </Overlay>
                )
                : (
                    <div data-testid="app" className="main" >
                        {overlayTrigger}
                        {matlabJsd}
                        {overlay}
                    </div>
                )}
        </React.Fragment>
    );
}

export default App;
