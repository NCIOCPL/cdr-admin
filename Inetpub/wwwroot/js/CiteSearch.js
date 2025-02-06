/**
 * Client-side scripting for the advanced citation search form.
 */

// Set the name of the Import/Update button.
function chk_cdrid() {
  const cdrid = document.getElementById("cdrid").value;
  const button = document.getElementById("submit-button-import");
  if (cdrid.replace(/\D/g, "").length === 0) {
    button.value = "Import";
  } else {
    button.value = "Update";
  }
}

// The Import/Update button is only available when a PMID has been entered.
function chk_pmid() {
  const pmid = document.getElementById("pmid").value.trim();
  const button = document.getElementById("submit-button-import");
  button.disabled = pmid.length === 0;
}

// Avoid opening a new tab for and import or update.
function clear_target() {
  document.getElementById("primary-form").setAttribute("target", "");
}

// Apply initial configuration of the Import/Update button.
document.addEventListener("DOMContentLoaded", () => {
  chk_cdrid();
  chk_pmid();
});
