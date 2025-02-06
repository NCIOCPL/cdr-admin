/**
 * Client-side scripting for the Media Language Compare report.
 */

// Establish initial block visibility settings and install some event listeners.
document.addEventListener("DOMContentLoaded",  () => {

  // Show the block used by the current selection method.
  function check_selection_method(method) {
    ["id", "search", "title"].forEach(name => {
      const display = name === method ? "block" : "none";
      document.querySelectorAll(`.by-${name}-block`).forEach(e => e.style.display = display);
    });
  }

  // Install the event handler for the selection method buttons.
  document.querySelectorAll("input[name='selection_method']").forEach(button => {
    button.addEventListener("click", () => check_selection_method(button.value));
  });

  // Keep track of the "select all" option states.
  const previousAllSelected = {diagnosis: false, category: false};

  // Make sure the selection options don't contradict each other.
  function check_all(which) {
    const selector = `#${which} option:checked:not([value='all'])`;
    const all = document.querySelector(`#${which} option[value='all']`);
    const ind = document.querySelectorAll(`#${which} option:checked:not([value='all'])`);
    if (all.selected !== previousAllSelected[which]) {
      if (all.selected) {
        ind.forEach(option => option.selected = false);
      } else if (ind.length < 1) {
        all.selected = true;
      }
    } else {
      all.selected = ind.length < 1;
    }
    previousAllSelected[which] = all.selected;
  }

  // Install change event listeners for the multi-selection fields.
  ["diagnosis", "category"].forEach(id => {
    document.getElementById(id).addEventListener("change", () => check_all(id));
  });

  // Show the block which matches the initial selection method.
  const method = document.querySelector("input[name='selection_method']:checked").value ?? '';
  check_selection_method(method);
});
