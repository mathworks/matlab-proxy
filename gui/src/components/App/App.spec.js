// Copyright (c) 2020-2023 The MathWorks, Inc.

import React from 'react';
import { render, fireEvent } from '../../test/utils/react-test';
import App from './index';

describe('App Component', () => {
  let initialState;
  beforeEach(() => {
    initialState = {
      triggerPosition: { x: 539, y: 0 },
      tutorialHidden: false,
      overlayVisibility: false,
      serverStatus: {
        licensingInfo: { type: 'MHLM', emailAddress: 'abc@mathworks.com' },
        matlabStatus: 'up',
        matlabVersion: 'R2020b',
        isFetching: false,
        hasFetched: true,
        isSubmitting: false,
        fetchFailCount: 0,
        wsEnv: 'mw'
      },
      loadUrl: null,
      error: null,
      authInfo: {
        authEnabled: false,
        authStatus: false,
        authToken: null,
      },
    };
    const mockIntersectionObserver = jest.fn();
    mockIntersectionObserver.mockReturnValue({
      observe: () => null,
      disconnect: () => null,
    });

    window.IntersectionObserver = mockIntersectionObserver;
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  // it('renders app without crashing', () => {
  //   const { getByTestId } = render(<App />);
  //   expect(getByTestId('app')).toBeInTheDocument();
  // });

  it('should render overlayTrigger (after closing the tutorial)', () => {

    // Hide the tutorial before rendering the component.
    initialState.tutorialHidden = true;
    initialState.authInfo.authEnabled = true;
    initialState.authInfo.authStatus = true;

    const { getByTestId } = render(<App />, {
      initialState: initialState,
    });

    //grab the overlayTrigger
    const overlayTriggerComponent = getByTestId(
      'overlayTrigger'
    );

    expect(overlayTriggerComponent).toBeInTheDocument();
  });

  it('should render LicensingGatherer component within the App component when no licensing is provided and user is authenticated', () => {

    //Set lincensingInfo to empty object.
    initialState.overlayVisibility = true;
    initialState.serverStatus.licensingInfo = {};
    initialState.authInfo.authEnabled = true;
    initialState.authInfo.authStatus = true;
    
    const { getByRole } = render(<App />, { initialState: initialState });

    const licensingGathererComponent = getByRole(
      'dialog', {description: "licensing-dialog"});

    expect(licensingGathererComponent).toBeInTheDocument();
  });

  it('should render LicensingGatherer component within the App component when no licensing is provided and authentication is disabled', () => {

    //Set lincensingInfo to empty object.
    initialState.overlayVisibility = true;
    initialState.serverStatus.licensingInfo = {};
    initialState.authInfo.authEnabled = false;
    
    const { getByRole } = render(<App />, { initialState: initialState });

    const licensingGathererComponent = getByRole(
      'dialog', { description: "licensing-dialog" });
  
    expect(licensingGathererComponent).toBeInTheDocument();
  });

  it('should render Information Component within App Component after licensing is provided and user is authenticated', () => {

    // Hide the tutorial and make the overlay visible.
    initialState.tutorialHidden = true;
    initialState.overlayVisibility = true;

    initialState.authInfo.authEnabled = true;
    initialState.authInfo.authStatus = true;

    //Rendering the App component with the above changes to the initial
    // state should render the Information Component.
    const { getByRole } = render(<App />, {
      initialState: initialState,
    });
    const informationComponent = getByRole(
      'dialog', { description: "information-dialog" });

    expect(informationComponent).toBeInTheDocument();
  });

  it('should render Information Component within App Component after licensing is provided and auth is not enabled', () => {

    // Hide the tutorial and make the overlay visible.
    initialState.tutorialHidden = true;
    initialState.overlayVisibility = true;

    initialState.authInfo.authEnabled = false;

    //Rendering the App component with the above changes to the initial
    // state should render the Information Component.
    const { getByRole } = render(<App />, {
      initialState: initialState,
    });

    const informationComponent = getByRole(
      'dialog', { description: "information-dialog" });
      
    expect(informationComponent).toBeInTheDocument();
  });

  it('should display integration terminated error', () => {

    //Hide the tutorial, make the overlay visible and set fetchFailCount to 10
    initialState.tutorialHidden = true;
    initialState.overlayVisibility = true;
    initialState.serverStatus.fetchFailCount = 10;

    //Rendering the App component with above changes to the initial state
    // will terminate the integration.
    const { container } = render(<App />, {
      initialState: initialState,
    });


    const paragraphElements = [...container.getElementsByTagName('pre')];


    expect(
      paragraphElements.some((p) =>
        p.textContent.includes('integration terminated')
      )
    ).toBe(true);
  });

  it('should display MatlabInstallError', () => {
    initialState.error = {
      type: 'MatlabInstallError',
      message: 'Matlab Installation error. Exited with status code -9',
    };
    initialState.serverStatus.licensingInfo = {};
    initialState.overlayVisibility = true;

    const { container } = render(<App />, {
      initialState: initialState,
    });

    const paragraphElements = [...container.getElementsByTagName('pre')];

    expect(
      paragraphElements.some((p) =>
        p.textContent.includes(initialState.error.message)
      )
    ).toBe(true);
  });

  it('should display Confirmation component ', () => {

    //Hide the tutorial and make the overlay visible
    initialState.tutorialHidden = true;
    initialState.overlayVisibility = true;

    const { getByTestId, container } = render(<App />, {
      initialState: initialState,
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

    //Hide the tutorial and make the overlay visible
    initialState.tutorialHidden = true;
    initialState.overlayVisibility = true;

    const { getByTestId, container, getByRole } = render(<App />, {
      initialState: initialState,
    });


    // Grab the help button and click it.
    const helpBtn = getByTestId('helpBtn');
    fireEvent.click(helpBtn);

    const helpElement = container.querySelector('#confirmation-dialog-title');

    expect(helpElement.textContent).toMatch('Help');
  });

  it('should set the window location from state', () => {
    const url = 'http://localhost.com:5555/matlab/index.html'  
    
    // define new complete url for document.URL for baseUrl variable to evaluate correctly
    // As the tests are run in a NodeJS environment where as the correct values for document.URL and window.location.href
    // are set by the browser, set the appropriate values for document.URL, window.location.href and window.location.origin
    // for the component to render without errors
    delete document.URL;
    document = {URL: url}

    // Delete and redefine 'origin' and 'href' properties as they are read-only. 
    delete window.location;
    window.location = {      
      origin: "/",
      href : "http://127.0.0.1/"
    }

    initialState.loadUrl =  url;
    render(<App />, { initialState: initialState });  
    // Check if href has been set to loadUrl by the useEffect  
    expect(window.location.href).toBe(url);
  });
});
