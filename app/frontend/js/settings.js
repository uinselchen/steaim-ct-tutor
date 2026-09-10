document.addEventListener("DOMContentLoaded", function () {
  function setText(id, text, state) {
    var element = document.getElementById(id);
    if (!element) {
      return;
    }
    element.textContent = text;
    element.classList.remove("status-ok", "status-warning");
    if (state) {
      element.classList.add(state);
    }
  }

  function setInputValue(id, value) {
    var element = document.getElementById(id);
    if (element) {
      element.value = value || "";
    }
  }

  function renderPromptPaths(prompts) {
    var list = document.getElementById("promptPathList");
    if (!list) {
      return;
    }
    list.innerHTML = "";
    prompts = Array.isArray(prompts) ? prompts : [];
    if (!prompts.length) {
      var empty = document.createElement("li");
      empty.textContent = "No prompt files found.";
      list.appendChild(empty);
      return;
    }
    prompts.forEach(function (prompt) {
      var item = document.createElement("li");
      var state = prompt.exists ? "available" : "missing";
      item.textContent = (prompt.relativePath || prompt.name || "unknown") + " (" + state + ")";
      item.className = prompt.exists ? "status-ok" : "status-warning";
      list.appendChild(item);
    });
  }

  function renderRuntimeStatus(status) {
    var list = document.getElementById("startupStatusList");
    var summary = document.getElementById("startupStatusSummary");
    if (!list) {
      return;
    }
    var mistral = status.mistral || {};
    var runtime = status.runtime || {};
    var checks = [
      { ok: !!mistral.configured, label: mistral.configured ? "Mistral API key configured" : "Mistral API key missing" },
      { ok: runtime.exportDependencies !== false, label: runtime.exportDependencies !== false ? "DOCX/PDF export packages available" : "Missing export packages: " + (runtime.missingDependencies || []).join(", ") },
      { ok: runtime.requiredFolders !== false, label: runtime.requiredFolders !== false ? "Local tutor folders ready" : "Missing folders: " + (runtime.missingFolders || []).join(", ") },
      { ok: !!runtime.python, label: runtime.python ? "Python " + runtime.python + " detected" : "Python runtime unavailable" }
    ];
    list.innerHTML = "";
    checks.forEach(function (check) {
      var item = document.createElement("li");
      item.className = check.ok ? "status-ok" : "status-warning";
      item.textContent = (check.ok ? "✓ " : "! ") + check.label;
      list.appendChild(item);
    });
    var ready = checks.every(function (check) { return check.ok; });
    if (summary) {
      summary.textContent = ready ? "Ready" : "Action required";
      summary.className = ready ? "status-ok" : "status-warning";
    }
  }

  function applyStatus(status) {
    status = status || {};
    var mistral = status.mistral || {};
    var email = status.email || {};
    var paths = status.paths || {};

    renderRuntimeStatus(status);

    setText(
      "mistralStatus",
      mistral.configured
        ? "Configured. Model: " + (mistral.model || "default") + ". API URL: " + (mistral.apiUrl || "not set")
        : "No API key configured. Enter it below; it will be stored locally in " + (mistral.apiKeyFile || "app/server/mistral_api_key.txt") + ".",
      mistral.configured ? "status-ok" : "status-warning"
    );
    setText(
      "emailStatus",
      email.configured ? "Configured. Recipient: " + (email.recipient || "not shown") : "Missing SMTP or MAIL_TO_ADDRESS settings in app/server/.env.",
      email.configured ? "status-ok" : "status-warning"
    );
    setText(
      "curriculaStatus",
      paths.curriculaRoot ? "Using local folder: " + paths.curriculaRoot : "Curricula folder not found.",
      paths.curriculaRoot ? "status-ok" : "status-warning"
    );
    setText(
      "logsStatus",
      paths.outputRoot ? "Logs and exports are stored in: " + paths.outputRoot : "Output folder not found.",
      paths.outputRoot ? "status-ok" : "status-warning"
    );

    setInputValue("mistralApiUrl", mistral.apiUrl || "");
    setInputValue("mistralModel", mistral.model || "");
    renderPromptPaths(status.prompts || []);
  }

  function loadStatus() {
    return fetch("/settings-status")
      .then(function (response) {
        if (!response.ok) {
          throw new Error("Unable to load settings status.");
        }
        return response.json();
      })
      .then(applyStatus)
      .catch(function (error) {
        setText("mistralStatus", error.message, "status-warning");
        setText("emailStatus", "Status unavailable.", "status-warning");
        setText("curriculaStatus", "Status unavailable.", "status-warning");
        setText("logsStatus", "Status unavailable.", "status-warning");
      });
  }

  function saveSettings(event) {
    event.preventDefault();
    var form = event.currentTarget;
    var payload = {
      mistralApiUrl: form.mistralApiUrl.value.trim(),
      mistralModel: form.mistralModel.value.trim(),
      mistralApiKey: form.mistralApiKey.value.trim()
    };

    setText("settingsSaveStatus", "Saving settings...");
    fetch("/settings", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    })
      .then(function (response) {
        return response.json().then(function (data) {
          if (!response.ok) {
            throw new Error((data && data.error) || "Unable to save settings.");
          }
          return data;
        });
      })
      .then(function (data) {
        form.mistralApiKey.value = "";
        var keyFile = data.status && data.status.mistral && data.status.mistral.apiKeyFile
          ? data.status.mistral.apiKeyFile
          : "app/server/mistral_api_key.txt";
        setText("settingsSaveStatus", "The API Key is now stored locally under " + keyFile + ".", "status-ok");
        if (data.status) {
          applyStatus(data.status);
        } else {
          loadStatus();
        }
      })
      .catch(function (error) {
        setText("settingsSaveStatus", error.message || "Unable to save settings.", "status-warning");
      });
  }

  var form = document.getElementById("mistralSettingsForm");
  if (form) {
    form.addEventListener("submit", saveSettings);
  }

  loadStatus();
});
