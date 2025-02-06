/**
 * Client-side scripting for the interface used to edit control values.
 */

// Repopulate the name picklist when a new group is selected.
function check_group() {
  const groupSelect = document.getElementById("group");
  const group = groupSelect[groupSelect.selectedIndex].value ?? "";
  const nameSelect = document.getElementById("name");
  nameSelect.innerHTML = "";
  groups[group]?.options?.forEach((o, i) => {
    const option = document.createElement("option");
    option.value = o.key;
    option.text = o.name;
    if (!i) {
      option.selected = true;
      nameSelect.selectedIndex = 0;
    }
    nameSelect.appendChild(option);
  });
  check_name();
}

// Handle switching to a different value name.
function check_name() {
  const groupSelect = document.getElementById("group");
  const group = groupSelect[groupSelect.selectedIndex].value ?? "";
  const nameSelect = document.getElementById("name");
  const name = nameSelect[nameSelect.selectedIndex].value ?? "";
  const values = groups[group].values[name];
  document.getElementById("value").value = values.value;
  document.getElementById("comment").value = values.comment;
}
