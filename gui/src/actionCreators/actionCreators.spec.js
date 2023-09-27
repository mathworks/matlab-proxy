// Copyright (c) 2020-2022 The MathWorks, Inc.

import configureMockStore from 'redux-mock-store';
import thunk from 'redux-thunk';
import fetchMock from 'fetch-mock';
import * as actions from '../actions';
import * as actionCreators from './index';

const middlewares = [thunk];
const mockStore = configureMockStore(middlewares);



describe.each([
  [actionCreators.setTutorialHidden, [true], { type: actions.SET_TUTORIAL_HIDDEN, hidden: true }],
  [actionCreators.setTutorialHidden, [false], { type: actions.SET_TUTORIAL_HIDDEN, hidden: false }],
  [actionCreators.setOverlayVisibility, [true], { type: actions.SET_OVERLAY_VISIBILITY, visibility: true }],
  [actionCreators.setOverlayVisibility, [false], { type: actions.SET_OVERLAY_VISIBILITY, visibility: false }],
  [actionCreators.setTriggerPosition, [12, 12], { type: actions.SET_TRIGGER_POSITION, x: 12, y: 12 }],
  [actionCreators.setTriggerPosition, [52, 112], { type: actions.SET_TRIGGER_POSITION, x: 52, y: 112 }],
  [actionCreators.setAuthStatus, [true], { type: actions.SET_AUTH_STATUS, authInfo: true }],
  [actionCreators.setAuthStatus, [false], { type: actions.SET_AUTH_STATUS, authInfo: false }],
  [actionCreators.setAuthToken, ['string'], { type: actions.SET_AUTH_TOKEN, authInfo: 'string' }],
  [actionCreators.setAuthToken, [null], { type: actions.SET_AUTH_TOKEN, authInfo: null }]
])('Test Set actionCreators', (method, input, expectedAction) => {
  test(`check if an action of type  ${expectedAction.type} is returned when method actionCreator.${method.name}() is called`, () => {
    expect(method(...input)).toEqual(expectedAction);
  });
});


describe.each([
  [actionCreators.requestServerStatus, { type: actions.REQUEST_SERVER_STATUS }],
  [actionCreators.requestSetLicensing, { type: actions.REQUEST_SET_LICENSING }],
  [actionCreators.requestStopMatlab, { type: actions.REQUEST_STOP_MATLAB, status: 'stopping' }],
  [actionCreators.requestStartMatlab, { type: actions.REQUEST_START_MATLAB, status: 'starting' }],
  [actionCreators.requestTerminateIntegration, { type: actions.REQUEST_TERMINATE_INTEGRATION }],
])('Test Request actionCreators', (method, expectedAction) => {

  test(`check if an action of type  ${expectedAction.type} is returned when method actionCreator.${method.name}() is called`, () => {
    expect(method()).toEqual(expectedAction);
  });
});


describe.each([
  [actionCreators.receiveSetLicensing, { type: 'MHLM' }, { type: actions.RECEIVE_SET_LICENSING, status: { type: 'MHLM' } }],
  [actionCreators.receiveStopMatlab, { matlabStatus: 'down' }, { type: actions.RECEIVE_STOP_MATLAB, status: { matlabStatus: 'down' } }],
  [actionCreators.receiveStartMatlab, { matlabStatus: 'up' }, { type: actions.RECEIVE_START_MATLAB, status: { matlabStatus: 'up' } }],
  [actionCreators.receiveError, { message: 'ERROR: License Manager Error -9', logs: null }, { type: actions.RECEIVE_ERROR, error: { message: 'ERROR: License Manager Error -9', logs: null } }],
  [actionCreators.receiveTerminateIntegration, { licensing: {} }, { type: actions.RECEIVE_TERMINATE_INTEGRATION, status: { licensing: {} }, loadUrl: '../' }],
])('Test Receive actionCreators', (method, input, expectedAction) => {

  test(`check if an action of type  ${expectedAction.type} is returned when method actionCreator.${method.name}() is called`, () => {
    expect(method(input)).toEqual(expectedAction);
  });
});



