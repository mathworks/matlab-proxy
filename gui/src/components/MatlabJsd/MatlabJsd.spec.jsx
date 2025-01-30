// Copyright 2020-2025 The MathWorks, Inc.

import React from 'react';
import MatlabJsd from './index';
import { render } from '../../test/utils/react-test';
import { fireEvent, cleanup } from '@testing-library/react';

describe('MatlabJsd Component', () => {
    afterEach(() => {
        vi.clearAllMocks();
    });

    it('throws console.error when rendered without required prop-type', () => {
    // Mocking console.error to do nothing.
        const errorMock = vi.spyOn(console, 'error').mockImplementation(() => { });
        const errorMessages = [
            'The prop `url` is marked as required in `MatlabJsd`, but its value is `undefined`.',        
            'The prop `shouldListenForEvents` is marked as required in `MatlabJsd`, but its value is `undefined`.',
            'The prop `handleUserInteraction` is marked as required in `MatlabJsd`, but its value is `undefined`.'
        ];
        const ref = {
            current: null
        };

        const { queryByTitle } = render(<MatlabJsd iFrameRef={ref}/>);

        // Check if attribute 'src' is not present in the rendered iFrame
        const iFrame = queryByTitle('MATLAB JSD');
        expect(iFrame).not.toHaveAttribute('src');

        // Check if console.error has been called 3 times (3 required props are missing).
        expect(errorMock).toHaveBeenCalledTimes(3);

        errorMessages.forEach(function (element, index) {
            expect(console.error.mock.calls[index][2]).toContain(element);
        });
    });

    it('renders without crashing', () => {
        const ref = {
            current: null
        };
        const { queryByTitle, container } = render(
            <MatlabJsd url={'http://localhost:3000'} iFrameRef={ref} shouldListenForEvents={true} handleUserInteraction={() => {}} />
        );

        // Check if div is rendered
        expect(container.querySelector('#MatlabJsd')).toBeInTheDocument();

        // Check if url is passed to the iFrame
        const iFrame = queryByTitle('MATLAB JSD');
        expect(iFrame).toHaveAttribute('src');
    });

    it('test event handlers on iframe', () => {
        const ref = {
            current: null
        };
        const mockHandleUserEvents = vi.fn();
        const { queryByTitle } = render(
            <MatlabJsd url={'http://localhost:3000'} iFrameRef={ref} shouldListenForEvents={false} handleUserInteraction={mockHandleUserEvents} />
        );

        let iFrame = queryByTitle('MATLAB JSD');

        // Check if iFrame is rendered
        expect(iFrame).toBeInTheDocument();

        fireEvent.mouseMove(iFrame.contentWindow, { clientX: 10, clientY: 10 });
        fireEvent.click(iFrame.contentWindow);
        fireEvent.keyDown(iFrame.contentWindow, { key: 'Enter', code: 'Enter' });

        // Event handlers must not be called because shouldListenForEvents is false
        expect(mockHandleUserEvents).not.toHaveBeenCalled();

        // cleanup the rendered component before re-rendering.
        cleanup();

        render(
            <MatlabJsd url={'http://localhost:3000'} iFrameRef={ref} shouldListenForEvents={true} handleUserInteraction={mockHandleUserEvents} />
        );
        iFrame = queryByTitle('MATLAB JSD');

        // Check if iFrame is rendered
        expect(iFrame).toBeInTheDocument();

        fireEvent.mouseMove(iFrame.contentWindow, { clientX: 10, clientY: 10 });
        fireEvent.click(iFrame.contentWindow);
        fireEvent.keyDown(iFrame.contentWindow, { key: 'Enter', code: 'Enter' });

        // Check if mouse move, key down and click event handlers are fired.
        expect(mockHandleUserEvents).toHaveBeenCalledTimes(3);
    });
});
