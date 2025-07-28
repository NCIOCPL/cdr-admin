/**
 * Client-side scripting for creating board member correspondence mailers.
 */

// Make it possible to detect when the board selection has changed.
var current_board = 0;

// When the board changes, re-populate the fields for members and letters.
function check_board() {

  // Has the currently selected board changed?
  const selected_board = document.querySelector("#boards input:checked");
  if (selected_board) {
    const board_id = selected_board.value;
    if (board_id != current_board) {

      // Renew the radio button fields for the available letters.
      current_board = board_id;
      const letters_fieldset = document.getElementById("letters");
      const old_letter_divs = letters_fieldset.querySelectorAll("div");
      old_letter_divs.forEach(div => div.remove());
      const board = boards[board_id];
      const type = board.type;
      for (const [name, key] of letters[type]) {
        const button = document.createElement("input");
        button.type = "radio";
        button.name = "letter";
        button.className = "usa-radio__input";
        button.value = key;
        button.id = key;
        button.addEventListener("click", check_submit_button);
        const label = document.createElement("label");
        label.htmlFor = key;
        label.className = "usa-radio__label";
        label.textContent = name;
        const div = document.createElement("div");
        div.className = "usa-radio";
        div.appendChild(button);
        div.appendChild(label);
        letters_fieldset.appendChild(div);
      }

      // Do the same for the list of board members.
      const member_fieldset = document.getElementById("members");
      const old_member_divs = member_fieldset.querySelectorAll("div");
      old_member_divs.forEach(div => div.remove());
      const all_members = [["all", "All board members"]];
      const members = all_members.concat(boards[board_id].members);
      for (const [id, name] of members) {
        const key = `member-${id}`;
        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.name = "member";
        checkbox.className = "usa-checkbox__input";
        checkbox.value = id;
        checkbox.id = key;
        checkbox.addEventListener("click", function() { check_member(this); });
        const label = document.createElement("label");
        label.htmlFor = key;
        label.className = "usa-checkbox__label";
        label.textContent = name;
        const div = document.createElement("div");
        div.className = "usa-checkbox";
        div.appendChild(checkbox);
        div.appendChild(label);
        member_fieldset.appendChild(div);
      }
    }
  }
  check_submit_button();
}

// Add some additional logic to the "All board members" checkbox.
function check_member(checkbox) {
  if (checkbox.id === "member-all") {
    const members = document.querySelectorAll("#members input");
    const checked = !!checkbox.checked;
    members.forEach(member => member.checked = checked);
  } else if (!checkbox.checked) {
    document.getElementById("member-all").checked = false;
  }
  check_submit_button();
}

// Show the submit button only if we have a letter and at least one recipient.
function check_submit_button() {
  const button = document.getElementById("submit-button-submit");
  const letter = document.querySelector("#letters input:checked");
  const member = document.querySelector("#members input:checked");
  button.style.display = letter && member ? "block" : "none";
}

// Plug in the handler for changes to the board selection, and run it now.
document.addEventListener("DOMContentLoaded", () => {
  const boards = document.querySelectorAll("#boards input");
  boards.forEach(board => board.addEventListener("click", check_board));
  check_board();
  check_submit_button();
});
