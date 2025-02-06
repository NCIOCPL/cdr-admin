/**
 * Client-side scripting support for the report on comments in Summary documents.
 */

// Add event listeners and set initial block display.
document.addEventListener("DOMContentLoaded",  () => {

  // Custom behavior for the checkboxes indicating which comments to include.
  function check_types(type) {
    switch (type) {
      case "C":
        document.getElementById("types-c").checked = true;
        document.querySelectorAll(".specific-comment-types").forEach(cb => cb.checked = false);
        break;
      case "R":
        break;
      default:
        document.getElementById("types-c").checked = false;
        break;
    }
    if (document.querySelectorAll("#types-block input:checked").length < 1) {
      document.getElementById("types-e").checked = true;
      document.getElementById("types-r").checked = true;
    }
  }
  document.querySelectorAll("input[name='types']").forEach(button => {
    button.addEventListener("click", () => check_types(button.value));
  });

  // Show the block used by the current selection method.
  function check_selection_method(method) {
    ["id", "board", "title"].forEach(name => {
      const display = name === method ? "block" : "none";
      document.querySelectorAll(`.by-${name}-block`).forEach(e => e.style.display = display);
    });
  }
  document.querySelectorAll("input[name='selection_method']").forEach(button => {
    button.addEventListener("click", () => check_selection_method(button.value));
  });

  // Make sure we start with the right blocks showing.
  const method = document.querySelector("input[name='selection_method']:checked").value ?? '';
  check_selection_method(method);
});
