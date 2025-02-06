/**
 * Client-side scripting for the filter testing page.
 */

// Function to add a new filter field
function add_filter_field() {
  const filters = document.querySelectorAll(".filter");
  const id = filters.length + 1;
  const wrapper = document.createElement("div");
  wrapper.className = "labeled-field filter";
  const input = document.createElement("input");
  input.name = "filter";
  input.id = `filter-${id}`;
  input.className = "usa-input usa-input--xl";

  wrapper.appendChild(input);
  document.getElementById("filters").appendChild(wrapper);
}

// Function to add new parameter fields
function add_parameter_fields() {

  // Create the wrapper element.
  const parameters = document.querySelectorAll(".parameter");
  const id = parameters.length + 1;
  document.getElementById("parm-count").value = id;
  const parm_div = document.createElement("div");
  parm_div.className = "parameter";

  // Create the name field.
  const name_div = document.createElement("div");
  name_div.className = "labeled-field parm-name";
  const name_label = document.createElement("label");
  name_label.className = "usa-label";
  name_label.htmlFor = `parm-name-${id}`;
  name_label.textContent = "Name";
  const name_input = document.createElement("input");
  name_input.className = "usa-input usa-input--xl";
  name_input.name = `parm-name-${id}`;
  name_input.id = `parm-name-${id}`;
  name_div.appendChild(name_label);
  name_div.appendChild(name_input);

  // Create the value field.
  const value_div = document.createElement("div");
  value_div.className = "labeled-field";
  const value_label = document.createElement("label");
  value_label.className = "usa-label";
  value_label.htmlFor = `parm-value-${id}`;
  value_label.textContent = "Value";
  const value_input = document.createElement("input");
  value_input.className = "usa-input usa-input--xl";
  value_input.name = `parm-value-${id}`;
  value_input.id = `parm-value-${id}`;

  // Assemble the block and add it to the DOM.
  value_div.appendChild(value_label);
  value_div.appendChild(value_input);
  parm_div.appendChild(name_div);
  parm_div.appendChild(value_div);
  document.getElementById("parameters").appendChild(parm_div);
}

// Function to check the glossary checkbox state
document.addEventListener("DOMContentLoaded", () => {
  const glossary = document.getElementById("glossary");
  glossary.addEventListener("click", () => {
    if (glossary.checked) {
      document.getElementById("glosspatient").checked = true;
      document.getElementById("glosshp").checked = true;
    }
  });
});
