document.addEventListener("DOMContentLoaded", function () {
  // Each tutor restart begins in English; the selection can still be changed for this run.
  window.localStorage.setItem("preferredLanguage", "English");
  window.localStorage.setItem("preferredLanguageCountry", "");
  window.dispatchEvent(new Event("languagechange"));

  // A browser session starts with no lesson-specific conversation state.
  if (!window.sessionStorage.getItem("tutorSessionInitialized")) {
    ["step2Analysis", "step2UploadMeta", "step2Selections", "step2Preparation", "step2PointDiscussions", "step2AdditionalUploadMeta", "step2PrivacyWarning", "step3Draft", "step3Conversation", "step3Progress", "step3Session"].forEach(function (key) {
      window.localStorage.removeItem(key);
    });
    window.sessionStorage.setItem("tutorSessionInitialized", "1");
  }

  var startButton = document.getElementById("startButton");
  var infoButton = document.getElementById("infoButton");
  var projectButton = document.getElementById("projectButton");
  var settingsButton = document.getElementById("settingsButton");
  var apiKeyModalBackdrop = document.getElementById("apiKeyModalBackdrop");
  var configureApiKeyButton = document.getElementById("configureApiKeyButton");
  var apiKeyModalTitle = document.getElementById("apiKeyModalTitle");
  var apiKeyModalMessage = document.getElementById("apiKeyModalMessage");
  var languageCountrySelect = document.getElementById("languageCountrySelect");
  var apiKeyConfigured = null;
  var setupReady = null;

  var countryLanguages = {
    Austria: "German",
    Germany: "German",
    Switzerland: "German",
    Spain: "Spanish",
    CzechRepublic: "Czech",
    Poland: "Polish",
    Portugal: "Portuguese",
    Italy: "Italian",
    France: "French",
    Slovakia: "Slovak",
    Hungary: "Hungarian",
    Slovenia: "Slovenian",
    Croatia: "Croatian",
    Romania: "Romanian",
    Bulgaria: "Bulgarian",
    Greece: "Greek"
  };

  function languageForCountry(country) {
    var key = String(country || "").replace(/[^A-Za-z]/g, "");
    return countryLanguages[key] || String(country || "English");
  }

  function loadLanguageCountries() {
    if (!languageCountrySelect) {
      return;
    }
    fetch("/config")
      .then(function (response) {
        if (!response.ok) {
          throw new Error("Unable to load countries.");
        }
        return response.json();
      })
      .then(function (config) {
        var countries = Array.isArray(config && config.countries) ? config.countries : [];
        var storedCountry = window.localStorage.getItem("preferredLanguageCountry") || "";
        languageCountrySelect.innerHTML = "";
        var defaultOption = document.createElement("option");
        defaultOption.value = "";
        defaultOption.textContent = "English (default)";
        languageCountrySelect.appendChild(defaultOption);
        countries.forEach(function (country) {
          var option = document.createElement("option");
          option.value = country;
          option.textContent = country + " (" + languageForCountry(country) + ")";
          languageCountrySelect.appendChild(option);
        });
        if (countries.indexOf(storedCountry) !== -1) {
          languageCountrySelect.value = storedCountry;
        } else {
          languageCountrySelect.value = "";
          window.localStorage.setItem("preferredLanguageCountry", "");
          window.localStorage.setItem("preferredLanguage", "English");
        }
        window.dispatchEvent(new Event("languagechange"));
      })
      .catch(function () {
        languageCountrySelect.innerHTML = "<option value=\"\">English (default)</option>";
      });
  }

  if (languageCountrySelect) {
    languageCountrySelect.addEventListener("change", function () {
      var country = languageCountrySelect.value;
      window.localStorage.setItem("preferredLanguageCountry", country);
      window.localStorage.setItem("preferredLanguage", languageForCountry(country));
      window.dispatchEvent(new Event("languagechange"));
    });
  }

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
  loadLanguageCountries();
});
