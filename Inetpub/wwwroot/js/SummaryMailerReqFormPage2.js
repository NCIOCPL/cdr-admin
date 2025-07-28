/**
 * Client-side scripting for the summary mailer request cascading form.
 */

// Check all checkboxes on the page.
function check_all() {
  [".outer-cb input", ".inner-cb input"].forEach(selector => {
    document.querySelectorAll(selector).forEach(cb => cb.checked = true);
  });
}

// Uncheck all checkboxes on the page.
function clear_all() {
  [".outer-cb input", ".inner-cb input"].forEach(selector => {
    document.querySelectorAll(selector).forEach(cb => cb.checked = false);
  });
}

// If any inner value is selected, so must its matching outer value be.
function inner_clicked(id) {
  const selector = `.inner-${id}:checked`;
  const checked = document.querySelectorAll(selector).length > 0;
  document.getElementById(`outer-${id}`).checked = checked;
}

// Make the states of a set of inner checkboxes match their corresponding
// outer checkbox's new state.
function outer_clicked(id) {
  const state = document.getElementById(`outer-${id}`).checked;
  document.querySelectorAll(`.inner-${id}`).forEach(cb => cb.checked = state);
}
