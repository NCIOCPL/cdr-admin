/**
 * Client-side scription for the board meeting dates report.
 */

// Ensure that the board checkboxes are logically consistent.
document.addEventListener("DOMContentLoaded", () => {
  function check_board(val) {
    const all = document.getElementById("board-all");
    const checked = document.querySelectorAll("input[name='board']:checked");
    if (val === "all") {
      checked.forEach(checkbox => checkbox.checked = false);
      all.checked = true;
    } else {
      all.checked = checked.length < 1;
    }
  }
  document.querySelectorAll("input[name='board']").forEach(checkbox => {
    checkbox.addEventListener("click", () => check_board(checkbox.value));
  })
});
