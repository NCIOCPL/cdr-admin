/**
 * Client-side scripting for the drug information lists report.
 */

// Don't show extra columns without grid lines.
document.addEventListener("DOMContentLoaded", () => {
  const gridlines = document.getElementById("options-gridlines");
  const extra = document.getElementById("options-extra");
  function adjust() {
    if (!gridlines.checked) {
      extra.checked = false;
    }
  }
  [gridlines, extra].forEach(cb => cb.addEventListener("click", adjust));
});
