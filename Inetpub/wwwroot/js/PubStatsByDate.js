/**
 * Client-side scripting for the Publishing Job Statistics By Date report.
 */

// Make the document type checkboxes play nice with each other.
document.addEventListener("DOMContentLoaded", () => {
  function check_doctype(name) {
    const all = document.getElementById("doctype-all");
    const ind = document.querySelectorAll(".dt:checked");
    if (name == "all") {
      ind.forEach(cb => cb.checked = false);
      all.checked = true;
    } else {
      all.checked = ind.length < 1;
    }
  }
  document.querySelectorAll("input[name='doctype']").forEach(checkbox => {
    checkbox.addEventListener("click", () => check_doctype(checkbox.value));
  });
});
