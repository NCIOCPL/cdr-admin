/**
 * Client-side support for the Edit Link Type form.
 */

// Make sure each repeatable block has a unique ID.
let next_counter = 0;

// Map of strings used for confirmation block.
const descs = { "e": "linking element", "r": "custom rule" };

// Add a repeatable block.
function add_block(n, t) {
  const block = templates[t].replace(/@@COUNTER@@/g, next_counter);
  const element = document.getElementById(`block-${n}`);
  element.insertAdjacentHTML("afterend", block);
  next_counter++;
}

// Remove a repeatable block.
function del_block(n, t) {
  if (confirm(`Do you really want to delete this ${descs[t]} block?`)) {
    if (document.querySelectorAll(`.${t}-block`).length < 2) {
      add_block(n, t);
    }
    const element = document.getElementById("block-" + n);
    element.remove();
  }
}

// Set the cancel tooltip, delete callback, and next block counter.
document.addEventListener("DOMContentLoaded", () => {
  const title = "Return to menu of link types";
  const cancel_button = document.getElementById("submit-button-cancel");
  cancel_button.setAttribute("title", title);
  const delete_button = document.getElementById("submit-button-delete");
  if (delete_button) {
    delete_button.addEventListener("click", (e) => {
      if (!confirm("Are you sure?")) {
        e.preventDefault();
      }
    });
  }
  next_counter = document.querySelectorAll(".numbered-block").length + 1;
});
