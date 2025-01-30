// Copyright 2020-2025 The MathWorks, Inc.

import { render } from '../../test/utils/react-test';
import { fireEvent, waitFor } from '@testing-library/react';
import { renderHook, act } from '@testing-library/react-hooks';
import React from 'react';
import OverlayTrigger from './index';
import state from '../../test/utils/state';

const _ = require('lodash');

describe('OverlayTrigger Component', () => {
    let mockIntersectionObserver, observe, unobserve, disconnect, initialState;

    beforeEach(() => {
    // creating a mock intersection observer to check whether the observe function will be called when resizing viewport
        mockIntersectionObserver = vi.fn();
        observe = vi.fn();
        unobserve = vi.fn();
        disconnect = vi.fn();
        initialState = _.cloneDeep(state);
        initialState.tutorialHidden = false;
        initialState.overlayVisibility = true;

        mockIntersectionObserver.mockReturnValue({
            observe,
            unobserve,
            disconnect
        });

        window.IntersectionObserver = mockIntersectionObserver;
    });

    afterEach(() => {
        vi.clearAllMocks();
    });

    // returns the width and height of the current window
    function getWindowDimensions () {
        const { innerWidth: width, innerHeight: height } = window;
        return { width, height };
    }

    // add an event listener to the window for 'resize'
    // Have a function that updates state with the new window size
    // Remove the event listener when the component unmounts
    function useWindowDimensions () {
        const [windowDimensions, setWindowDimensions] = React.useState(
            getWindowDimensions()
        );
        React.useEffect(() => {
            function handleResize () {
                setWindowDimensions(getWindowDimensions());
            }
            window.addEventListener('resize', handleResize);
            return () => window.removeEventListener('resize', handleResize);
        }, []);
        return windowDimensions;
    }

    it('should resize the viewport and call observe function', async () => {
        render(<OverlayTrigger />, {
            initialState
        });

        const { result } = renderHook(() => useWindowDimensions());

        act(() => {
            window.innerWidth = 200;
            window.innerHeight = 200;
            fireEvent(window, new Event('resize'));
        });

        await waitFor(() => {
            // check if the viewport is resized
            expect(result.current.width).toBe(200);
            expect(result.current.height).toBe(200);

            // check that the observe intersection observer vi function has been called
            // We conclude the working of intersection observer after resizing viewport because
            // the observe vi function of our mock intersection observer has been called
            expect(observe).toHaveBeenCalledTimes(1);
        });
    });
});