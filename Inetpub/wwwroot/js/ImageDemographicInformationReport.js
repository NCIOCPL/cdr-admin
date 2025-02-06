/**
 * Client-side scripting for the Image Demographics report.
 */

// Create, install, and invoke the necessary event handlers.
document.addEventListener("DOMContentLoaded", () => {

  // Route the work to handle block visibility based on the user's selected report type.
  function check_type(value) {
    if (value === "images") {
      const method = document.querySelector("input[name='image_method']:checked").value;
      check_image_method(method);
    } else {
      const method = document.querySelector("input[name='summary_method']:checked").value;
      check_summary_method(method);
    }
  }

  // Hook up the click event listener to the report type radio buttons.
  document.querySelectorAll("input[name='type']").forEach(button => {
    button.addEventListener("click", () => check_type(button.value));
  });

  // Show the fieldsets needed by the user's chosen image selection method.
  function check_image_method(value) {
    document.querySelectorAll("fieldset.default-hidden").forEach(function(fieldset) {
      fieldset.style.display = "none";
    });

    document.getElementById("image-method-fieldset").style.display = "block";

    if (value === "id") {
      document.getElementById("image-id-fieldset").style.display = "block";
    } else if (value === "title") {
      document.getElementById("image-title-fieldset").style.display = "block";
    } else {
      document.getElementById("image-category-fieldset").style.display = "block";
    }
  }

  // Hook up the click event listener to the buttons for the image selection method.
  document.querySelectorAll("input[name='image_method']").forEach(button => {
    button.addEventListener("click", () => check_image_method(button.value));
  });

  // Show the fieldsets needed by the user's chosen summary selection method.
  function check_summary_method(value) {
    document.querySelectorAll("fieldset.default-hidden").forEach(function(fieldset) {
      fieldset.style.display = "none";
    });

    document.getElementById("summary-method-fieldset").style.display = "block";
    document.getElementById("summary-options-fieldset").style.display = "block";

    if (value === "id") {
      document.getElementById("summary-id-fieldset").style.display = "block";
    } else if (value === "title") {
      document.getElementById("summary-title-fieldset").style.display = "block";
    } else if (value === "board") {
      document.getElementById("summary-board-fieldset").style.display = "block";
    } else {
      document.getElementById("summary-type-fieldset").style.display = "block";
    }
  }

  // Hook up the click event listener to the buttons for the summary selection method.
  document.querySelectorAll("input[name='summary_method']").forEach(button => {
    button.addEventListener("click", () => check_summary_method(button.value));
  });

  // Make the "All Boards" option interact intelligently with the other board options.
  function check_board(val) {
    if (val === "all") {
      document.querySelectorAll("input[name='board']").forEach(function(input) {
        input.checked = false;
      });
      document.getElementById("board-all").checked = true;
    } else if (document.querySelectorAll("input[name='board']:checked").length > 0) {
      document.getElementById("board-all").checked = false;
    } else {
      document.getElementById("board-all").checked = true;
    }
  }

  // Hook up the click event listener to the checkboxes for the boards.
  document.querySelectorAll("input[name='board']").forEach(checkbox => {
    checkbox.addEventListener("click", () => check_board(checkbox.value));
  });

  // Set the appropriate block visibility.
  const value = document.querySelector("input[name='type']:checked").value;
  check_type(value);
});
