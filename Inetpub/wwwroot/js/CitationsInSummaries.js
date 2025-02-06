/**
 * Client-side scripting for the Citations In Summaries report.
 */

// Adjust block visibility to for the quick-and-dirty version of the report.
document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("options-quick").addEventListener("click", () => {
    if (document.getElementById("options-quick").checked) {
      document.getElementById("limit-block").style.display = "block";
      document.getElementById("email-block").style.display = "none";
    } else {
      document.getElementById("limit-block").style.display = "none";
      document.getElementById("email-block").style.display = "block";
    }
  });
});
