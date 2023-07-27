// Copyright (c) 2020-2023 The MathWorks, Inc.

import React from "react";
import EntitlementSelector from "./index";
import App from "../App";
import { render, fireEvent } from "../../test/utils/react-test";
import userEvent from "@testing-library/user-event";

describe("EntitlementSelector Component", () => {
  let initialState;

  beforeEach(() => {
    initialState = {
      triggerPosition: { x: 539, y: 0 },
      tutorialHidden: false,
      overlayVisibility: false,
      serverStatus: {
        licensingInfo: {
          type: "mhlm",
          emailAddress: "abc@mathworks.com",
          entitlements: [
            { id: "1234567", label: null, license_number: "7654321" },
            {
              id: "2345678",
              label: "MATLAB - Staff Use",
              license_number: "87654432",
            },
          ],
          entitlementId: null,
        },
        matlabStatus: "down",
        matlabVersion: "R2023a",
        isFetching: false,
        hasFetched: true,
        isSubmitting: false,
        fetchFailCount: 0,
        wsEnv: "mw",
      },
      loadUrl: null,
      error: null,
      authInfo: {
        authEnabled: false,
        authStatus: false,
        authToken: null,
      },
    };
  });

  const options = [
    { value: "license1", label: "Entitlement1" },
    { value: "license2", label: "Entitlement2" },
    { value: "license3", label: "Entitlement3" },
  ];

  function setup(jsx) {
    return {
      user: userEvent.setup(),
      ...render(jsx),
    };
  }

  it("should render correctly", () => {
    render(<EntitlementSelector options={options} />);
  });

  it("should render with default value selected and all options present", () => {
    const { getByRole } = render(<EntitlementSelector options={options} />);

    let comboBox = getByRole("combobox");
    expect(comboBox.length).toBe(3);
    expect(comboBox).toHaveValue("license1");
    expect(getByRole("option", { name: "Entitlement1" }).selected).toBe(true);
  });

  it("should select correct value on change", async () => {
    const { user, getByRole } = setup(
      <EntitlementSelector options={options} />
    );
    let comboBox = getByRole("combobox");
    await user.selectOptions(comboBox, "license2");
    expect(comboBox).toHaveValue("license2");
  });

  it("should fire onClick Event for submit button without crashing", () => {
    const { getByTestId, container, unmount } = render(<App />, {
      initialState: initialState,
    });

    // Expecting the license selector dialog since entitlementId is not set
    expect(
      container.querySelector("#entitlement-selection")
    ).toBeInTheDocument();
    const submitButton = getByTestId("submitButton");
    fireEvent.click(submitButton);

    // re-rendering (via unmount and rendering again similar to real app) so 
    // that the redux state (entitlementId) is updated for test App component
    unmount();
    render(<App />);
    expect(
      container.querySelector("#entitlement-selection")
    ).not.toBeInTheDocument();
  });
});
