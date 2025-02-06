/**
 * Client-side support for assigning members to CDR filter sets.
 */

// Call this every time the filter set membership changes.
function check_members() {

  // If we have real members, remove the placeholder.
  const count = document.querySelectorAll("#members li").length;
  if (count > 1) {
    const dummies = document.querySelectorAll("#members .dummy");
    dummies.forEach(dummy => dummy.remove());
  }

  // If the set of members is empty, add the placeholder.
  if (count < 1) {
    const dummy = '<li class="dummy">Add some members, please!</li>';
    const members = document.getElementById("members");
    members.insertAdjacentHTML("beforeend", dummy);
  }
}

// Update the 'members' hidden field and submit the form for saving the set.
function save(e) {
  const members = [];
  document.querySelectorAll("#members li").forEach(li => {
    const name = li.textContent;
    const type = li.getAttribute("class");
    if (type !== "dummy") {
      members.push({ name, type });
    }
  });
  const set_name = (document.getElementById("name").value ?? "").trim();
  if (!set_name) {
    alert("Set must have a title.");
    e.preventDefault();
  } else if (members.length < 1) {
    alert("Set has no members.");
    e.preventDefault();
  } else {
    const json = JSON.stringify(members);
    document.querySelector("input[name='members']").value = json;
    document.querySelector("input[name='action']").value = "Save Set";
    document.getElementById("primary-form").submit();
  }
}

// Support editing of the set membership using the graphical user interface.
document.addEventListener("DOMContentLoaded", () => {

  // Keep track of drag-and-drop state.
  let dragged_item = null;
  let remove_intent = false;

  // Find the container for the set membership.
  const members = document.getElementById("members");

  // Enable drag-and-drop for a list item.
  function make_draggable(element) {
    element.draggable = true;
    element.addEventListener("dragend", () => {
      if (dragged_item) {
        if (remove_intent) {
          dragged_item.remove();
        } else {
          dragged_item.classList.remove("dragging");
        }
        dragged_item = null;
      }
      check_members();
    });
  }

  // Attach listeners to the containers and their child items.
  ["filters", "sets", "members"].forEach(container_id => {
    const container = document.getElementById(container_id);
    container.addEventListener("dragstart", (event) => {
      if (event.target.tagName === "LI") {
        if (container_id === "members") {
          dragged_item = event.target;
        } else {
          dragged_item = event.target.cloneNode(true);
          make_draggable(dragged_item);
        }
        const inner_html = event.target.innerHTML;
        event.dataTransfer.setData("text/html", inner_html);
        event.dataTransfer.effectAllowed = "move";
        dragged_item.classList.add("dragging");
      }
      remove_intent = false;
    });
    container.addEventListener("dblclick", (event) => {
      if (event.target.tagName === "LI") {
        if (container_id === "members") {
          event.target.remove();
          check_members();
        } else {
          const cloned_member = event.target.cloneNode(true);
          make_draggable(cloned_member);
          members.appendChild(cloned_member);
          check_members();
        }
      }
    });
    container.querySelectorAll("li").forEach(item => make_draggable(item));
  });

  // Give visible feedback about where the element will land if dropped now.
  members.addEventListener("dragover", (event) => {
    event.preventDefault();
    const after_element = get_drag_after_element(members, event.clientY);
    if (dragged_item) {
      dragged_item.classList.remove("remove-intent");
      if (after_element == null) {
        members.appendChild(dragged_item);
      } else {
        members.insertBefore(dragged_item, after_element);
      }
      remove_intent = false;
    }
  });

  // An item has been added to or moved in the members container.
  members.addEventListener("drop", (event) => {
    event.preventDefault();
    dragged_item.classList.remove("dragging");
    dragged_item.classList.remove("remove-intent");
    dragged_item = null;
    remove_intent = false;
    check_members();
  });

  // Note that the member has been dragged out of the container.
  members.addEventListener("dragleave", () => {
    remove_intent = true;
    if (dragged_item) {
      dragged_item.classList.add("remove-intent");
    }
  });

  // Figure out where the element would get dropped if released now.
  function get_drag_after_element(container, y) {
    const items = [...container.querySelectorAll("li:not(.dragging)")];
    return items.reduce((closest, child) => {
      const box = child.getBoundingClientRect();
      const offset = y - box.top - box.height / 2;
      if (offset < 0 && offset > closest.offset) {
        return { offset, element: child };
      } else {
        return closest;
      }
    }, { offset: Number.NEGATIVE_INFINITY }).element;
  }

  // Intercept the Save action.
  const save_button = document.querySelector("input[value='Save Set']");
  save_button.addEventListener("click", save);

  // Make sure the set has at least a placeholder item.
  check_members();
});
