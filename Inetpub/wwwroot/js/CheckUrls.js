/**
 * Client-side scripting for the report on external URLs with problems.
 */

// Make the All Boards check play nice with the other board checkboxes. This handler
// gets attached to the checkboxes by cdrcgi.Controller.add_board_fieldset().
function check_board(val) {
  const all_checkbox = document.getElementById("board-all");
  const ind_checkboxes = document.querySelectorAll("#board-set .ind");
  if (val === "all") {
    if (all_checkbox.checked) {
      ind_checkboxes.forEach(cb => cb.checked = false);
    } else {
      all_checkbox.checked = true;
    }
  } else {
    const any_checked = Array.from(ind_checkboxes).some(cb => cb.checked);
    all_checkbox.checked = !any_checked;
  }
}

// Add the other event handlers and set initial visibility of page components.
document.addEventListener("DOMContentLoaded", () => {

  // Adjust option visibility to match selected report flavor.
  function check_report_type(type) {
    const redirects_option = document.querySelector(".opts-redirects-wrapper");
    const show_all_option = document.querySelector(".opts-show-all-wrapper");
    if (type === "Broken URLs") {
      redirects_option.style.display = "block";
      show_all_option.style.display = "none";
    } else {
      redirects_option.style.display = "none";
      show_all_option.style.display = "block";
    }
  }
  document.querySelectorAll("input[name='report-type']").forEach(button => {
    button.addEventListener("click", () => check_report_type(button.value));
  });

  // Adjust visibility of blocks based on the selection method chosen.
  function check_method(method) {
    const by_doctype = document.querySelectorAll(".by-doctype-block");
    const by_board = document.querySelectorAll(".by-board-block");
    const by_id = document.querySelectorAll(".by-id-block");
    switch (method) {
      case "id":
        by_doctype.forEach(block => block.style.display = "none");
        by_board.forEach(block => block.style.display = "none");
        by_id.forEach(block => block.style.display = "block");
        break;
      case "doctype":
        by_doctype.forEach(block => block.style.display = "block");
        by_id.forEach(block => block.style.display = "none");
        check_doctype();
        break;
    }
  }
  document.querySelectorAll("input[name='method']").forEach(button => {
    button.addEventListener("click", () => check_method(button.value));
  });

  // Adjust the visibility of blocks based on the document type selected.
  function check_doctype() {
    const summary = document.getElementById("doctype-summary");
    const gtc = document.getElementById("doctype-glossarytermconcept");
    const board_blocks = document.querySelectorAll(".by-board-block");
    const board_set = document.getElementById("board-set");
    const display = (summary.checked || gtc.checked) ? "block" : "none";
    board_blocks.forEach(block => block.style.display = display);
    board_set.style.display = summary.checked ? "block" : "none";
  }
  document.querySelectorAll("input[name='doctype']").forEach(button => {
    button.addEventListener("click", () => check_doctype(button.value));
  });

  // Adjust visibility of blocks controlled by the "quick report" setting.
  function check_quick_option() {
    const opt_quick = document.getElementById("opt-quick");
    const throttle_block = document.getElementById("throttle-block");
    const email_block = document.getElementById("email-block");
    if (opt_quick.checked) {
      throttle_block.style.display = "block";
      email_block.style.display = "none";
    } else {
      throttle_block.style.display = "none";
      email_block.style.display = "block";
    }
  }
  document.getElementById("opt-quick").addEventListener("click", check_quick_option);

  // Start the page off with the appropriate blocks showing.
  const method_selector = "input[name='method']:checked";
  const method = document.querySelector(method_selector);
  const report_type_selector = "input[name='report-type']:checked";
  const report_type = document.querySelector(report_type_selector);
  if (method) check_method(method.value);
  check_quick_option();
  if (report_type) check_report_type(report_type.value);
});
