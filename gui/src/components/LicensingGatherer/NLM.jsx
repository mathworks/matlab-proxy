// Copyright 2020-2025 The MathWorks, Inc.

import React, { useState } from 'react';
import { useDispatch } from 'react-redux';
import {
    fetchSetLicensing
} from '../../actionCreators';

// Regular expression to match port@hostname,
// where port is any number and hostname is alphanumeric
// Regex FOR
//      Start of Line, Any number of 0-9 digits , @, any number of nonwhite space characters with "- _ ." allowed, and EOL
// IS:
// ^[0-9]+[@](\w|\_|\-|\.)+$
// Server triad is of the form : port@host1,port@host2,port@host3

// eslint-disable-next-line
const connStrRegex = /^[0-9]+[@](\w|\_|\-|\.)+/

function validateInput (nlmConnectionsStr) {
    /*
    nlmConntectionsStr must contain server names (each of the form port@hostname) separated by \':\' on unix or \';\' on windows(server triads however must be comma seperated)

    Some valid nlmConntectionsStr values are:
    1) port@hostname
    3) port1@hostname1:port2@hostname2
    4) port1@hostname1:port2@hostname2:port3@hostname3
    5) port1@hostname1:port2@hostname2,port3@hostname3,port4@hostname4:port5@hostname5
    */

    const nlmConnectionStrs = nlmConnectionsStr.split(/:|;|,/);

    // All strings comply with port@hostname format
    for (const nlmConnectionStr of nlmConnectionStrs) {
        if (!connStrRegex.test(nlmConnectionStr)) {
            return false;
        }
    }
    return true;
}

function NLM () {
    const dispatch = useDispatch();
    const [connStr, setConnStr] = useState('');
    const [changed, setChanged] = useState(false);

    const valid = validateInput(connStr);

    function submitForm (event) {
        event.preventDefault();
        dispatch(fetchSetLicensing({
            type: 'nlm',
            connectionString: connStr
        }));
    }

    return (
        <div id="NLM">
            <form onSubmit={submitForm}>
                <div className={`form-group has-feedback ${changed
                    ? (valid
                        ? 'has-success'
                        : 'has-error')
                    : ''}`}>
                    <label htmlFor="nlm-connection-string">License Server Address</label>
                    <input id="nlm-connection-string"
                        type="text"
                        required={true}
                        placeholder={'port@hostname'}
                        className="form-control"
                        aria-invalid={!valid}
                        value={connStr}
                        onChange={event => { setChanged(true); setConnStr(event.target.value); }}
                    />
                    <span className="glyphicon form-control-feedback glyphicon-remove"></span>
                    <span className="glyphicon form-control-feedback glyphicon-ok"></span>
                </div>
                <input type="submit" id="submit" value="Submit" className="btn btn_color_blue" disabled={!valid} />
            </form>
        </div>
    );
}

export default NLM;
