// Copyright 2024-2025 The MathWorks, Inc.

// Dialog box that pops up when the main timer has expired.
// The user can either resume or shutdown the current session of matlab proxy.
// In case of no interaction, the application will automatically shutdown after
// 'bufferTimeout' seconds (which is given as a prop to the component)

import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { useDispatch, useSelector } from 'react-redux';
import {
    selectIntegrationName
} from '../../selectors';
import { setOverlayVisibility } from '../../actionCreators';
import './ShutdownWarning.css';

function ShutdownWarning ({ bufferTimeout, resumeCallback }) {
    const dispatch = useDispatch();
    const integrationName = useSelector(selectIntegrationName);

    const [bufferTimeoutLeft, setBufferTimeoutLeft] = useState(bufferTimeout);

    useEffect(() => {
        const intervalId = setInterval(() => {
            setBufferTimeoutLeft(prevValue => prevValue - 1);
        }, 1000);

        return () => clearInterval(intervalId);
    }, []);

    return (
        <div className="modal show" data-testid="ShutdownWarning"
            id="information"
            tabIndex="-1"
            role="dialog">
            <div className="modal-dialog modal-dialog-centered" role="document">
                <div className="modal-content alert alert-warning">
                    <div className="modal-header">
                        <span className="alert_icon icon-alert-warning" />
                        <h4 className="modal-title alert_heading" id="information-dialog-title">Warning</h4>
                    </div >
                    <div className="modal-body">
                        <div className="details">
                            <div>No activity detected. {integrationName} will shutdown in {bufferTimeoutLeft} seconds.</div>
                        </div>
                    </div>
                    <div className="modal-footer">
                        <div>
                            <button
                                className='btn'
                                id='resume-button'
                                onClick={() => {
                                    resumeCallback();
                                    dispatch(setOverlayVisibility(false));
                                }}
                            >
                                <span className='btn-label'>Resume Session</span>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

ShutdownWarning.propTypes = {
    bufferTimeout: PropTypes.number.isRequired,
    resumeCallback: PropTypes.func.isRequired
};

export default ShutdownWarning;
