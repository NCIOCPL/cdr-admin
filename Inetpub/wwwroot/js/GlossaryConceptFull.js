/**
 * Client-side scripting for the Glossary Concept Full report.
 */

// Play a sound file.
document.addEventListener("DOMContentLoaded", function() {
  document.querySelectorAll("a.sound").forEach(function(element) {
    element.addEventListener("click", function(event) {
      var url = this.getAttribute("href");
      var audio = document.createElement("audio");
      audio.setAttribute("src", url);
      audio.load();
      audio.addEventListener("canplay", function() {
        audio.play();
      });
      event.preventDefault();
    });
  });
});
