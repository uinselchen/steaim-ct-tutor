document.addEventListener("DOMContentLoaded", function () {
  var countrySelect = document.getElementById("country");
  var countryOtherInput = document.getElementById("countryOther");
  var addCountryButton = document.getElementById("addCountryButton");
  var subjectCheckboxes = document.getElementById("subjectCheckboxes");
  var subjectOtherInput = document.getElementById("subjectOther");
  var addSubjectButton = document.getElementById("addSubjectButton");
  var fileDropzone = document.getElementById("fileDropzone");
  var fileInput = document.getElementById("lessonPlanUpload");
  var fileName = document.getElementById("fileName");
  var continueButton = document.getElementById("continueButton");
  var moreInfoButton = document.getElementById("moreInfoButton");

  var currentSubjects = [];
  var currentCountries = [];

  function setError(id, message) {
    var element = document.getElementById(id);
    if (element) {
      element.textContent = message;
    }
  }

  function clearError(id) {
    setError(id, "");
  }

  function updateFileDisplay() {
    var file = fileInput.files[0];
    fileName.textContent = file ? file.name + " (" + Math.round(file.size / 1024) + " KB)" : "";
  }

  function toggleCountryOther() {
    var isOther = countrySelect.value === "Other";
    countryOtherInput.style.display = isOther ? "block" : "none";
    addCountryButton.style.display = isOther && countryOtherInput.value.trim() ? "inline-flex" : "none";
    if (!isOther) {
      countryOtherInput.value = "";
    }
  }

  function updateAddCountryButton() {
    var isOther = countrySelect.value === "Other";
    var customCountry = countryOtherInput.value.trim();
    addCountryButton.style.display = isOther && customCountry ? "inline-flex" : "none";
  }

  function toggleSubjectOther() {
    var otherCheckbox = document.getElementById("subjectOtherCheckbox");
    var isChecked = otherCheckbox && otherCheckbox.checked;
    subjectOtherInput.style.display = isChecked ? "block" : "none";
    addSubjectButton.style.display = isChecked ? "inline-flex" : "none";
    if (!isChecked) {
      subjectOtherInput.value = "";
    }
    updateAddSubjectButton();
  }

  function updateAddSubjectButton() {
    var otherCheckbox = document.getElementById("subjectOtherCheckbox");
    var customText = subjectOtherInput.value.trim();
    if (otherCheckbox && otherCheckbox.checked && customText) {
      addSubjectButton.style.display = "inline-flex";
    } else {
      addSubjectButton.style.display = "none";
    }
  }

  function updateAddSubjectButton() {
    var otherCheckbox = document.getElementById("subjectOtherCheckbox");
    var customText = subjectOtherInput.value.trim();
    if (otherCheckbox && otherCheckbox.checked && customText) {
      addSubjectButton.style.display = "inline-flex";
    } else {
      addSubjectButton.style.display = "none";
    }
  }

  function getSelectedSubjects() {
    var subjects = Array.from(document.querySelectorAll("input[name='subjects']:checked")).map(function (input) {
      return input.value;
    });
    var otherCheckbox = document.getElementById("subjectOtherCheckbox");
    if (otherCheckbox && otherCheckbox.checked) {
      var custom = subjectOtherInput.value.trim();
      if (custom) {
        return subjects.filter(function (item) {
          return item !== "Other";
        }).concat(custom);
      }
    }
    return subjects;
  }

  function normalizeNumericText(value) {
    if (!value) {
      return null;
    }
    var digits = value.match(/\d+/g);
    return digits ? digits.join("") : null;
  }

  function handleNumericInput(event) {
    var input = event.target;
    var sanitized = normalizeNumericText(input.value);
    if (input.value !== sanitized) {
      if (sanitized) {
        window.alert("Only numeric characters are allowed. Non-numeric text was removed.");
      } else {
        window.alert("Only numeric characters are allowed. Please enter digits only.");
      }
      input.value = sanitized;
    }
  }

  function showInputGuidance(fieldName) {
    var message = "Please enter only numbers in these fields.";
    if (fieldName === "grade") {
      message = "Please enter grade values as numbers, for example '4'.";
    } else if (fieldName === "age") {
      message = "Please enter age values as numbers, for example '11'.";
    }
    window.alert(message);
  }

  function populateSelect(options) {
    currentCountries = options.slice();
    countrySelect.innerHTML = "<option value=\"\">Select country</option>";
    options.forEach(function (country) {
      var option = document.createElement("option");
      option.value = country;
      option.textContent = country;
      countrySelect.appendChild(option);
    });
    if (options.indexOf("Other") === -1) {
      var otherOption = document.createElement("option");
      otherOption.value = "Other";
      otherOption.textContent = "Other";
      countrySelect.appendChild(otherOption);
    }
    toggleCountryOther();
  }

  function populateSubjects(subjects) {
    currentSubjects = subjects.slice();
    subjectCheckboxes.innerHTML = "";
    subjects.forEach(function (subject) {
      var label = document.createElement("label");
      var input = document.createElement("input");
      input.type = "checkbox";
      input.name = "subjects";
      input.value = subject;
      label.appendChild(input);
      label.appendChild(document.createTextNode(" " + subject));
      subjectCheckboxes.appendChild(label);
    });

    var otherLabel = document.createElement("label");
    var otherInput = document.createElement("input");
    otherInput.type = "checkbox";
    otherInput.name = "subjects";
    otherInput.value = "Other";
    otherInput.id = "subjectOtherCheckbox";
    otherLabel.appendChild(otherInput);
    otherLabel.appendChild(document.createTextNode(" Other"));
    subjectCheckboxes.appendChild(otherLabel);

    var otherCheckbox = document.getElementById("subjectOtherCheckbox");
    if (otherCheckbox) {
      otherCheckbox.addEventListener("change", toggleSubjectOther);
    }
    toggleSubjectOther();
  }

  function loadConfig() {
    fetch("/config")
      .then(function (response) {
        if (!response.ok) {
          throw new Error("Unable to load config");
        }
        return response.json();
      })
      .then(function (config) {
        populateSelect(config.countries || []);
        populateSubjects(config.subjects || []);
      })
      .catch(function () {
        populateSelect(["Slovakia", "Germany", "Austria", "Spain"]);
        populateSubjects(["Mathematics", "Informatics / CS", "Biology", "Physics", "Chemistry"]);
      });
  }

  function saveCustomSubject(subject) {
    return fetch("/config", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ newSubject: subject })
    });
  }

  function saveCustomCountry(country) {
    return fetch("/config", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ newCountry: country })
    });
  }

  function validateForm() {
    var valid = true;
    clearError("countryError");
    clearError("subjectsError");
    clearError("gradeError");
    clearError("ageError");
    clearError("fileError");

    var country = countrySelect.value.trim();
    var countryOtherText = countryOtherInput.value.trim();
    var subjects = getSelectedSubjects();
    var file = fileInput.files[0];
    var otherCheckbox = document.getElementById("subjectOtherCheckbox");
    var otherText = subjectOtherInput.value.trim();
    var gradeFromRaw = document.getElementById("gradeFrom").value.trim();
    var gradeToRaw = document.getElementById("gradeTo").value.trim();
    var ageFromRaw = document.getElementById("ageFrom").value.trim();
    var ageToRaw = document.getElementById("ageTo").value.trim();

    var gradeFrom = normalizeNumericText(gradeFromRaw);
    var gradeTo = normalizeNumericText(gradeToRaw);
    var ageFrom = normalizeNumericText(ageFromRaw);
    var ageTo = normalizeNumericText(ageToRaw);

    if (!country) {
      setError("countryError", "Please select a country.");
      valid = false;
    }

    if (country === "Other" && !countryOtherText) {
      setError("countryError", "Please specify your country.");
      valid = false;
    }

    if (!subjects.length) {
      setError("subjectsError", "Please select at least one subject.");
      valid = false;
    }

    if (otherCheckbox && otherCheckbox.checked && !otherText) {
      setError("subjectsError", "Please specify your other subject.");
      valid = false;
    }

    if (gradeFromRaw && gradeFrom === null) {
      setError("gradeError", "Please enter a valid grade value.");
      showInputGuidance("grade");
      valid = false;
    }
    if (gradeToRaw && gradeTo === null) {
      setError("gradeError", "Please enter a valid grade value.");
      showInputGuidance("grade");
      valid = false;
    }
    if (ageFromRaw && ageFrom === null) {
      setError("ageError", "Please enter a valid age value.");
      showInputGuidance("age");
      valid = false;
    }
    if (ageToRaw && ageTo === null) {
      setError("ageError", "Please enter a valid age value.");
      showInputGuidance("age");
      valid = false;
    }

    if (!gradeFromRaw) {
      setError("gradeError", "Please enter at least one grade.");
      valid = false;
    } else if (!gradeFrom) {
      setError("gradeError", "Please enter a valid grade value.");
      showInputGuidance("grade");
      valid = false;
    } else if (gradeToRaw && !gradeTo) {
      setError("gradeError", "Please enter a valid grade value.");
      showInputGuidance("grade");
      valid = false;
    } else if (gradeFrom && gradeTo && parseInt(gradeFrom, 10) > parseInt(gradeTo, 10)) {
      setError("gradeError", "Please make sure the grade range is valid.");
      valid = false;
    }

    if ((ageFromRaw && !ageToRaw) || (!ageFromRaw && ageToRaw)) {
      setError("ageError", "Please enter both age fields or leave them blank.");
      valid = false;
    } else if ((ageFromRaw || ageToRaw) && (ageFrom === null || ageTo === null)) {
      setError("ageError", "Please enter a valid age range.");
      showInputGuidance("age");
      valid = false;
    } else if (ageFrom && ageTo && parseInt(ageFrom, 10) > parseInt(ageTo, 10)) {
      setError("ageError", "Please make sure the age range is valid.");
      valid = false;
    }

    if (gradeFrom !== null && gradeFrom !== undefined) {
      document.getElementById("gradeFrom").value = gradeFrom;
    }
    if (gradeTo !== null && gradeTo !== undefined) {
      document.getElementById("gradeTo").value = gradeTo;
    }
    if (ageFrom !== null) {
      document.getElementById("ageFrom").value = ageFrom;
    }
    if (ageTo !== null) {
      document.getElementById("ageTo").value = ageTo;
    }

    if (!file) {
      setError("fileError", "Please upload your lesson plan.");
      valid = false;
    } else {
      var allowed = [".pdf", ".docx", ".txt"];
      var filename = file.name.toLowerCase();
      var allowedType = allowed.some(function (ext) {
        return filename.endsWith(ext);
      });
      if (!allowedType) {
        setError("fileError", "Please upload a PDF, DOCX, or TXT file.");
        valid = false;
      }
      if (file.size > 20 * 1024 * 1024) {
        setError("fileError", "The file is too large. Please upload a file smaller than 20 MB.");
        valid = false;
      }
    }

    return valid;
  }

  function uploadForm() {
    var subjects = getSelectedSubjects();
    var customSubject = document.getElementById("subjectOtherCheckbox") && document.getElementById("subjectOtherCheckbox").checked ? subjectOtherInput.value.trim() : "";
    var country = countrySelect.value;
    var countryOtherText = country === "Other" ? countryOtherInput.value.trim() : "";
    var customCountry = country === "Other" ? countryOtherText : "";
    var upload = function () {
      var formData = new FormData();
      formData.append("country", customCountry || country);
      if (customCountry) {
        formData.append("countryOther", customCountry);
      }
      subjects.forEach(function (subject) {
        formData.append("subjects[]", subject);
      });
      if (customSubject) {
        formData.append("subjectOther", customSubject);
      }
      formData.append("ageFrom", document.getElementById("ageFrom").value);
      formData.append("ageTo", document.getElementById("ageTo").value);
      formData.append("gradeFrom", document.getElementById("gradeFrom").value);
      formData.append("gradeTo", document.getElementById("gradeTo").value);
      formData.append("specifics", document.getElementById("specifics").value.trim());
      formData.append("lessonPlan", fileInput.files[0]);

      fetch("/upload", {
        method: "POST",
        body: formData
      })
        .then(function (response) {
          if (!response.ok) {
            throw new Error("Upload failed");
          }
          return response.json();
        })
        .then(function () {
          window.location.href = "first-analysis-and-suggestions.html";
        })
        .catch(function () {
          setError("fileError", "The upload failed. Please try again.");
        });
    };

    var customCountry = countrySelect.value === "Other" ? countryOtherInput.value.trim() : "";
    var saveTasks = [];

    if (customSubject && currentSubjects.indexOf(customSubject) === -1) {
      saveTasks.push(
        saveCustomSubject(customSubject).then(function () {
          if (currentSubjects.indexOf(customSubject) === -1) {
            currentSubjects.push(customSubject);
          }
        })
      );
    }

    if (customCountry && currentCountries.indexOf(customCountry) === -1) {
      saveTasks.push(
        saveCustomCountry(customCountry).then(function () {
          if (currentCountries.indexOf(customCountry) === -1) {
            currentCountries.push(customCountry);
          }
        })
      );
    }

    if (saveTasks.length) {
      Promise.all(saveTasks)
        .then(function () {
          upload();
        })
        .catch(function () {
          upload();
        });
    } else {
      upload();
    }
  }

  fileDropzone.addEventListener("click", function () {
    fileInput.click();
  });

  fileDropzone.addEventListener("dragover", function (event) {
    event.preventDefault();
    fileDropzone.classList.add("drag-over");
  });

  fileDropzone.addEventListener("dragleave", function () {
    fileDropzone.classList.remove("drag-over");
  });

  fileDropzone.addEventListener("drop", function (event) {
    event.preventDefault();
    fileDropzone.classList.remove("drag-over");
    var droppedFiles = event.dataTransfer.files;
    if (droppedFiles.length) {
      fileInput.files = droppedFiles;
      updateFileDisplay();
    }
  });

  countrySelect.addEventListener("change", toggleCountryOther);
  countryOtherInput.addEventListener("input", updateAddCountryButton);
  fileInput.addEventListener("change", updateFileDisplay);
  subjectOtherInput.addEventListener("input", updateAddSubjectButton);
  document.getElementById("gradeFrom").addEventListener("input", handleNumericInput);
  document.getElementById("gradeTo").addEventListener("input", handleNumericInput);
  document.getElementById("ageFrom").addEventListener("input", handleNumericInput);
  document.getElementById("ageTo").addEventListener("input", handleNumericInput);

  addCountryButton.addEventListener("click", function () {
    var customCountry = countryOtherInput.value.trim();
    clearError("countryError");
    if (!customCountry) {
      setError("countryError", "Please specify your other country before adding it.");
      return;
    }

    saveCustomCountry(customCountry)
      .then(function () {
        if (currentCountries.indexOf(customCountry) === -1) {
          currentCountries.push(customCountry);
        }
        populateSelect(currentCountries);
        countrySelect.value = customCountry;
        toggleCountryOther();
        countryOtherInput.value = "";
      })
      .catch(function () {
        setError("countryError", "Unable to save the country. Please try again.");
      });
  });

  addSubjectButton.addEventListener("click", function () {
    var customSubject = subjectOtherInput.value.trim();
    clearError("subjectsError");
    if (!customSubject) {
      setError("subjectsError", "Please specify your other subject before adding it.");
      return;
    }

    saveCustomSubject(customSubject)
      .then(function () {
        if (currentSubjects.indexOf(customSubject) === -1) {
          currentSubjects.push(customSubject);
        }
        populateSubjects(currentSubjects);
        var newCheckbox = Array.from(document.querySelectorAll("input[name='subjects']")).find(function (input) {
          return input.value === customSubject;
        });
        if (newCheckbox) {
          newCheckbox.checked = true;
        }
        subjectOtherInput.value = "";
        updateAddSubjectButton();
      })
      .catch(function () {
        setError("subjectsError", "Unable to save the subject. Please try again.");
      });
  });

  continueButton.addEventListener("click", function () {
    if (!validateForm()) {
      return;
    }
    uploadForm();
  });

  moreInfoButton.addEventListener("click", function () {
    window.location.href = "info.html";
  });

  loadConfig();
});
