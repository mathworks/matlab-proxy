// Copyright 2020-2025 The MathWorks, Inc.

import React, { useRef } from 'react';
import PropTypes from 'prop-types';
import { useSelector } from 'react-redux';
import  {Tooltip as ReactTooltip} from 'react-tooltip';
import {
    selectSubmittingServerStatus,
    selectLicensingInfo,
    selectLicensingProvided,
    selectMatlabUp,
    selectMatlabStarting,
    selectMatlabStopping,
    selectMatlabDown,
    selectError,
    selectIsAuthenticated,
    selectAuthEnabled,
    selectLicensingIsMhlm,
    selectIsEntitled,
    selectShouldShowShutdownButton
} from '../../selectors';
import {
    fetchStartMatlab,
    fetchStopMatlab,
    fetchShutdownIntegration,
    fetchUnsetLicensing
} from '../../actionCreators';
import './Controls.css';

// Suggested actions for certain errors
const ERROR_TYPE_MAP = {
    'sign-out': ['NetworkLicensingError', 'EntitlementError', 'UIVisibleFatalError'],
    restart: ['OnlineLicensingError']
};

function Controls ({
    callback
}) {
    const tooltipRef = useRef(null);

    const submitting = useSelector(selectSubmittingServerStatus);
    const licensed = useSelector(selectLicensingProvided);
    const matlabStarting = useSelector(selectMatlabStarting);
    const matlabUp = useSelector(selectMatlabUp);
    const matlabStopping = useSelector(selectMatlabStopping);
    const matlabDown = useSelector(selectMatlabDown);
    const error = useSelector(selectError);
    const authEnabled = useSelector(selectAuthEnabled);
    const isAuthenticated = useSelector(selectIsAuthenticated);
    const licensingInfo = useSelector(selectLicensingInfo);
    const canResetLicensing = licensed && !submitting;

    // If licensing type is MHLM and the user is not entitled ( MATLAB version couldn't be determined (VersionInfo.xml was not found))
    // then start, stop & signout buttons should be disabled.
    const licensingIsMhlm = useSelector(selectLicensingIsMhlm);
    const isEntitled = useSelector(selectIsEntitled);

    const shouldShowShutdownButton = useSelector(selectShouldShowShutdownButton);

    let licensingData, licensingConfirmationMessage;
    switch (licensingInfo?.type) {
        case 'mhlm':
            licensingData = {
                label: 'Sign Out',
                dataTip: 'Sign out of MATLAB'
            };
            licensingConfirmationMessage = 'Are you sure you want to sign out of MATLAB?';
            break;
        case 'nlm':
            licensingData = {
                label: 'Remove License Server Address',
                dataTip: 'Remove the network license manager server address'
            };
            licensingConfirmationMessage = 'Are you sure you want to remove the network license manager server address?';
            break;

        case 'existing_license':
            licensingData = {
                label: 'Stop using Existing License',
                dataTip: 'Stop using existing license'
            };
            licensingConfirmationMessage = 'Are you sure you want to stop using an Existing License?';
            break;

        default:
            licensingData = {
                label: 'None',
                dataTip: 'None'
            };
            licensingConfirmationMessage = null;
    }

    const Confirmations = {
        START: {
            type: 'confirmation',
            message: `Are you sure you want to ${matlabUp
                ? 're'
                : ''}start MATLAB?`,
            callback: fetchStartMatlab
        },
        STOP: {
            type: 'confirmation',
            message: 'Are you sure you want to stop MATLAB?',
            callback: fetchStopMatlab
        },
        SHUTDOWN: {
            type: 'confirmation',
            message: 'Are you sure you want to shut down MATLAB and MATLAB Proxy?',
            callback: fetchShutdownIntegration
        },
        SIGN_OUT: {
            type: 'confirmation',
            message: licensingConfirmationMessage,
            callback: fetchUnsetLicensing
        },
        HELP: {
            type: 'help'
        }
    };

    function getBtnClass (btn) {
        const cls = 'btn companion_btn ';
        if (error) {
            if ((ERROR_TYPE_MAP[btn] || []).includes(error.type)) {
                return cls + 'btn_color_blue';
            }
        } else if (btn === 'start' && (authEnabled && !isAuthenticated)) {
            // if there's no error, then highlight the "Start" button (if visible)
            return cls + 'btn_color_blue';
        }
        return cls + 'btn_color_mediumgray';
    }

    return (
        <div id="controls" className="labels-on-top">
            <button
                id="startMatlab"
                data-testid='startMatlabBtn'
                className={getBtnClass(matlabUp
                    ? 'restart'
                    : 'start')}
                onClick={() => callback(Confirmations.START)}
                disabled={!licensed || matlabStarting || matlabStopping || (authEnabled && !isAuthenticated) || (licensingIsMhlm && !isEntitled)}
                data-tooltip-id="control-button-tooltip"
                data-tooltip-content={`${matlabUp
                    ? 'Restart'
                    : 'Start'}  MATLAB`}
                data-tooltip-variant="info"
            >
                <span className={`icon-custom-${matlabUp
                    ? 're'
                    : ''}start`}></span>
                <span className='btn-label'>{`${matlabUp
                    ? 'Restart'
                    : 'Start'} MATLAB`}</span>
            </button>
            <button
                id="stopMatlab"
                data-testid='stopMatlabBtn'
                className={getBtnClass('stop')}
                onClick={() => callback(Confirmations.STOP)}
                disabled={ matlabStopping || matlabDown || (authEnabled && !isAuthenticated)}
                data-tooltip-id="control-button-tooltip"
                data-tooltip-content="Stop MATLAB"
                data-tooltip-variant="info"
            >
                <span className='icon-custom-stop'></span>
                <span className='btn-label'>Stop MATLAB</span>
            </button>
            <button
                id="unsetLicensing"
                data-testid='unsetLicensingBtn'
                className={getBtnClass('sign-out')}
                onClick={() => callback(Confirmations.SIGN_OUT)}
                disabled={!canResetLicensing || (authEnabled && !isAuthenticated)}
                data-tooltip-id="control-button-tooltip"
                data-tooltip-content= {licensingData.dataTip}
                data-tooltip-variant="info"
            >
                <span className='icon-custom-sign-out'></span>
                <span className='btn-label'>{licensingData.label}</span>
            </button>
            {shouldShowShutdownButton && <button
                id="shutdownMatlabandMatlabProxy"
                data-testid='shutdownBtn'
                className={getBtnClass('shutdown')}
                onClick={() => callback(Confirmations.SHUTDOWN)}
                disabled={!canResetLicensing || (authEnabled && !isAuthenticated)}
                data-tooltip-id="control-button-tooltip"
                data-tooltip-content= "Stop MATLAB and MATLAB Proxy"
                data-tooltip-variant="info"
            >
                <span className='icon-custom-shutdown'></span>
                <span className='btn-label'>Shut Down</span>
            </button>}
            <a
                id="feedback"
                data-testid='feedbackLink'
                className="btn btn_color_mediumgray companion_btn"
                href="https://github.com/mathworks/matlab-proxy/issues/new/choose"
                target="_blank"
                rel="noreferrer"
                data-tooltip-id="control-button-tooltip"
                data-tooltip-content="Provide feedback (opens matlab-proxy repository on github.com in a new tab)"
                data-tooltip-variant="info"
            >
                <span className='icon-custom-feedback'></span>
                <span className='btn-label'>Feedback</span>
            </a>
            <button
                id="Help"
                data-testid='helpBtn'
                className="btn btn_color_mediumgray companion_btn"
                onClick={() => callback(Confirmations.HELP)}
                data-tooltip-id="control-button-tooltip"
                data-tooltip-content="See a description of the buttons"
                data-tooltip-variant="info"
            >
                <span className='icon-custom-help'></span>
                <span className='btn-label'>Help</span>
            </button>
            <ReactTooltip
                id="control-button-tooltip"
                ref={tooltipRef}
                place="top"
                type="info"
                effect="solid"
            />
        </div>
    );
}

// TODO: Should these be required ?
Controls.propTypes = {
    confirmHandler: PropTypes.func,
    callback: PropTypes.func.isRequired
};

export default Controls;
