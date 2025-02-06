/**
 * Client-side scripting for the Summary Metadata report.
 */

// Show the fields required for the current document selection method.
function check_method(method) {
  const blocks = [
    ["id", "doc-id-box"],
    ["title", "doc-title-box"],
    ["group", "group-box"],
  ];
  blocks.forEach(([m, id]) => document.getElementById(id).style.display = method === m ? "block" : "none");
}

// Hook up the listener and start out with the right blocks visible.
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("input[name='method']").forEach(button => {
    button.addEventListener("click", () => check_method(button.value));
  });
  const selector = "input[name='method']:checked";
  const method = document.querySelector(selector).value ?? "";
  check_method(method);
});
