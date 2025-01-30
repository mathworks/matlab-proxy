// Copyright 2020-2025 The MathWorks, Inc.

import React from 'react';
import { render } from '../../test/utils/react-test';
import { fireEvent } from '@testing-library/react';
import App from './index';
import * as actionCreators from '../../actionCreators';
import state from '../../test/utils/state';
import { MAX_REQUEST_FAIL_COUNT } from '../../constants';
import { MWI_AUTH_TOKEN_NAME_FOR_HTTP } from '../../constants';

import { vi } from 'vitest';

const _ = require('lodash');


describe('App Component', () => {
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
        // Set initial hasFetched to true to skip mocking the initial /get_status request
        initialState.serverStatus.hasFetched = true;

        const mockIntersectionObserver = vi.fn();
        mockIntersectionObserver.mockReturnValue({
            observe: () => null,
            disconnect: () => null
        });

        window.IntersectionObserver = mockIntersectionObserver;
    });

    afterEach(() => {
        vi.clearAllMocks();
    });

    it('renders app without crashing', () => {
        const { getByTestId } = render(<App />, {initialState});
        expect(getByTestId('app')).toBeInTheDocument();
    });

    it('should render overlayTrigger (after closing the tutorial)', () => {
        // Hide the tutorial before rendering the component.
        initialState.tutorialHidden = true;
        initialState.overlayVisibility = false;

        const { getByTestId } = render(<App />, {
            initialState
        });

        // grab the overlayTrigger
        const overlayTriggerComponent = getByTestId(
            'overlayTrigger'
        );

        expect(overlayTriggerComponent).toBeInTheDocument();
    });

    it('should render LicensingGatherer component within the App component when no licensing is provided and user is authenticated', () => {
        // Set licensingInfo to empty object.
        initialState.overlayVisibility = true;
        initialState.serverStatus.licensingInfo = {};
        initialState.authentication.enabled = true;
        initialState.authentication.status = true;

        const { getByRole } = render(<App />, { initialState });

        const licensingGathererComponent = getByRole(
            'dialog', { description: 'licensing-dialog' });

        expect(licensingGathererComponent).toBeInTheDocument();
    });

    it('should render LicensingGatherer component within the App component when no licensing is provided and authentication is disabled', () => {
        // Set licensingInfo to empty object.
        initialState.overlayVisibility = true;
        initialState.serverStatus.licensingInfo = {};
        initialState.authentication.enabled = false;

        const { getByRole } = render(<App />, { initialState });

        const licensingGathererComponent = getByRole(
            'dialog', { description: 'licensing-dialog' });

        expect(licensingGathererComponent).toBeInTheDocument();
    });

    it('should render Information Component within App Component after licensing is provided and user is authenticated', () => {
        // Hide the tutorial and make the overlay visible.
        initialState.tutorialHidden = true;
        initialState.overlayVisibility = true;

        initialState.authentication.enabled = true;
        initialState.authentication.status = true;

        // Rendering the App component with the above changes to the initial
        // state should render the Information Component.
        const { getByRole } = render(<App />, {
            initialState
        });
        const informationComponent = getByRole(
            'dialog', { description: 'information-dialog' });

        expect(informationComponent).toBeInTheDocument();
    });

    it('should render Information Component within App Component after licensing is provided and auth is not enabled', () => {
        // Hide the tutorial and make the overlay visible.
        initialState.tutorialHidden = true;
        initialState.overlayVisibility = true;

        initialState.authentication.enabled = false;

        // Rendering the App component with the above changes to the initial
        // state should render the Information Component.
        const { getByRole } = render(<App />, {
            initialState
        });

        const informationComponent = getByRole(
            'dialog', { description: 'information-dialog' });

        expect(informationComponent).toBeInTheDocument();
    });

    it('should display integration terminated error', () => {
        // Hide the tutorial, make the overlay visible and set fetchFailCount to MAX_REQUEST_FAIL_COUNT
        initialState.tutorialHidden = true;
        initialState.overlayVisibility = true;
        initialState.serverStatus.fetchFailCount = MAX_REQUEST_FAIL_COUNT;

        // Rendering the App component with above changes to the initial state
        // will terminate the integration.
        const { container } = render(<App />, {
            initialState
        });

        const paragraphElement = [...container.getElementsByTagName('pre')][0];

        expect(paragraphElement.textContent.includes('terminated or the session ended')).toBe(true);
    });

    it('should display MatlabInstallError', () => {
        initialState.error = {
            type: 'MatlabInstallError',
            message: 'Matlab Installation error. Exited with status code -9'
        };
        initialState.serverStatus.licensingInfo = {};
        initialState.overlayVisibility = true;

        const { container } = render(<App />, {
            initialState
        });

        const paragraphElements = [...container.getElementsByTagName('pre')];

        expect(
            paragraphElements.some((p) =>
                p.textContent.includes(initialState.error.message)
            )
        ).toBe(true);
    });

    it('should display Confirmation component ', () => {
        // Hide the tutorial and make the overlay visible
        initialState.tutorialHidden = true;
        initialState.overlayVisibility = true;

        const { getByTestId, container } = render(<App />, {
            initialState
        });

        const startMatlabBtn = getByTestId('startMatlabBtn');

        fireEvent.click(startMatlabBtn);

        const confirmMatlabRestart = container
            .getElementsByClassName('modal-body')
            .item(0);

        expect(confirmMatlabRestart.textContent).toMatch('restart MATLAB?');

        const confirmBtn = getByTestId('confirmButton');
        expect(confirmBtn).toBeInTheDocument();
    });

    it('should display Help Component', () => {
        // Hide the tutorial and make the overlay visible
        initialState.tutorialHidden = true;
        initialState.overlayVisibility = true;

        const { getByTestId, container } = render(<App />, {
            initialState
        });

        // Grab the help button and click it.
        const helpBtn = getByTestId('helpBtn');
        fireEvent.click(helpBtn);

        const helpElement = container.querySelector('#confirmation-dialog-title');

        expect(helpElement.textContent).toMatch('Help');
    });

    it('should set the window location from state', () => {
        // define new complete url for document.URL for baseUrl variable to evaluate correctly
        const url = 'http://localhost.com:5555/matlab/index.html';

        // Mock the URL property of the document
        Object.defineProperty(window, 'location', {
            value: { href: url, origin: 'http://localhost.com:5555'},
            writable: true,
        });
       
        Object.defineProperty(document, 'URL', {
            value: url,
            writable: true, 
        });

    
        initialState.loadUrl = url;
        render(<App />, { initialState });
    
        // Check if href has been set to loadUrl by the useEffect
        expect(window.location.href).toBe(url);
    });

    const tokenInQuery = '12345';
    it.each([
        [`?${MWI_AUTH_TOKEN_NAME_FOR_HTTP}=${tokenInQuery}&test1=1&test2=2`, tokenInQuery],
        [`?test1=1&${MWI_AUTH_TOKEN_NAME_FOR_HTTP}=${tokenInQuery}&test2=2`, tokenInQuery],
        [`?test1=1&test2=2&${MWI_AUTH_TOKEN_NAME_FOR_HTTP}=${tokenInQuery}`, tokenInQuery]
    ])('should pick the token correctly when the query parameters are \'%s\'', (queryParams, expectedToken) => {
        const url = 'http://localhost.com:5555';
        const mockUpdateAuthStatus = vi.spyOn(actionCreators, 'updateAuthStatus').mockImplementation(() => {
            return () => Promise.resolve();
        });
        window.location = {
            origin: '/',
            href: url,
            search: queryParams
        };
        render(<App />, { initialState });
        expect(mockUpdateAuthStatus).toHaveBeenCalledWith(expectedToken);
        mockUpdateAuthStatus.mockRestore();
    });
});
