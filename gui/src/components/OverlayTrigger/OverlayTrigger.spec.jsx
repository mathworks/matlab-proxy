// Copyright 2020-2025 The MathWorks, Inc.

import { render } from '../../test/utils/react-test';
import { fireEvent } from '@testing-library/react';
import React from 'react';
import OverlayTrigger from './index';
import configureMockStore from 'redux-mock-store';

import * as actions from '../../actions';
import * as actionCreators from '../../actionCreators';
import state from '../../test/utils/state';
const _ = require('lodash');

describe('OverlayTrigger Component', () => {
    let mockStore, initialState;
    beforeEach(() => {
        initialState = _.cloneDeep(state);
        initialState.tutorialHidden = false;
        initialState.overlayVisibility = true;
        mockStore = configureMockStore();

        const mockIntersectionObserver = vi.fn();
        mockIntersectionObserver.mockReturnValue({
            observe: () => null,
            unobserve: () => null,
            disconnect: () => null
        });
        window.IntersectionObserver = mockIntersectionObserver;
    });

    afterEach(() => {
        vi.clearAllMocks();
    });

    it('should render without crashing', () => {
        const { getByTitle } = render(<OverlayTrigger />, {
            initialState
        });

        expect(getByTitle('tools icon')).toBeInTheDocument();
    });

    it('should close tutorial on click', () => {
        const { getByTestId, container } = render(<OverlayTrigger />, {
            initialState
        });

        // grab the tutorial close button and click on it.
        const tutorialCloseBtn = getByTestId('tutorialCloseBtn');
        fireEvent.click(tutorialCloseBtn);

        // Check if the tutorial is not rendered as it was closed.
        const tutorial = container.querySelector('#trigger-tutorial');
        expect(tutorial).not.toBeInTheDocument();
    });

    it('should dispatch SET_TRIGGER_POSITION when overlay trigger is moved', async () => {
        const store = mockStore(state);
        // dispatching an action to setTriggerPosition to (22, 22) in the mockstore
        store.dispatch(actionCreators.setTriggerPosition(22, 22));

        const actionsFromStore = store.getActions();
        const expectedPayload = {
            type: actions.SET_TRIGGER_POSITION,
            x: 22,
            y: 22
        };

        // Check if the action dispatched from mockstore is same as expected action
        expect(actionsFromStore).toEqual([expectedPayload]);
    });

    it('should display correct text on the overlay trigger', async () => {
        const { getByRole } = render(<OverlayTrigger />, {
            initialState
        });
        const buttonElement = getByRole('button', { name: 'Menu' });
        expect(buttonElement).toHaveAttribute('data-tooltip-content', 'Open the MATLAB Desktop settings');
    });
});