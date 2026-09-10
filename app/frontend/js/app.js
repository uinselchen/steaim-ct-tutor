document.addEventListener("DOMContentLoaded", function () {
  var startButton = document.getElementById("startButton");
  var infoButton = document.getElementById("infoButton");
  var projectButton = document.getElementById("projectButton");
  var settingsButton = document.getElementById("settingsButton");
  var apiKeyModalBackdrop = document.getElementById("apiKeyModalBackdrop");
  var configureApiKeyButton = document.getElementById("configureApiKeyButton");
  var apiKeyModalTitle = document.getElementById("apiKeyModalTitle");
  var apiKeyModalMessage = document.getElementById("apiKeyModalMessage");
  var apiKeyConfigured = null;
  var setupReady = null;

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
        setupReady = !status.runtime || status.runtime.ready === true;
        if (!apiKeyConfigured || !setupReady) {
          showSetupRequired(status);
        }
      })
      .catch(function () {
        setupReady = false;
        showSetupRequired(null);
      });
  }

  function showSetupRequired(status) {
    if (!status) {
      if (apiKeyModalTitle) {
        apiKeyModalTitle.textContent = "Setup status unavailable";
      }
      if (apiKeyModalMessage) {
        apiKeyModalMessage.textContent = "The tutor could not verify its setup. Open Admin settings for the detailed system check.";
      }
      setApiKeyModalOpen(true);
      return;
    }
    var runtime = status && status.runtime ? status.runtime : {};
    var missing = [];
    if (!apiKeyConfigured) {
      missing.push("the Mistral API key");
    }
    if (runtime.exportDependencies === false) {
      missing.push("DOCX/PDF export packages");
    }
    if (runtime.requiredFolders === false) {
      missing.push("required local folders");
    }
    if (apiKeyModalTitle) {
      apiKeyModalTitle.textContent = missing.length ? "Setup required" : "Setup status unavailable";
    }
    if (apiKeyModalMessage) {
      apiKeyModalMessage.textContent = missing.length
        ? "This computer is missing " + missing.join(" and ") + ". Open Admin settings to see the detailed system check and next steps."
        : "The tutor could not verify its setup. Open Admin settings for the detailed system check.";
    }
    setApiKeyModalOpen(true);
  }

  if (startButton) {
    startButton.addEventListener("click", function () {
      if (apiKeyConfigured !== true || setupReady !== true) {
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
