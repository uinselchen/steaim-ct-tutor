document.addEventListener("DOMContentLoaded", function () {
  var startButton = document.getElementById("startButton");
  var infoButton = document.getElementById("infoButton");
  var projectButton = document.getElementById("projectButton");
  var settingsButton = document.getElementById("settingsButton");
  var apiKeyModalBackdrop = document.getElementById("apiKeyModalBackdrop");
  var configureApiKeyButton = document.getElementById("configureApiKeyButton");
  var apiKeyConfigured = null;

  function setApiKeyModalOpen(open) {
    if (!apiKeyModalBackdrop) {
      return;
    }
    apiKeyModalBackdrop.classList.toggle("open", open);
    apiKeyModalBackdrop.setAttribute("aria-hidden", open ? "false" : "true");
  }

  function loadApiKeyStatus() {
    return fetch("/settings-status")
      .then(function (response) {
        if (!response.ok) {
          throw new Error("Unable to load API key status.");
        }
        return response.json();
      })
      .then(function (status) {
        apiKeyConfigured = Boolean(status && status.mistral && status.mistral.configured);
        if (!apiKeyConfigured) {
          setApiKeyModalOpen(true);
        }
      })
      .catch(function () {
        // The tutor can still be opened if the status endpoint is unavailable.
      });
  }

  if (startButton) {
    startButton.addEventListener("click", function () {
      if (apiKeyConfigured !== true) {
        setApiKeyModalOpen(true);
        return;
      }
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

  if (configureApiKeyButton) {
    configureApiKeyButton.addEventListener("click", function () {
      window.location.href = "settings.html";
    });
  }

  loadApiKeyStatus();
});
