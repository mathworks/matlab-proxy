// Copyright 2020-2025 The MathWorks, Inc.

import React from 'react';
import Controls from './index';
import App from '../App';
import { render } from '../../test/utils/react-test';
import { fireEvent } from '@testing-library/react';
import state from '../../test/utils/state';
import * as actionCreators from '../../actionCreators';

const _ = require('lodash');

describe('Controls Component', () => {
    let initialState, callbackFn;

    beforeEach(() => {
        initialState = _.cloneDeep(state);
        initialState.serverStatus.licensingInfo.entitlementId = initialState.serverStatus.licensingInfo.entitlements[0].id;
        initialState.serverStatus.isSubmitting = false;
        callbackFn = vi.fn().mockImplementation(() => {});        
    });

    afterEach(() => {
        vi.clearAllMocks();
    });

    it('should render without crashing', () => {
        render(<Controls callback={callbackFn} />);
    });

    it('should startMatlab on button click', () => {
        const { getByTestId } = render(<Controls callback={callbackFn} />, {
            initialState
        });

        const btn = getByTestId('startMatlabBtn');
        fireEvent.click(btn);

        expect(callbackFn).toHaveBeenCalledTimes(1);
    });

    it('should stopMatlab on button click', () => {
        const { getByTestId } = render(<Controls callback={callbackFn} />, {
            initialState
        });

        const btn = getByTestId('stopMatlabBtn');
        fireEvent.click(btn);

        expect(callbackFn).toHaveBeenCalledTimes(1);
    });

    it('should unsetLicensing on button click', () => {
        const { getByTestId } = render(<Controls callback={callbackFn} />, {
            initialState
        });

        const btn = getByTestId('unsetLicensingBtn');
        fireEvent.click(btn);

        expect(callbackFn).toHaveBeenCalledTimes(1);
    });

    it('should open Help on button click', () => {
        const { getByTestId } = render(<Controls callback={callbackFn} />, {
            initialState
        });

        const btn = getByTestId('helpBtn');
        fireEvent.click(btn);

        expect(callbackFn).toHaveBeenCalledTimes(1);
    });

    it('should render additional css style when error', () => {
        initialState.error = {
            type: 'OnlineLicensingError'
        };

        const { getByTestId } = render(<Controls callback={callbackFn} />, {
            initialState
        });

        const btn = getByTestId('startMatlabBtn');
        expect(btn).toHaveClass('btn_color_blue');
    });

    it('should restart matlab upon clicking the Start/Restart Matlab button', () => {
    // Hide the tutorial and make the overlay visible.
        initialState.tutorialHidden = true;
        initialState.overlayVisibility = true;

        const mockFetchStartMatlab = vi.spyOn(actionCreators, 'fetchStartMatlab').mockImplementation(() => {
            return () => Promise.resolve();
        });

        const mockFetchServerStatus= vi.spyOn(actionCreators, 'fetchServerStatus').mockImplementation(() => {
            return () => Promise.resolve();
        });

        const { getByTestId, container } = render(<App />, {
            initialState
        });

        const startMatlabButton = getByTestId('startMatlabBtn');
        fireEvent.click(startMatlabButton);

        expect(container.querySelector('#confirmation')).toBeInTheDocument();

        const confirmButton = getByTestId('confirmButton');
        fireEvent.click(confirmButton);

        const tableData = container.querySelector('.details');
        expect(tableData.innerHTML).toContain('Running');
        mockFetchStartMatlab.mockRestore();            
        mockFetchServerStatus.mockRestore();            
    });

    it('should show shutdown button for matlab-proxy', () => {
        // Hide the tutorial and make the overlay visible.
        initialState.tutorialHidden = true;
        initialState.overlayVisibility = true;

        const { getByTestId } = render(<Controls callback={callbackFn} />, {
            initialState
        });

        const btn = getByTestId('shutdownBtn');

        expect(btn).toBeInTheDocument();
    });

    it('should not show shutdown button for non matlab-proxy environments', () => {
        // Hide the tutorial and make the overlay visible.
        initialState.tutorialHidden = true;
        initialState.overlayVisibility = true;

        // Update the envConfig to not show shutdown button
        initialState.envConfig.should_show_shutdown_button = false;

        const { container } = render(<Controls callback={callbackFn} />, {
            initialState
        });

        const btn = container.querySelector('#shutdownMatlabandMatlabProxy');

        expect(btn).not.toBeInTheDocument();
    });
});
