/**
 * Client-side scripting for the Summary Comprehensive Review Dates report.
 */

// Make the board checkboxes behave reasonably.
document.addEventListener("DOMContentLoaded", () => {
  function check_board(val) {
    const all = document.getElementById("board-all");
    const ind = document.querySelectorAll(".some:checked");
    if (val === "all") {
      ind.forEach(checkbox => checkbox.checked = false);
    } else {
      all.checked = ind.length < 1;
    }
  }
  document.querySelectorAll("input[name='board']").forEach(checkbox => {
    checkbox.addEventListener("click", () => check_board(checkbox.value));
  });
});
