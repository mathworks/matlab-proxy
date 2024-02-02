// Copyright 2020-2024 The MathWorks, Inc.

import React, { useState, useCallback, useEffect, useMemo } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { useInterval } from 'react-use';
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
    selectUseMOS,
    selectUseMRE,
    selectIsConcurrent,
    selectWasEverActive,
    selectIsConcurrencyEnabled,
} from "../../selectors";

import {
    setOverlayVisibility,
    fetchServerStatus,
    fetchEnvConfig,
    updateAuthStatus,
} from '../../actionCreators';
import blurredBackground from './MATLAB-env-blur.png';
import EntitlementSelector from "../EntitlementSelector";

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
    const useMOS = useSelector(selectUseMOS);
    const useMRE = useSelector(selectUseMRE);
    const isSessionConcurrent = useSelector(selectIsConcurrent);
    const isConcurrencyEnabled = useSelector(selectIsConcurrencyEnabled);
    const wasEverActive = useSelector(selectWasEverActive);

    const baseUrl = useMemo(() => {
        const url = document.URL
        return url.split(window.location.origin)[1].split('index.html')[0]
    }, [])

    const parseQueryParams = (url) => {
        const queryParams = new URLSearchParams(url.search);
        return queryParams;
    }

    const fullyQualifiedUrl = useMemo(() => {
        // Returns the Fully Qualified URL used to load the page.
        const url = document.URL
        let baseUrlStr = url.split('/index.html')[0]
        return baseUrlStr;
    }, [])

    const htmlToRenderMATLAB = () => {
        let theHtmlToRenderMATLAB = useMOS ? "index-matlabonlineserver.html" : 'index-jsd-cr.html'
        if (useMRE) {
            theHtmlToRenderMATLAB += `?mre=${fullyQualifiedUrl}`
        }
        return theHtmlToRenderMATLAB
    }

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
            case 'confirmation':
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
                message="Either this integration terminated or the session ended"
            >
                <p>Attempt to <a href="../">return to a parent app</a></p>
            </Error>
        );
    } else if (error && error.type === "MatlabInstallError") {
        dialog = <Error message={error.message} />;
    } 
    // check the user authentication before giving them the option to transfer the session.
    else if ((!authEnabled || isAuthenticated) && isSessionConcurrent && isConcurrencyEnabled) {
        // Transfer the session to this tab 
        // setting the query parameter of requestTransferSession to true
        const transferSessionOnClick= () => {
            dispatch(fetchServerStatus(true));
            sessionDialog=null;
        }
        const endSession = () => {
            setIsTerminated(true);
        }
        if(isTerminated) {
            sessionDialog = <Error message="Your session has been terminated. Refresh the page to restart the session." />;
        }
        else {
            sessionDialog = (
                <Confirmation
                    confirm={transferSessionOnClick}
                    cancel={endSession}
                    title='MATLAB is currently open in another window'
                    cancelButton={wasEverActive?('Cancel'):('Continue in existing window')}
                    confirmButton = {wasEverActive?('Confirm'):('Continue in this window')}>
                    {wasEverActive
                        ? 'You have been disconnected because MATLAB is open in another window. Click on Confirm to continue using MATLAB here.'
                        : <div>MATLAB is open in another window and cannot be opened in a second window or tab at the same time.<br></br>Would you like to continue in this window?</div> }
                </Confirmation>
            );
        }
    }

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
        if(hasFetchedServerStatus)
        {
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
        const queryParams = parseQueryParams(window.location);
        const token = queryParams.get("mwi_auth_token");

        if (token) {
            dispatch(updateAuthStatus(token));
        }
        window.history.replaceState(null, '', `${baseUrl}index.html`);
    }, [dispatch, baseUrl]);

    // Display one of:
    // * Confirmation
    // * Help
    // * Error
    // * License gatherer
    // * License selector
    // * Status Information
    let overlayContent;

    if (dialog) {
        // TODO Inline confirmation component build
        overlayContent = dialog;
    }
    // Give precedence to token auth over licensing info ie. once after token auth is done, show licensing if not provided.
    else if ((!licensingProvided) && hasFetchedServerStatus && (!authEnabled || isAuthenticated)) {
        overlayContent = <LicensingGatherer role="licensing" aria-describedby="license-window" />;
    }
    // Show license selector if the user has entitlements and is not currently entitled
    else if (hasEntitlements && !isEntitled) {
        overlayContent = <EntitlementSelector options={licensingInfo.entitlements} />;
    }
    // in all other cases, we will either ask for the token, 
    else if (!dialog) {
        overlayContent = (
            <Information closeHandler={toggleOverlayVisible}>
                <Controls callback={args => setDialogModel(args)} />
            </Information>
        );
    }

    const overlay = overlayVisible ? (
        <Overlay>
            {overlayContent}
        </Overlay>
    ) : null;


    // FIXME Until https://github.com/http-party/node-http-proxy/issues/1342
    // is addressed, use a direct URL in development mode. Once that is
    // fixed, the request will be served by the fake MATLAB Embedded Connector
    // process in development mode

    // MW Internal Comment: See g2992889 for a discussion on why a FQDN is required in the MRE parameter.
    // MW Internal Comment: Using websocket on breaks some UI components : `./index-matlabonlineserver.html?websocket=on&mre=${fullyQualifiedUrl}`;
    const matlabUrl = process.env.NODE_ENV === 'development'
        ? 'http://localhost:31515/index-jsd-cr.html'
        : `./${htmlToRenderMATLAB()}`;

    let matlabJsd = null;
    if (matlabUp) {
        matlabJsd = (!authEnabled || isAuthenticated)
            ? (<MatlabJsd url={matlabUrl} />)
            : <img style={{ objectFit: 'fill' }} src={blurredBackground} alt='Blurred MATLAB environment' />
    }

    const overlayTrigger = overlayVisible ? null : <OverlayTrigger />;

    return (
        // If we use div instead of React.Fragment then the editor screen becomes white / doesn't fully render.
        // Have noticed this behavior both in windows and Linux.
        // If session dialog is not 'null' then render the transfer dialog or error dialog otherwise render the normal MATLAB.
        <React.Fragment>
            {sessionDialog?(
                <Overlay>
                    {sessionDialog}
                </Overlay>
            ):(
                <div data-testid="app" className="main">
                    {overlayTrigger}
                    {matlabJsd}
                    {overlay}
                </div>
            )}
        </React.Fragment>
    );
}

export default App;