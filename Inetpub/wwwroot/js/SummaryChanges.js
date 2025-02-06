/**
 * Client-side scripting for the Summary Changes report.
 */

// Don't show the date fields if the user requests the complete history report version.
document.addEventListener("DOMContentLoaded", () => {
  const block = document.getElementById("date-range");
  document.querySelectorAll("input[name='scope']").forEach(button => {
    const display = button.value == "all" ? "none" : "block";
    button.addEventListener("click", () => block.style.display = display);
  });
});
// function check_scope(scope) {
//   .style.display = scope === "all" ? "none" : "block";
// }
