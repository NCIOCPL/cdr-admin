/**
 * Client-side scripting for the summary mailer request landing page.
 */

// Show/hide the extra instruction text.
function toggle_help() {
  const fieldset = document.getElementById("instructions");
  const extra = fieldset.querySelectorAll(".more");
  const legend = fieldset.querySelector("legend");
  if (legend.textContent === "Instructions [More]") {
    legend.textContent = "Instructions [Less]";
    extra.forEach(paragraph => paragraph.style.display = "block");
    fieldset.title = "Click [Less] to collapse instructions box.";
  } else {
    legend.textContent = "Instructions [More]";
    fieldset.title = "Click [More] to see more complete instructions.";
    extra.forEach(paragraph => paragraph.style.display = "none");
  }
}

// Show the picklist matching the chosen selection method.
function check_selection_method(method) {
  switch (method) {
  case "all":
    document.getElementById("members-block").style.display = "none";
    document.getElementById("summaries-block").style.display = "none";
    break;
  case "summary":
    document.getElementById("members-block").style.display = "none";
    document.getElementById("summaries-block").style.display = "block";
    break;
  case "member":
    document.getElementById("members-block").style.display = "block";
    document.getElementById("summaries-block").style.display = "none";
    break;
  }
}

// Keep track of the "select all" option states.
const previousAllSelected = {members: false, summaries: false};

// Make sure the selection options don't contradict each other.
function check_all(which) {
  const all = document.querySelector(`#${which} .all`);
  const ind = document.querySelectorAll(`#${which} .individual:checked`);
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
const memchg = () => check_all("members");
const sumchg = () => check_all("summaries");

// Repopulate the picklists when a different board is selected.
function board_change() {

  // Find out which board has been picked.
  const board = document.getElementById("board");
  const board_id = board.options[board.selectedIndex].value;

  // If no board has been picked, just hide the lower bloks.
  if (!board_id) {
      document.getElementById("method-block").style.display = "none";
      document.getElementById("members-block").style.display = "none";
      document.getElementById("summaries-block").style.display = "none";
      return;
  }

  // Show the field for choosing how to select the letters to be sent.
  document.getElementById("method-block").style.display = "block";

  // Repopulate both of the picklists.
  const board_data = boards[board_id];
  const members = document.getElementById("members");
  const summaries = document.getElementById("summaries");
    members.innerHTML = "";
  summaries.innerHTML = "";
  const labels = ["All members of Board", "All Summaries for Board"];
  const selects = [members, summaries];
  labels.forEach((label, i) => {
    const opt = `<option value="all" class="all" selected>${label}</option>`;
    selects[i].insertAdjacentHTML("beforeend", opt);
  });
  ["members", "summaries"].forEach((name, i) => {
    board_data[name].forEach(option => {
      const attr = `class="individual" value="${option.value}"`;
      const html = `<option ${attr}>${option.label}</option>`;
      selects[i].insertAdjacentHTML("beforeend", html);
    })
  });

  // Show the right picklist.
  const selector = "input[name='selection_method']:checked";
  const method = document.querySelector(selector).value;
  check_selection_method(method);

  // Initialize the "select all" option states.
  previousAllSelected.members = true;
  previousAllSelected.summaries = true;
}

// Start out with the picklist and selection method fields hidden.
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("input[name='selection_method']").forEach(button => {
    button.addEventListener("click", () => check_selection_method(button.value));
  });
  board_change();
});
