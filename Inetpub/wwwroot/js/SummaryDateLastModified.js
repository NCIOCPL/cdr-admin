/**
 * Custom client-side scripting for the Summary Date Last Modified report.
 */

// Custom behavior for the summary type checkboxes.
const checkSummaryTypeCheckboxes = (prefix, value) => {
  if (value === "all") {
    document.querySelectorAll(`.${prefix}-individual`).forEach(cb => cb.checked = false);
  } else {
    document.getElementById(`${prefix}-all`).checked = false;
  }
};
const check_est = value => checkSummaryTypeCheckboxes("est", value);
const check_sst = value => checkSummaryTypeCheckboxes("sst", value);

// Ensure that only one set of start/end dates has values.
document.addEventListener("DOMContentLoaded", () => {
  [["u", "s"], ["s", "u"]].forEach(([current, other]) => {
    ["start", "end"].forEach(suffix => {
      document.getElementById(`${current}-${suffix}`).addEventListener("change", () => {
        ["start", "end"].forEach(sfx => document.getElementById(`${other}-${sfx}`).value = "");
      });
    });
  });
});
