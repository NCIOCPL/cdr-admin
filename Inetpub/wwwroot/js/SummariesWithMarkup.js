/**
 * Client-side scripting for the Summaries With Markup report.
 */

// Make the board checkboxes behave rationally.
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
