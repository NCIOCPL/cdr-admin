/**
 * Client-side scripting for managing glossifier servers.
 */

// Insert buttons for adding/removing server blocks.
function add_buttons() {

  // Clear out the existing server buttons.
  const buttons = document.querySelectorAll(".glossary-server-button");
  buttons.forEach(button => button.remove());

  // Attach a button to the last server block for adding a new one.
  const legends = document.querySelectorAll(".server-block legend");
  if (legends.length > 0) {
    legends[legends.length - 1].appendChild(green_button());
  }

  // Add a delete button to each server block.
  legends.forEach((legend, i) => {
    legend.appendChild(red_button(i));
  });
}

// Create a button which adds a new (empty) server block.
function green_button() {
  const span = document.createElement("span");
  span.className = "glossary-server-button";

  const img = document.createElement("img");
  img.src = "/images/add.gif";
  img.onclick = () => add_server_block();
  img.className = "clickable";
  img.title = "Add another server";
  img.alt = "green plus sign";

  span.appendChild(img);
  return span;
}

// Create a button which removes the server block it's in.
function red_button(i) {
  const span = document.createElement("span");
  span.className = "glossary-server-button";

  const img = document.createElement("img");
  img.src = "/images/del.gif";
  img.onclick = () => remove_server(i + 1);
  img.className = "clickable";
  img.title = "Remove server";
  img.alt = "red X";

  span.appendChild(img);
  return span;
}

// Add a server block, possibly with existing values.
function add_server_block(i, alias, url) {
  const id = i ?? document.querySelectorAll(".alias").length + 1;

  const fieldset = document.createElement("fieldset");
  fieldset.className = "server-block usa-fieldset";
  fieldset.id = `server-block-${id}`;

  const legend = document.createElement("legend");
  legend.className = "usa-legend";
  legend.textContent = "Server";

  fieldset.appendChild(legend);
  fieldset.appendChild(make_field("alias", id, "Alias", alias));
  fieldset.appendChild(make_field("url", id, "URL", url));

  const submitButton = document.getElementById("submit-button-submit");
  submitButton.parentNode.insertBefore(fieldset, submitButton);

  document.querySelector("input[name='num-servers']").value = id;
  i ?? add_buttons();
}

// Delete a server block and recreate all the remaining blocks.
function remove_server(id) {
  const blocks = collect_servers(id);
  document.querySelectorAll(".server-block").forEach(block => block.remove());
  blocks.forEach((server, i) => {
    add_server_block(i + 1, server.alias, server.url);
  });
  if (blocks.length === 0) {
    add_server_block();
  }
  add_buttons();
}

// Create a labeled form field, possibly with an existing value.
function make_field(name, id, label, value) {
  const fieldName = `${name}-${id}`;

  const field = document.createElement("div");
  field.className = "labeled-field";

  const labelElement = document.createElement("label");
  labelElement.className = "usa-label";
  labelElement.htmlFor = fieldName;
  labelElement.textContent = label;

  const input = document.createElement("input");
  input.className = `${name} usa-input usa-input--xl`;
  input.name = fieldName;
  input.id = fieldName;
  if (value) input.value = value;

  field.appendChild(labelElement);
  field.appendChild(input);

  return field;
}

// Gather up all the server information so we can recreate the blocks.
// Leave out the block we're going to remove.
function collect_servers(skip) {
  const count = parseInt(document.querySelector("input[name='num-servers']").value);
  const positions = Array.from({ length: count }, (_, i) => i + 1);

  return positions.filter(i => i !== skip).map(i => {
    const url = document.getElementById(`url-${i}`).value;
    const alias = document.getElementById(`alias-${i}`).value;
    return { alias, url };
  });
}

// Add the red and green buttons when the page first loads.
document.addEventListener("DOMContentLoaded", () => add_buttons());
