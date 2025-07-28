/**
 * Client-side scripting for the document display page.
 */

// Adjust block visibility to match current document selection method.
function check_selection_method(method) {
  switch (method) {
    case "id":
      document.getElementById("by-id-block").style.display = "block";
      document.getElementById("by-title-block").style.display = "none";
      break;
    case "title":
      document.getElementById("by-id-block").style.display = "none";
      document.getElementById("by-title-block").style.display = "block";
      break;
  }
}

// Show the version number block if that's how the version will be specified.
function check_vtype(vtype) {
  const display = vtype === "num" ? "block" : "none";
  document.getElementById("version-number-block").style.display = display;
}

// Install listeners and set initial block visibility.
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("input[name='selection_method']").forEach(button => {
    button.addEventListener("click", () => check_selection_method(button.value));
  });
  document.querySelectorAll("input[name='vtype']").forEach(button => {
    button.addEventListener("click", () => check_vtype(button.value));
  });
  const selectionMethod = document.querySelector("input[name='selection_method']:checked").value ?? "";
  const versionType = document.querySelector("input[name='vtype']:checked").value ?? "";
  check_selection_method(selectionMethod);
  check_vtype(versionType);
});