describe('Test Sync actionCreators', () => {
  it('should dispatch action of type RECEIVE_SERVER_STATUS ', () => {
    const store = mockStore({
      overlayVisibility: false,
      error: null,
      serverStatus: {
        matlabStatus: 'starting',
        matlabVersion: 'R2020b',
        isFetching: true,
        hasFetched: false,
        fetchFailCount: 0,
        licensingInfo: {
          type: 'NLM',
          connectionString: 'abc@nlm',
        }
      },
      authInfo: {
        authEnabled: false,
        authStatus: false,
        authToken: null,
      }
    });

    const status = {
      matlab: {
        status: 'up',
      },
      licensing: {
        type: 'MHLM',
      },
    };
    store.dispatch(actionCreators.receiveServerStatus(status));

    const expectedActionTypes = [actions.RECEIVE_SERVER_STATUS];

    const receivedActions = store.getActions();

    expect(receivedActions.map((element) => element.type)).toEqual(expectedActionTypes);
  });
});

describe('Test fetchWithTimeout method', () => {
  let store;
  beforeEach(() => {
    store = mockStore({
      error: null,
      serverStatus: {
        matlabVersion: 'R2020b',
        licensingInfo: {
          type: 'NLM',
          connectionString: 'abc@nlm',
        },
        isFetching: false,
        isSubmitting: false,
        hasFetched: false,
        fetchFailCount: 0,
      },
    });
  });

  afterEach(() => {
    fetchMock.restore();
  });

  it('should fetch requested data without raising an exception or dispatching any action', async () => {
    fetchMock.getOnce('/get_status', {
      body: {
        matlab: {
          status: 'down',
        },
        licensing: {},
      },
      headers: { 'content-type': 'application/json' },
    });

    const response = await actionCreators.fetchWithTimeout(store.dispatch, '/get_status', {}, 10000);
    const body = await response.json()

    expect(body).not.toBeNull();
  });

  it('dispatches RECIEVE_ERROR when no response is received', async () => {

    const expectedActions = [
      actions.RECEIVE_ERROR,
    ];

    try {
      const response = await actionCreators.fetchWithTimeout(store.dispatch, '/get_status', {}, 100);
    } catch (error) {
      expect(error).toBeInstanceOf(TypeError)
      const received = store.getActions();
      expect(received.map((a) => a.type)).toEqual(expectedActions);
    }
  });


  it('should send a delayed response after timeout expires, thereby triggering abort() method of AbortController', async () => {

    const timeout = 10
    const delay = (response, after = 500) => () => new Promise(resolve => setTimeout(resolve, after)).then(() => response);

    // Send a delayed response, well after the timeout for the request has expired.
    // This should trigger the abort() method of the AbortController()
    fetchMock.mock('/get_status', delay(200, timeout + 100));

    const abortSpy = jest.spyOn(AbortController.prototype, 'abort');
    const expectedActions = [
      actions.RECEIVE_ERROR,
    ];

    await actionCreators.fetchWithTimeout(store.dispatch, '/get_status', {}, timeout);

    expect(abortSpy).toBeCalledTimes(1);
    const received = store.getActions();
    expect(received.map((a) => a.type)).toEqual(expectedActions);
  });

});

