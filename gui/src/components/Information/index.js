// Copyright (c) 2020-2023 The MathWorks, Inc.

import React, { useRef, useState } from 'react';
import PropTypes from 'prop-types';
import { useSelector, useDispatch } from 'react-redux';
import Linkify from 'react-linkify';
import {
    selectLicensingInfo,
    selectError,
    selectOverlayHidable,
    selectInformationDetails,
    selectAuthEnabled,
    selectIsAuthenticated,
    selectAuthToken,
} from '../../selectors';
import { updateAuthStatus, getAuthToken } from '../../actionCreators';
import './Information.css';

function Information({
    closeHandler,
    children
}) {
    const licensingInfo = useSelector(selectLicensingInfo);
    const error = useSelector(selectError);
    const overlayHidable = useSelector(selectOverlayHidable);

    const [token, setToken] = useState('');
    const [showToken, setShowToken] = useState(false);
    const authEnabled = useSelector(selectAuthEnabled);
    const isAuthenticated = useSelector(selectIsAuthenticated);
    const authToken = useSelector(selectAuthToken);
    const dispatch = useDispatch();
    const tokenInput = useRef();

    const [errorLogsExpanded, setErrorLogsExpanded] = useState(false);
    const errorLogsExpandedToggle = () => {
        setErrorLogsExpanded(!errorLogsExpanded);
    };

    let info;
    switch (licensingInfo?.type) {
        case "mhlm":
            info = {
                label: `Online License Manager (${licensingInfo.emailAddress})`
            };
            break;
        case "nlm":
            info = {
                label: `Network License Manager (${licensingInfo.connectionString})`
            };
            break;
        case "existing_license":            
            info = {
                label : 'Existing License'
            };
            break;
        default:
            info = {
                label: 'None'
            };
    }

    const details = useSelector(selectInformationDetails);

    const errorMessageNode = error ? (
        <div className="error-container alert alert-danger">
            <p><strong>Error</strong></p>
            <Linkify>
                <div className="error-text"><pre style={{backgroundColor: 'hsla(0,0%,100%,0)', border: 'none', fontFamily: 'inherit', fontSize: '15px'}}>{error.message}</pre></div>
            </Linkify>
        </div>
    ) : null;

    const errorLogsNode = (error && error.logs !== null && error.logs.length > 0) ? (
        <div className="expand_collapse error-logs-container">
            <h4 className={`expand_trigger ${errorLogsExpanded ? 'expanded' : 'collapsed'}`}
                onClick={errorLogsExpandedToggle}>
                <span className="icon-arrow-open-down"></span>
                <span className="icon-arrow-open-right"></span>
                Error logs
            </h4>
            <div id="error-logs"
                className={`expand_target error-container alert alert-danger ${errorLogsExpanded ? 'expanded' : 'collapsed'}`}
                aria-expanded={errorLogsExpanded}>
                <Linkify>
                    <div className="error-msg">{error.logs.join('\n').trim()}</div>
                </Linkify>
            </div>
        </div>
    ) : null;

    const onCloseClick = event => {
        if (event.target === event.currentTarget) {
            event.preventDefault();
            closeHandler();
        }
    };

    const viewToken = () => {
        // Fetch auth token from server if it is not already available in redux store
        if (!authToken) {
            dispatch(getAuthToken());
        }
        setShowToken(true);
    }

    const toggleVisibility = () => {
        tokenInput.current.type = tokenInput.current.type === 'text' ? 'password' : 'text';
    }

    const authenticate = async (token) => {
        // Update redux state with the token after validation from the backend
        dispatch(updateAuthStatus(token.trim()));

        // Reset local state variable which was used to hold user's input for token. 
        setToken('');
    }

    return (
        <div className="modal show"
            id="information"
            onClick={overlayHidable ? onCloseClick : null}
            tabIndex="-1"
            role="dialog"
            aria-labelledby="information-dialog-title"
            aria-describedby="information-dialog">
            <div className="modal-dialog modal-dialog-centered" role="document">
                <div className={`modal-content alert alert-${details.alert}`}>
                    <div className="modal-header">
                        { 
                            overlayHidable && (
                                <button
                                    type="button"
                                    className="close"
                                    data-dismiss="modal"
                                    aria-label="Close"
                                    onClick={closeHandler}>
                                    <span aria-hidden="true">&times;</span>
                                </button>
                            )
                        }
                        <span className={`alert_icon icon-alert-${details.icon}`} />
                        <h4 className="modal-title alert_heading" id="information-dialog-title">Status Information</h4>
                    </div >
                    <div className="modal-body">
                        <div className="details">
                                <div className='flex-container main-flex'>
                                    <div className='flex-item-1'>MATLAB Status:</div>
                                    <div className='flex-item-2'>
                                        <span id="spinner"
                                            className={details.spinner ? 'show' : 'hidden'}
                                        ></span>
                                        {details.label}
                                    </div>
                                </div>
                                <div className='flex-container'>
                                    <div className='flex-item-1'>Licensing:</div>
                                    <div className='flex-item-2'>{info.label}</div>
                                </div>

                                <div className='flex-container'>      
                                    {authEnabled &&
                                    <>  
                                    <div onClick={()=>{ if(showToken) setShowToken(false)}} 
                                        className={`${showToken ? 'passive-link': ''} flex-item-1`} 
                                        ><span id={`${showToken ? 'offset' : '' }`}>{isAuthenticated ? showToken ? '(Hide Token)' : 'Authenticated!' : 'Please Authenticate' }</span>
                                            {(isAuthenticated && !showToken) && <span id='icon-small' className={'alert_icon icon-alert-success flex-item-1'} />}
                                        </div>
                                        <>
                                        {isAuthenticated ? 
                                        <>
                                            <div className='flex-item-2'>
                                                <span onClick={viewToken} 
                                                className={`${!showToken ? 'passive-link': ''} flex-item-1`} > {showToken ? `${authToken}` : '(View token)'}</span>
                                            </div>
                                        </>
                                        :
                                        <div className="flex-item-2">
                                            <form id="token-form" onSubmit={(e) => e.preventDefault()} className='flex-container'>
                                            <input
                                            
                                            ref={tokenInput} 
                                            onBlur={toggleVisibility}
                                            onFocus={toggleVisibility}
                                            className='flex-item-2'
                                            id='token' name='token' placeholder='Please enter auth token' type='password' value={token} onChange={(e)=> setToken(e.target.value)}/>

                                            <button onClick={()=>authenticate(token)} className="btn btn_color_blue token-btn"
                                            >Submit</button>
                                        </form>
                                        </div>
                                        }
                                        </>
                                    </>
                                    }
                                </div>
                        </div>
                        {errorMessageNode}
                        {errorLogsNode}
                    </div>
                    <div className="modal-footer">
                        {children}
                    </div>
                </div>
            </div>
        </div>
    );
}

Information.propTypes = {
    closeHandler: PropTypes.func.isRequired
};

export default Information;