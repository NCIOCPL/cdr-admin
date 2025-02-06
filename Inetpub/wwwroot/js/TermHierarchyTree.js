/**
 * Client-side scripting for the Term Hierarchy Tree report.
 */

// Copy term document IDs for a node in the tree to the clipboard.
function send_to_clipboard(ids, n) {
  navigator.clipboard.writeText(ids).then(() => {
    const message = n === 1 ? "1 leaf ID has" : `${n} leaf IDs have`;
    alert(`${message} been copied to the clipboard.`);
  }).catch(err => {
    const clipboard_area = document.getElementById("clipboard");
    const textarea = clipboard_area.querySelector("textarea");
    textarea.value = ids;
    clipboard_area.style.display = "block";
    alert("IDs have been copied to the edit box at the bottom of this page. " +
          "You can type Control/Command+C now to copy them to the clipboard.");
    console.error("Copy failed:", err);
  });
}

// Expand or collapse a node in the tree.
function toggle_node(event, id) {
  const node = document.getElementById(id);
  const children = node.querySelectorAll(":scope > ul");
  const sign = node.querySelector(":scope > span > span.sign");
  if (node.classList.contains("hide")) {
    node.classList.remove("hide");
    children.forEach(ul => ul.style.display = "block");
    sign.textContent = "-";
  } else {
    node.classList.add("hide");
    children.forEach(ul => ul.style.display = "none");
    sign.textContent = "+";
  }
  event.stopPropagation();
}
