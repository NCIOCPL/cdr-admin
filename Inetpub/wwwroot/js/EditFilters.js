/**
 * Client-side scripting for the Manage Filters page.
 */

// Flip between two displays of the filters, each sorted differently.
function toggle(show, hide) {
  document.getElementById(show).style.display = "block";
  document.getElementById(hide).style.display = "none";
}

// Set the listeners, classes, and initial block visibility.
document.addEventListener("DOMContentLoaded", () => {
  const titleCol = document.querySelector("#idsort .title-col");
  const idCol = document.querySelector("#titlesort .id-col");
  titleCol.addEventListener("click", () => toggle("titlesort", "idsort"));
  idCol.addEventListener("click", () => toggle("idsort", "titlesort"));
  [titleCol, idCol].forEach(col => col.classList.add("clickable"));
  toggle("titlesort", "idsort");
});