describe('Test Async actionCreators', () => {
  let store;
  beforeEach(() => {
    store = mockStore({
      error: null,
      serverStatus: {
        matlabVersion: 'R2020b',
        licensingInfo: {
          type: 'NLM',
          connectionString: 'abc@nlm',
        },
        isFetching: false,
        isSubmitting: false,
        hasFetched: false,
        fetchFailCount: 0,
      },
      authInfo: {
        authEnabled: false,
        authStatus: false,
        authToken: null,
      },
    });
  });

  afterEach(() => {
    fetchMock.restore();
  });

  it('dispatches SET_AUTH_STATUS when fetching auth info and not authorized', () => {
    let token = 'token'
    fetchMock.once('/authenticate', {
      body: {
        authStatus: false,
        error: {
          message: "Token invalid. Please enter a valid token to authenticate",
          type: "invalidToken",
          logs: null,
        }
      }
    });
    const expectedActions = [actions.SET_AUTH_STATUS];

    return store.dispatch(actionCreators.updateAuthStatus(token)).then(() => {
      const received = store.getActions();
      expect(received.map((a) => a.type)).toEqual(expectedActions);
    });
  });

  it('dispatches SET_AUTH_STATUS, when fetching auth info and authorized', () => {
    let token = 'token'
    fetchMock.once('/authenticate', {
      body: {
        authStatus: true,
        error: null
      }
    });
    const expectedActions = [actions.SET_AUTH_STATUS];

    return store.dispatch(actionCreators.updateAuthStatus(token)).then(() => {
      const received = store.getActions();
      expect(received.map((a) => a.type)).toEqual(expectedActions);
    });
  });



  it('dispatches REQUEST_SERVER_STATUS, RECEIVE_SERVER_STATUS when fetching status', () => {
    fetchMock.getOnce('/get_status', {
      body: {
        matlab: {
          status: 'down',
        },
        licensing: {},
      },
      headers: { 'content-type': 'application/json' },
    });

    const expectedActions = [
      actions.REQUEST_SERVER_STATUS,
      actions.RECEIVE_SERVER_STATUS,
    ];

    return store.dispatch(actionCreators.fetchServerStatus()).then(() => {
      const received = store.getActions();
      expect(received.map((a) => a.type)).toEqual(expectedActions);
    });
  });

  it('dispatches REQUEST_ENV_CONFIG, RECEIVE_ENV_CONFIG when fetching environment configuration', () => {
    fetchMock.getOnce('/get_env_config', {
      body: {
        "doc_url": "https://github.com/mathworks/matlab-proxy/",
        "extension_name": "default_configuration_matlab_desktop_proxy",
        "extension_name_short_description": "MATLAB Web Desktop",
      },
      headers: { 'content-type': 'application/json' },
    });

    const expectedActions = [
      actions.REQUEST_ENV_CONFIG,
      actions.RECEIVE_ENV_CONFIG,
    ];

    return store.dispatch(actionCreators.fetchEnvConfig()).then(() => {
      const received = store.getActions();
      expect(received.map((a) => a.type)).toEqual(expectedActions);
    });
  });

  it('should dispatch REQUEST_SET_LICENSING and RECEIVE_SET_LICENSING when we set license', () => {
    fetchMock.putOnce('/set_licensing_info', {
      body: {
        matlab: {
          status: 'up',
        },
        licensing: {
          type: 'NLM',
          connectionString: 'abc@nlm',
        },
      },
      headers: { 'content-type': 'application/json' },
    });

    const expectedActionTypes = [
      actions.REQUEST_SET_LICENSING,
      actions.RECEIVE_SET_LICENSING,
    ];
    const info = {
      type: 'NLM',
      connectionString: 'abc@nlm',
    };
    return store.dispatch(actionCreators.fetchSetLicensing(info)).then(() => {
      const receivedActions = store.getActions();
      expect(receivedActions.map((action) => action.type)).toEqual(
        expectedActionTypes
      );
    });
  });

  it('should dispatch REQUEST_SET_LICENSING and RECEIVE_SET_LICENSING when we unset license', () => {
    fetchMock.deleteOnce('./set_licensing_info', {
      body: {
        matlab: {
          status: 'down',
        },
        licensing: null,
      },
      headers: { 'content-type': 'application/json' },
    });

    const expectedActionTypes = [
      actions.REQUEST_SET_LICENSING,
      actions.RECEIVE_SET_LICENSING,
    ];

    return store.dispatch(actionCreators.fetchUnsetLicensing()).then(() => {
      const receivedActions = store.getActions();
      expect(receivedActions.map((action) => action.type)).toEqual(
        expectedActionTypes
      );
    });
  });

  it('should dispatch REQUEST_TERMINATE_INTEGRATION and RECEIVE_TERMINATE_INTEGRATION when we terminate the integration', () => {
    fetchMock.deleteOnce('./terminate_integration', {
      body: {
        matlab: {
          status: 'down',
        },
        licensing: null,
      },
      headers: { 'content-type': 'application/json' },
    });

    const expectedActionTypes = [
      actions.REQUEST_TERMINATE_INTEGRATION,
      actions.RECEIVE_TERMINATE_INTEGRATION,
    ];

    return store
      .dispatch(actionCreators.fetchTerminateIntegration())
      .then(() => {
        const receivedActions = store.getActions();
        expect(receivedActions.map((action) => action.type)).toEqual(
          expectedActionTypes
        );
      });
  });

  it('should dispatch REQUEST_STOP_MATLAB AND RECEIVE_STOP_MATLAB when we stop matlab', () => {
    fetchMock.putOnce('./start_matlab', {
      body: {
        matlab: {
          status: 'down',
        },
        licensing: null,
      },
      headers: { 'content-type': 'application/json' },
    });

    const expectedActionTypes = [
      actions.REQUEST_START_MATLAB,
      actions.RECEIVE_START_MATLAB,
    ];

    return store.dispatch(actionCreators.fetchStartMatlab()).then(() => {
      const receivedActions = store.getActions();
      expect(receivedActions.map((action) => action.type)).toEqual(
        expectedActionTypes
      );
    });
  });
});
