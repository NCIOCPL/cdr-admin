/* Client-side scripting for QC report forms. */

// Install event handlers to add custom handling for the report options.
document.addEventListener("DOMContentLoaded", () => {

  // Adjust block visibility and checkbox settings for the report option fields.
  function check_options(option) {

    // If the user wants to see images, show the companion checkbox.
    if (option === "images") {
      const images = document.getElementById("options-images");
      const pub = document.getElementById('pub-images');
      pub.style.display = images.checked ? "block" : "none";
    }

    // Coordinate the two sets of checkboxes for controlling which
    // comments are to be displayed for summaries. This reproduces the
    // bugs in the original version, because the users are fond of those
    // bugs. :)
    else if (option === "com-all") {
      const alt = document.querySelectorAll("#alternate-comment-options input");
      alt.forEach(checkbox => checkbox.checked = true);
      document.querySelectorAll(".comgroup input").forEach(checkbox => checkbox.checked = false);
      document.getElementById("options-com-all").checked = true;
    }
    else if (option === "com-none") {
      const alt = document.querySelectorAll("#alternate-comment-options input");
      alt.forEach(checkbox => checkbox.checked = false);
      document.querySelectorAll(".comgroup input").forEach(checkbox => checkbox.checked = false);
      document.getElementById("options-com-none").checked = true;
    }
    else if (option === "com-int" || option === "com-perm") {
      const internal = document.getElementById("options-com-int");
      const permanent = document.getElementById("options-com-perm");
      // Remember these flags so we can restore them below.
      const internalChecked = internal.checked;
      const permanentChecked = permanent.checked;
      var key = (internalChecked ? "Y" : "N") + (permanentChecked ? "Y" : "N");
      var uncheck = {
        YY: ["aud-ext"],
        YN: ["aud-ext", "dur-perm"],
        NY: ["dur-temp"],
        NN: []
      };
      if (uncheck[key].length) {
        const alt = document.querySelectorAll("#alternate-comment-options input");
        alt.forEach(checkbox => checkbox.checked = true);
        uncheck[key].forEach(value => document.getElementById(`options-com-${value}`).checked = false);
        document.querySelectorAll(".comgroup input").forEach(checkbox => checkbox.checked = false);
        internal.checked = internalChecked;
        permanent.checked = permanentChecked;
      }
    }
    else if (option === "com-ext" || option === "com-adv") {
      const external = document.getElementById("options-com-ext");
      const advisory = document.getElementById("options-com-adv");
      // Remember these flags so we can restore them below.
      const externalChecked = external.checked;
      const advisoryChecked = advisory.checked;
      var key = (externalChecked ? "Y" : "N") + (advisoryChecked ? "Y" : "N");
      var uncheck = {
        YY: option === "com_ext" ? ["aud-int", "src-adv"] : ["aud-int"],
        YN: ["aud-int", "src-adv"],
        NY: ["src-ed"],
        NN: []
      };
      if (uncheck[key].length) {
        const alt = document.querySelectorAll("#alternate-comment-options input");
        alt.forEach(checkbox => checkbox.checked = true);
        uncheck[key].forEach(value => document.getElementById(`options-com-${value}`).checked = false);
        document.querySelectorAll(".comgroup input").forEach(checkbox => checkbox.checked = false);
        external.checked = externalChecked;
        advisory.checked = advisoryChecked;
      }
    }
  }
  document.querySelectorAll("input[name='options']").forEach(checkbox => {
    checkbox.addEventListener("click", () => check_options(checkbox.value));
  });

  // Show/hide the parallel set of comment checkboxes.
  document.getElementById("show-options").addEventListener("click", () => {
    const container = document.getElementById("alternate-comment-options");
    const button = document.getElementById("show-options");
    if (container.style.display === 'block') {
      container.style.display = 'none';
      button.textContent = "Show Individual Options";
    }
    else {
      container.style.display = 'block';
      button.textContent = "Hide Individual Options";
    }
  });
});
