/**
 * Client-side scripting for the Drug Indications report.
 */

// Create the event listeners and set initial block visibility.
document.addEventListener("DOMContentLoaded", () => {

  // Control visibility of hideable blocks.
  function check_type(value) {
    const display = value === "plain" ? "none" : "block";
    const hideable = document.querySelectorAll("fieldset.hideable");
    hideable.forEach(element => element.style.display = display);
  }

  // Assign the event handlers.
  const buttons = document.querySelectorAll("input[name='type']");
  buttons.forEach(b => b.addEventListener("click", () => check_type(b.value)));

  // Start out with the right blocks visible.
  const type = document.querySelector("input[name='type']:checked");
  check_type(type.value ?? "plain");
});
