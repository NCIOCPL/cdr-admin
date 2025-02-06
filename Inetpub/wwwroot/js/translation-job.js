/**
 * Client-side scription for the translation job editing forms.
 */

// Prevent accidental deletions and double submissions.
document.addEventListener("DOMContentLoaded", () => {
  let submitted = false;
  const sub = document.getElementById("submit-button-submit");
  const del = document.getElementById("submit-button-delete");
  sub.addEventListener("click", (e) => {
    if (!submitted) {
      submitted = true;
      return true;
    }
    e.preventDefault();
  });
  if (del) {
    del.addEventListener("click", (e) => {
      if (confirm("Are you sure?")) {
        return true;
      }
      e.preventDefault();
    });
  }
});
