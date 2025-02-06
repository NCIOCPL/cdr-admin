/**
 * Client-side scripting fot the Board Roster report.
 */

// Adjust block visibility to match report type.
document.addEventListener("DOMContentLoaded", () => {
  function check_type(choice) {
    if (choice == 'full') {
      document.getElementById("full-options-box").style.display = "block";
      document.querySelectorAll(".summary-fieldset").forEach(fs => fs.style.display = "none");
    } else {
      document.getElementById("full-options-box").style.display = "none";
      document.querySelectorAll(".summary-fieldset").forEach(fs => fs.style.display = "block");
    }
  }
  document.querySelectorAll("input[name='type']").forEach(button => {
    button.addEventListener("click", () => check_type(button.value));
  });
  const choice = document.querySelector("input[name='type']:checked").value;
  check_type(choice);
});
