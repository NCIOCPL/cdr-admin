/**
 * Client-side scripting for the Summaries Lists report.
 */

// Add the event handlers.
document.addEventListener("DOMContentLoaded", () => {

  // Adjust the visibility of the summaries sets fieldset.
  document.querySelectorAll("input[name='included']").forEach(button => {
    const display = button.value === "p" ? "none" : "block";
    const box = document.getElementById("select-summary-sets-box");
    button.addEventListener("click", () => box.style.display = display);
  });

  // Make the board checkboxes behave reasonably.
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
