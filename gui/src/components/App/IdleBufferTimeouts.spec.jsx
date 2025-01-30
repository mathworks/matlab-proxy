// Copyright 2024-2025 The MathWorks, Inc.

// File to test IDLE and BUFFER timeouts.
// Need a seperate file for mocking BUFFER_TIMEOUT_DURATION before App component is imported for testing.

import React from 'react';

import fetchMock from 'fetch-mock';
import state from '../../test/utils/state';
import { createStatusResponse } from '../../test/utils/responses';
import { render } from '../../test/utils/react-test';
import { waitFor } from '@testing-library/react';
import * as responses from '../../test/utils/responses';

import App from './index';
//
// Mock BUFFER_TIMEOUT_DURATION before import App.
vi.mock('../../constants', async (importOriginal) => {
    const actualConstants = await importOriginal();
    return {
        ...actualConstants,
        BUFFER_TIMEOUT_DURATION: 1
    };
});
const _ = require('lodash');

describe('Timeouts in App Component', () => {
    let initialState;
    beforeEach(() => {
        initialState = _.cloneDeep(state);

        // As the tests are run in a NodeJS environment whereas the correct values for document.URL and window.location.href
        // are set by the browser, for tests, set the appropriate values for document.URL, window.location.href and window.location.origin
        // for the component to render without errors
        // Delete and redefine 'origin' and 'href' properties as they are read-only.
        delete window.location;
        window.location = {
            origin: '/',
            href: 'http://127.0.0.1/'
        };

        initialState.serverStatus.licensingInfo.entitlements = [{ id: '1234567', label: null, license_number: '7654321' }];
        initialState.serverStatus.licensingInfo.entitlementId = '1234567';

        const mockIntersectionObserver = vi.fn();
        mockIntersectionObserver.mockReturnValue({
            observe: () => null,
            disconnect: () => null
        });

        window.IntersectionObserver = mockIntersectionObserver;
    });

    afterEach(() => {
        vi.clearAllMocks();
        fetchMock.restore();
    });

    it('should dispatch fetchShutdownIntegration when both IDLE and BUFFER timer expires', async () => {
    // Hide the tutorial and make the overlay visible
        initialState.tutorialHidden = true;
        initialState.overlayVisibility = true;
        initialState.idleTimeoutDuration = 1;
        const mockBufferTimeoutDuration = 1;
        // Takes a tiny amount of time(10ms) apart from idleTimeoutDuration + bufferTimeoutDuration
        // for fetchMock to be called for the second time. Only specific to this test. Using 1000ms for test to pass in CI systems.
        const additionalTimeForFetchMock = 1;

        // // Mock initial fetchServerStatus response
        fetchMock.getOnce('/get_status', {
            body: createStatusResponse,
            headers: { 'content-type': 'application/json' }
        });

        // Mock fetchShutdownIntegration response
        fetchMock.deleteOnce('/shutdown_integration', {
            body: createStatusResponse,
            headers: { 'content-type': 'application/json' }
        });

        render(<App />, {
            initialState
        });

        await waitFor(() => {
            expect(fetchMock.called('get_status')).toBe(true);
            expect(fetchMock.called('shutdown_integration')).toBe(true);
        }, { timeout: initialState.idleTimeoutDuration * 1000 + mockBufferTimeoutDuration * 1000 + additionalTimeForFetchMock * 1000 });
    });

    it('should show TerminationWarning dialog box when IDLE timer expires', async () => {
    // Hide the tutorial and make the overlay visible
        initialState.tutorialHidden = true;
        initialState.overlayVisibility = true;
        initialState.idleTimeoutDuration = 1;

        // Mock initial fetchServerStatus response
        fetchMock.getOnce('/get_status', {
            status: 200,
            body: responses.createStatusResponse,
            headers: { 'Content-Type': 'application/json' }

        });

        const consoleSpy = vi.spyOn(console, 'log').mockImplementation();

        const { getByTestId } = render(<App />, {
            initialState
        });

        await waitFor(() => {
            const shutdownWarningDialogBox = getByTestId('ShutdownWarning');
            expect(shutdownWarningDialogBox).toBeInTheDocument();
            const hasLog = consoleSpy.mock.calls.some(call => {
                return call[0].includes('The IDLE timer has expired due to inactivity. Will display Shutdown Warning to the user.');
            });
            expect(hasLog).toBe(true);
        }, { timeout: initialState.idleTimeoutDuration * 1000 });

        consoleSpy.mockRestore();
    });
});
