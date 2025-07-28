/**
 * Client-side scripting for the User editing form.
 */

// Create the account type listener and invoke it.
document.addEventListener("DOMContentLoaded", () => {

  // Show/hide the password fields depending on the account type.
  function check_authmode(mode) {
    const display = mode === "local" ? "block" : "none";
    document.getElementById("password-fields").style.display = display;
  }

  // Hook up the click event listener to the account type radio buttons.
  const buttons = document.querySelectorAll("input[name='authmode']");
  buttons.forEach(b => b.addEventListener("click", () => check_authmode(b.value)));

  // Set the initial visibility for the password fields.
  const mode = document.querySelector("input[name='authmode']:checked").value;
  check_authmode(mode);
});
