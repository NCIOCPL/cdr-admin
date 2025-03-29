/**
 * Client-side scripting for managing scheduled jobs.
 */

// Insert buttons for adding/removing job options.
function add_buttons() {
  document.querySelectorAll(".job-opt-button").forEach(button => button.remove());

  const legends = document.querySelectorAll(".opt-block legend");
  if (legends.length > 0) {
    legends[legends.length - 1].appendChild(green_button());
  }

  legends.forEach((legend, i) => {
    legend.appendChild(red_button(i));
  });
}

// Create a button which adds a new (empty) option block.
function green_button() {
  const span = document.createElement("span");
  span.className = "job-opt-button";

  const img = document.createElement("img");
  img.src = "/images/add.gif";
  img.onclick = () => add_option_block();
  img.className = "clickable";
  img.title = "Add another option";
  img.alt = "green plus sign";

  span.appendChild(img);
  return span;
}

// Create a button which removes the option block it's in.
function red_button(i) {
  const span = document.createElement("span");
  span.className = "job-opt-button";

  const img = document.createElement("img");
  img.src = "/images/del.gif";
  img.onclick = () => remove_option(i + 1);
  img.className = "clickable";
  img.title = "Remove option";
  img.alt = "red X";

  span.appendChild(img);
  return span;
}

// Add a new block, possibly with existing options.
function add_option_block(i, name, value) {
  const id = i ?? document.querySelectorAll(".opt-name").length + 1;

  const fieldset = document.createElement("fieldset");
  fieldset.className = "opt-block usa-fieldset";
  fieldset.id = `opt-block-${id}`;

  const legend = document.createElement("legend");
  legend.className = "usa-legend";
  legend.textContent = "Named Job Option";

  fieldset.appendChild(legend);
  fieldset.appendChild(make_field("name", id, "Name", name));
  fieldset.appendChild(make_field("value", id, "Value", value));

  const optionsBlock = document.getElementById("options-block");
  optionsBlock.parentNode.insertBefore(fieldset, optionsBlock);

  document.querySelector("input[name='num-opts']").value = id;
  i ?? add_buttons();
}

// Delete an option block and recreate all the remaining blocks.
function remove_option(id) {
  const blocks = collect_options(id);
  document.querySelectorAll(".opt-block").forEach(block => block.remove());
  blocks.forEach((block, i) => {
    add_option_block(i + 1, block.name, block.value);
  });
  if (blocks.length === 0) {
    add_option_block();
  }
  add_buttons();
}

// Create a labeled form field, possibly with an existing value.
function make_field(name, id, label, value) {
  const fieldName = `opt-${name}-${id}`;

  const field = document.createElement("div");
  field.className = "labeled-field";

  const labelElement = document.createElement("label");
  labelElement.className = "usa-label";
  labelElement.htmlFor = fieldName;
  labelElement.textContent = label;

  const input = document.createElement("input");
  input.className = `opt-${name} usa-input usa-input--xl`;
  input.name = fieldName;
  input.id = fieldName;
  if (value) input.value = value;

  field.appendChild(labelElement);
  field.appendChild(input);

  return field;
}

// Gather up all the value information so we can recreate the blocks.
// Leave out the block we're going to remove.
function collect_options(skip) {
  const count = parseInt(document.querySelector("input[name='num-opts']").value);
  const positions = Array.from({ length: count }, (_, i) => i + 1);

  return positions.filter(i => i !== skip).map(i => {
    const name = document.getElementById(`opt-name-${i}`).value;
    const value = document.getElementById(`opt-value-${i}`).value;
    return { name, value };
  });
}

// Add some buttons and some handlers when the page first loads.
document.addEventListener("DOMContentLoaded", () => {
  add_buttons();
  ["Run Job Now", "Delete Job"].forEach(text => {
    document.querySelector(`input[value="${text}"]`).addEventListener("click", e => {
      if (confirm("Are you sure?")) {
        return true;
      }
      e.preventDefault();
    });
  });
});
