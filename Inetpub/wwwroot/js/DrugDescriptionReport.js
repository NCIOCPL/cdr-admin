/**
 * Client-side scripting for the Drug Description report.
 */

// Adjust component visibility controlled by the selection method chosen.
function check_method(method) {
  ["name", "date", "type", "fda"].forEach(block => {
    const block_element = document.getElementById(`${block}-block`);
    if (block === method) {
      block_element.style.display = "block";
    } else {
      block_element.style.display = "none";
    }
  });
}

// Install drug selection event listeners and set up initial block visibility.
document.addEventListener("DOMContentLoaded", () => {
  const catchalls = ["drugs", "single-agent-drugs", "drug-combinations"];
  const drug_options = document.querySelectorAll("#drugs option");
  drug_options.forEach(option => {
    option.addEventListener("click", (event) => {
      const value = event.target.value;
      switch (value) {
        case "all-drugs":
        case "all-single-agent-drugs":
        case "all-drug-combinations":
          drug_options.forEach(opt => opt.selected = false);
          const selector = `#drugs option[value="${value}"]`;
          document.querySelector(selector).selected = true;
          break;
        default:
          catchalls.forEach(value => {
            const selector = `#drugs option[value="all-${value}"]`;
            document.querySelector(selector).selected = false;
          });
          break;
      }
    });
  });
  document.querySelectorAll("input[name='method']").forEach(button => {
    button.addEventListener("click", () => check_method(button.value));
  });
  const method = document.querySelector("input[name='method']:checked");
  if (method) {
    check_method(method.value);
  }
});
