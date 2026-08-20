document.addEventListener("DOMContentLoaded", function () {
  var startButton = document.getElementById("startButton");
  var infoButton = document.getElementById("infoButton");
  var projectButton = document.getElementById("projectButton");
  var settingsButton = document.getElementById("settingsButton");

  if (startButton) {
    startButton.addEventListener("click", function () {
      window.location.href = "lesson-info.html";
    });
  }

  if (infoButton) {
    infoButton.addEventListener("click", function () {
      window.location.href = "info.html";
    });
  }

  if (projectButton) {
    projectButton.addEventListener("click", function () {
      window.location.href = "project-info.html";
    });
  }

  if (settingsButton) {
    settingsButton.addEventListener("click", function () {
      window.location.href = "settings.html";
    });
  }
});
