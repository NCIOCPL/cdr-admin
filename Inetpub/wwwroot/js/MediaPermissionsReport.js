/**
 * Client-side support for the report on media usage rights.
 */

// Adjust the board selection checkboxes as appropriate. This handler gets
// attached to the checkboxes by cdrcgi.Controller.add_board_fieldset().
function check_board(value) {
  const all = document.getElementById("board-all");
  const boards = document.querySelectorAll("#board-set .ind");
  if (value === "all") {
    if (all.checked) {
      boards.forEach(board => board.checked = false);
    } else {
      all.checked = true;
    }
  } else if (Array.from(boards).filter(board => board.checked).length > 0) {
    all.checked = false;
  } else {
    all.checked = true;
  }
}

// Install the other event listening handlers and invoke the selection method handler.
document.addEventListener("DOMContentLoaded", () => {

  // Manage the visibility of blocks controlled by the selection method.
  function check_selection_method() {

    // Make sure a method is selected.
    const global = document.getElementById("selection_method-global");
    const specific = document.getElementById("selection_method-specific");
    if (!global.checked && !specific.checked) {
      global.checked = true;
    }

    // Show the blocks appropriate for the user's selection method.
    if (global.checked) {
      document.getElementById("global-block").style.display = "block";
      document.getElementById("specific-block").style.display = "none";
      document.getElementById("doctype-block").style.display = "none";
      document.getElementById("id-block").style.display = "none";
      document.querySelectorAll(".by-board-block").forEach(block => {
        block.style.display = "none";
      });
    }
    else {
      document.getElementById("global-block").style.display = "none";
      document.getElementById("specific-block").style.display = "block";
      check_specific();
    }
  }
  document.querySelectorAll("input[name='selection_method']").forEach(button => {
    button.addEventListener("click", check_selection_method);
  });

  // Manage visibility of blocks controlled by the "specific" selection method.
  function check_specific() {

    // Make sure one of the specific selection methods is chosen.
    const docid = document.getElementById("specific-docid");
    const doctype = document.getElementById("specific-doctype");
    const summary = document.getElementById("specific-summary");
    if (!docid.checked && !doctype.checked && !summary.checked) {
      doctype.checked = true;
    }

    // Show the blocks used by that specific selection method.
    let idDisplay = doctypeDisplay = boardDisplay = "none";
    if (doctype.checked) {
      doctypeDisplay = "block";
    } else if (docid.checked) {
      idDisplay = "block";
    } else {
      boardDisplay = "block";
    }
    document.getElementById("doctype-block").style.display = doctypeDisplay;
    document.getElementById("id-block").style.display = idDisplay;
    document.querySelectorAll(".by-board-block").forEach(block => {
      block.style.display = boardDisplay;
    });
  }
  document.querySelectorAll("input[name='specific']").forEach(button => {
    button.addEventListener("click", check_specific);
  });


  // Adjust the options for the "global" version of the report as appropriate.
  function check_global(value) {

    // Find the radio buttons.
    const english = document.getElementById("global-en");
    const spanish = document.getElementById("global-es");
    const denied = document.getElementById("global-denied");

    // Adjust the buttons based on which one was just clicked.
    switch (value) {
      case "denied":
        english.checked = spanish.checked = false;
        break;
      default:
        denied.checked = false;
        break;
    }

    // If the other two boxes are unchecked, make sure the English box is checked.
    if (!spanish.checked && !denied.checked) {
      english.checked = true;
    }
  }
  document.querySelectorAll("input[name='global']").forEach(button => {
    button.addEventListener("click", () => check_global(button.value));
  });

  // Start out with the appropriate blocks visibile.
  check_selection_method();
});