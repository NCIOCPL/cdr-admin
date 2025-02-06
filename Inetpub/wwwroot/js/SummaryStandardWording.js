/**
 * Client-side scripting for the Summary Standard Wording report.
 */

// Add another search term field.
function add_term_field() {
  const id = "term-" + (document.querySelectorAll(".term").length + 1);

  // Create a div element with class "labeled-field".
  const field = document.createElement("div");
  field.classList.add("labeled-field");

  // Create a label element with attributes.
  const label = document.createElement("label");
  label.setAttribute("for", id);
  label.classList.add("usa-label");
  label.textContent = "Term";

  // Create an input element with attributes.
  const input = document.createElement("input");
  input.classList.add("term", "usa-input", "usa-input--xl");
  input.setAttribute("name", "term");
  input.setAttribute("id", id);

  // Append the label and input to the field div.
  field.appendChild(label);
  field.appendChild(input);

  // Append the field div to the element with ID "search-terms".
  document.getElementById("search-terms").appendChild(field);
}
