/**
 * Client-side scripting for the ad-hoc query page.
 */

// Make the SQL window track the selected query.
function show_query() {
  const select = document.getElementById("query");
  const query = select.options[select.selectedIndex]?.value;
  document.getElementById("sql").value = queries[query] ?? "";
  adjust_height();
}

// Dynamically resize the SQL textarea to fit the value.
function adjust_height() {
  let box = document.getElementById("sql");
  let sql = box.value + "x";
  let rows = sql.split(/\r\n|\r|\n/).length;
  if (box.getAttribute("rows") != rows) {
    box.setAttribute("rows", rows);
  }
}

// Set the initial focus and register an event handler.
document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("query").focus();
  document.getElementById("sql").addEventListener("input", adjust_height);
});
