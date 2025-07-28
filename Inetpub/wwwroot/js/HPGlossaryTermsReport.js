/**
 * Client-side support for the HP glossary terms report.
 */

// Install dictionary and report type change event listeners and invoke them.
document.addEventListener("DOMContentLoaded", () => {

  // Suppress the levels-of-evidence option for the Genetics dictionary.
  function check_dictionary() {
    const type = document.querySelector("#dictionary :checked").text;
    const wrapper = document.getElementById("loe-wrapper");
    wrapper.style.display = type === "Genetics" ? "none" : "block";
  }

  // Hide the pronunciation option for the list of terms report variant.
  function check_type() {
    const type = document.querySelector("#type :checked").text;
    const wrapper = document.getElementById("pronunciation-wrapper");
    wrapper.style.display = type === "List of Terms" ? "none" : "block";
  }

  // Install the event handlers.
  document.getElementById("type").addEventListener("change", check_type);
  document.getElementById("dictionary").addEventListener("change", check_dictionary);

  // Invoke them to set the correct initial checkbox visibilities.
  check_type();
  check_dictionary();
});
