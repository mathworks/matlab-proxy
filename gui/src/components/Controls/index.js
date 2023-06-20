// Copyright (c) 2020-2023 The MathWorks, Inc.

import React, { useMemo } from 'react';
import PropTypes from 'prop-types';
import { useSelector } from 'react-redux';
import ReactTooltip from 'react-tooltip';
import {
    selectSubmittingServerStatus,
    selectLicensingInfo,    
    selectLicensingProvided,
    selectMatlabUp,
    selectMatlabStarting,
    selectMatlabStopping,
    selectMatlabDown, 
    selectMatlabVersion,
    selectError,
    selectIsAuthenticated,
    selectAuthEnabled,
} from '../../selectors';
import {
    fetchStartMatlab,
    fetchStopMatlab,
    fetchTerminateIntegration,
    fetchUnsetLicensing
} from '../../actionCreators';
import './Controls.css';

// Suggested actions for certain errors
const ERROR_TYPE_MAP = {
    'sign-out': ['NetworkLicensingError', 'EntitlementError'],
    'restart': ['OnlineLicensingError']
};

function Controls({
    callback
}) {
    const submitting = useSelector(selectSubmittingServerStatus);
    const licensed = useSelector(selectLicensingProvided);
    const matlabStarting = useSelector(selectMatlabStarting);
    const matlabUp = useSelector(selectMatlabUp);
    const matlabStopping = useSelector(selectMatlabStopping);
    const matlabDown = useSelector(selectMatlabDown);
    const matlabVersion = useSelector(selectMatlabVersion);
    const error = useSelector(selectError);
    const authEnabled = useSelector(selectAuthEnabled);
    const isAuthenticated = useSelector(selectIsAuthenticated);
    const licensingInfo = useSelector(selectLicensingInfo);
    const canResetLicensing = licensed && !submitting;

    const feedbackBody = useMemo(
        () => `%0D%0A
Thank you for providing feedback.%0D%0A
%0D%0A
MATLAB version: ${matlabVersion}%0D%0A`,
        [matlabVersion]
    );

    let licensingData, licensingConfirmationMessage;
    switch (licensingInfo?.type) {
        case "mhlm":
            licensingData =  {
                label: 'Sign Out',
                dataTip : 'Sign out of MATLAB',
            };
            licensingConfirmationMessage = `Are you sure you want to sign out of MATLAB?`
            break;
        case "nlm":
            licensingData =  {
                label: 'Remove License Server Address',
                dataTip : 'Remove the network license manager server address',
            };  
            licensingConfirmationMessage = `Are you sure you want to remove the network license manager server address?`
            break;

        case "existing_license":
            licensingData =  {
                label: 'Stop using Existing License',
                dataTip : 'Stop using existing license',
            };
            licensingConfirmationMessage = `Are you sure you want to stop using an Existing License?`
            break;
        
        default:
            licensingData =  {
                label: 'None',
                dataTip : 'None',
            }; 
            licensingConfirmationMessage = null  
        }



    const Confirmations = {
        START: {
            type: 'confirmation',
            message: `Are you sure you want to ${ matlabUp ? 're' : ''}start MATLAB?`,
            callback: fetchStartMatlab
        },
        STOP: {
            type: 'confirmation',
            message: 'Are you sure you want to stop MATLAB?',
            callback: fetchStopMatlab
        },
        TERMINATE: {
            type: 'confirmation',
            message: 'Are you sure you want to terminate MATLAB and the backing matlab-proxy server?',
            callback: fetchTerminateIntegration
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

    function getBtnClass(btn) {
        let cls = 'btn companion_btn ';
        if (error) {
            if ((ERROR_TYPE_MAP[btn] || []).includes(error.type)) {
                return cls + 'btn_color_blue';
            }
        } else if (btn === 'start' && (authEnabled && !isAuthenticated)) {
            // if there's no error, then highlight the "Start" button (if visible)
            return cls + 'btn_color_blue';
        }
        return cls + 'btn_color_mediumgray';
    };    

    return (
        <div id="controls" className="labels-on-top">
            <button
                id="startMatlab"
                data-testid='startMatlabBtn'
                className={getBtnClass(matlabUp ? 'restart' : 'start')}
                onClick={() => callback(Confirmations.START)}
                disabled={!licensed || matlabStarting || matlabStopping || (authEnabled && !isAuthenticated)}
                data-for="control-button-tooltip"
                data-tip={`${matlabUp ? 'Restart' : 'Start'}  MATLAB`}
            >
                <span className={`icon-custom-${matlabUp ? 're' : ''}start`}></span>
                <span className='btn-label'>{`${matlabUp ? 'Restart' : 'Start'} MATLAB`}</span>
            </button>
            <button
                id="stopMatlab"
                data-testid='stopMatlabBtn'
                className={getBtnClass('stop')}
                onClick={() => callback(Confirmations.STOP)}
                disabled={ matlabStopping || matlabDown || (authEnabled && !isAuthenticated)}
                data-for="control-button-tooltip"
                data-tip="Stop MATLAB"
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
                data-for="control-button-tooltip"
                data-tip= {licensingData.dataTip}
            >
                <span className='icon-custom-sign-out'></span>
                <span className='btn-label'>{licensingData.label}</span>
            </button>
            {/* <button
                id="terminateIntegration"
                className="btn btn_color_mediumgray companion_btn"
                style={{display: 'none'}}
                onClick={() => callback(Confirmations.TERMINATE)}
                disabled={!canTerminateIntegration}
                data-for="control-button-tooltip"
                data-tip="Terminate your MATLAB and MATLAB in Jupyter sessions"
            >
                <span className='icon-custom-terminate'></span>
                <span className='btn-label'>End Session</span>
            </button> */}
            <a
                id="feedback"
                data-testid='feedbackLink'
                className="btn btn_color_mediumgray companion_btn"
                href={`mailto:cloud@mathworks.com?subject=MATLAB-PROXY Feedback&body=${feedbackBody}`}
                data-for="control-button-tooltip"
                data-tip="Send feedback (opens your default email application)"
            >
                <span className='icon-custom-feedback'></span>
                <span className='btn-label'>Feedback</span>
            </a>
            <button
                id="Help"
                data-testid='helpBtn'
                className="btn btn_color_mediumgray companion_btn"
                onClick={() => callback(Confirmations.HELP)}
                data-for="control-button-tooltip"
                data-tip="See a description of the buttons"
            >
                <span className='icon-custom-help'></span>
                <span className='btn-label'>Help</span>
            </button>
            <ReactTooltip
                id="control-button-tooltip"
                place="top"
                type="info"
                effect="solid"
            />
        </div>
    );
}

Controls.propTypes = {
    confirmHandler: PropTypes.func
};

export default Controls;
