/**
 * Client-side scripting for the Summaries Table Of Contents report.
 */

// Add event listeners and set initial fieldset visibility.
document.addEventListener("DOMContentLoaded", () => {

  // Align fieldset visibility with chose selection method.
  function check_method(value) {
    switch (value) {
    case "id":
      document.querySelectorAll(".board-fieldset").forEach(fieldset => {
        fieldset.style.display = "none";
      });
      document.getElementById("title-fieldset").style.display = "none";
      document.getElementById("cdrid-fieldset").style.display = "block";
      break;
    case "title":
      document.querySelectorAll(".board-fieldset").forEach(fieldset => {
        fieldset.style.display = "none";
      });
      document.getElementById("title-fieldset").style.display = "block";
      document.getElementById("cdrid-fieldset").style.display = "none";
      break;
    default:
      document.querySelectorAll(".board-fieldset").forEach(fieldset => {
        fieldset.style.display = "block";
      });
      document.getElementById("title-fieldset").style.display = "none";
      document.getElementById("cdrid-fieldset").style.display = "none";
      break;
    }
  }
  document.querySelectorAll("input[name='method']").forEach(button => {
    button.addEventListener("click", () => check_method(button.value));
  });

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
  document.querySelectorAll("input[name='board']").forEach(button => {
    button.addEventListener("click", () => check_board(button.value));
  });

  // Establish initial block visibility.
  const value = document.querySelector("input[name='method']:checked").value ?? "";
  check_method(value);
});
