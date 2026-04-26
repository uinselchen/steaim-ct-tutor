document.addEventListener("DOMContentLoaded", function () {
  var startButton = document.getElementById("startButton");
  var infoButton = document.getElementById("infoButton");
  var projectButton = document.getElementById("projectButton");

  startButton.addEventListener("click", function () {
    window.location.href = "lesson-info.html";
  });

  infoButton.addEventListener("click", function () {
    window.location.href = "info.html";
  });

  projectButton.addEventListener("click", function () {
    window.location.href = "project-info.html";
  });
});
