// Copyright 2020-2025 The MathWorks, Inc.

import React from 'react';
import PropTypes from 'prop-types';

// Made the Confirmation component more scalable where one can customize all the messages which are to be displayed.
function Confirmation ({ confirm, cancel, title = 'Confirmation', cancelButton = 'Cancel', confirmButton = 'Confirm', children }) {
    return (
        <div className="modal show"
            id="confirmation"
            tabIndex="-1"
            role="dialog"
            aria-labelledby="confirmation-dialog-title">
            <div className="modal-dialog modal-dialog-centered"
                role="document">
                <div className="modal-content">
                    <div className="modal-header">
                        <h4 className="modal-title" id="confirmation-dialog-title">{title}</h4>
                    </div>
                    <div className="modal-body">
                        {children}
                    </div>
                    <div className="modal-footer">
                        <button onClick={cancel} data-testid='cancelButton' className="btn companion_btn btn_color_blue">{cancelButton}</button>
                        <button onClick={confirm} data-testid='confirmButton' className="btn btn_color_blue">{confirmButton}</button>
                    </div>
                </div>
            </div>
        </div>
    );
}

Confirmation.propTypes = {
    confirm: PropTypes.func.isRequired,
    cancel: PropTypes.func.isRequired,
    title: PropTypes.string,
    cancelButton: PropTypes.string,
    confirmButton: PropTypes.string,
    children: PropTypes.node.isRequired
};

export default Confirmation;
