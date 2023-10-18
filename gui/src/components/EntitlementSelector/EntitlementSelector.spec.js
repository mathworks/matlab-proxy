// Copyright 2020-2023 The MathWorks, Inc.

import React from "react";
import EntitlementSelector from "./index";
import App from "../App";
import { render, fireEvent } from "../../test/utils/react-test";
import userEvent from "@testing-library/user-event";
import { filterAndFormatEntitlements, defaultLicenseUnavailableMsg } from "./index";

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
    { id: "entitlement1", label: "label1", license_number: "license1" },
    { id: "entitlement2", label: "label2", license_number: "license2" },
    { id: "entitlement3", label: "label3", license_number: "license3" },
    { id: "entitlement4", label: "label4", license_number: null },
    { id: "entitlement5", label: "label5", license_number: "" },
    { id: "entitlement6", label: null, license_number: "license6" },
    { id: "entitlement7", label: "", license_number: "license7" },
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
    expect(comboBox.length).toBeGreaterThanOrEqual(3);
    expect(comboBox).toHaveValue("entitlement1");
    expect(getByRole("option", { name: "license1 - label1" }).selected).toBe(true);
  });

  it("should select correct value on change", async () => {
    const { user, getByRole } = setup(
      <EntitlementSelector options={options} />
    );
    let comboBox = getByRole("combobox");
    await user.selectOptions(comboBox, "entitlement2");
    expect(comboBox).toHaveValue("entitlement2");
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

  it("should filter and format entitlements correctly", async () => {
    const formattedEntitlements = filterAndFormatEntitlements(options);

    expect(formattedEntitlements).toEqual([
      { label: "license1 - label1", value: "entitlement1" },
      { label: "license2 - label2", value: "entitlement2" },
      { label: "license3 - label3", value: "entitlement3" },
      { label: `license6 - ${defaultLicenseUnavailableMsg}`, value: "entitlement6" },
      { label: `license7 - ${defaultLicenseUnavailableMsg}`, value: "entitlement7" },
    ]);

  });

});
