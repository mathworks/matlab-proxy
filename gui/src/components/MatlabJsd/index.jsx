// Copyright 2020-2025 The MathWorks, Inc.

import React, { useEffect } from 'react';
import PropTypes from 'prop-types';
import './MatlabJsd.css';
import {
    selectMatlabUp
} from '../../selectors';
import { useSelector } from 'react-redux';

function MatlabJsd ({ url, iFrameRef, shouldListenForEvents, handleUserInteraction }) {
    const matlabUp = useSelector(selectMatlabUp);

    useEffect(() => {
        // access the DOM node corresponding to the MatlabJSD Iframe
        const MatlabJsdIframeDom = iFrameRef.current;
        const userEvents = ['click', 'mousemove', 'keydown'];

        if (MatlabJsdIframeDom && shouldListenForEvents) {
            console.log('Adding event handlers to IFrame');
            userEvents.forEach((eventName) => {
                MatlabJsdIframeDom.contentWindow.addEventListener(eventName, handleUserInteraction, false);
            });
        }

        return () => {
            if (MatlabJsdIframeDom && shouldListenForEvents) {
                console.log('Removing event handlers from IFrame');
                userEvents.forEach((eventName) => {
                    MatlabJsdIframeDom.contentWindow.removeEventListener(eventName, handleUserInteraction, false);
                });
            }
        };
    }, [shouldListenForEvents, matlabUp, iFrameRef, handleUserInteraction]);

    return (
        <div id="MatlabJsd">
            <iframe
                ref={iFrameRef}
                title="MATLAB JSD"
                src={url}
                frameBorder="0"
                allowFullScreen />
        </div>
    );
}

MatlabJsd.propTypes = {
    url: PropTypes.string.isRequired,
    iFrameRef: PropTypes.object.isRequired,
    shouldListenForEvents: PropTypes.bool.isRequired,
    handleUserInteraction: PropTypes.func.isRequired
};

export default MatlabJsd;
