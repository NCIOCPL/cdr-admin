/**
 * Client-side scripting for alternate board roster report.
 */

// Manage block visibility.
document.addEventListener("DOMContentLoaded", () => {

  // Create the handler.
  function check_format() {
    const selector = "#report-formats input:checked";
    const format = document.querySelector(selector).value;
    const display = format === "full" ? "none" : "block"
    document.getElementById("columns").style.display = display;
  }

  // Install it.
  const buttons = document.querySelectorAll("#report-formats input");
  buttons.forEach(button => button.addEventListener("click", check_format));

  // Invoke it.
  check_format();
});
