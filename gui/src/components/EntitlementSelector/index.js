// Copyright (c) 2020-2023 The MathWorks, Inc.

import { useState } from "react";
import { useDispatch } from "react-redux";
import { fetchUpdateLicensing } from "../../actionCreators";

function EntitlementSelector({ options }) {
  const dispatch = useDispatch();
  const [selectedEntitlement, setSelected] = useState(options[0].value);

  function updateEntitlement(event) {
    event.preventDefault();
    dispatch(
      fetchUpdateLicensing({
        type: "mhlm",
        entitlement_id: selectedEntitlement,
      })
    );
  }

  return (
    <div
      className="modal show"
      id="entitlement-selection"
      tabIndex="-1"
      role="dialog"
      aria-labelledby="confirmation-dialog-title"
    >
      <div className="modal-dialog modal-dialog-centered" role="document">
        <div className="modal-content">
          <div className="modal-header">
            <h4 className="modal-title" id="confirmation-dialog-title">
              Your MathWorks account has multiple licenses. Select a license.
            </h4>
          </div>
          <div className="modal-body">
            <select
              value={selectedEntitlement}
              onChange={(e) => setSelected(e.target.value)}
            >
              {options.map((entitlement) => (
                <option value={entitlement.value} key={entitlement.label}>
                  {entitlement.label}
                </option>
              ))}
            </select>
          </div>
          <div className="modal-footer">
            <button
              type="button"
              data-testid="submitButton"
              onClick={updateEntitlement}
            >
              Submit
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default EntitlementSelector;
