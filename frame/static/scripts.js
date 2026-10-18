document.getElementById("start").addEventListener("input", function (e) {
  let timeVal = e.target.value;

  if (timeVal) {
    let [hours, minutes] = timeVal.split(":");

    if (minutes != "00") {
      e.target.value = `${hours}:00`;
    }
  }
});

function updateDiskSpace() {
  // Update HTML text
  document.getElementById("free-space").textContent = `${free} GB`;
  document.getElementById("disk-details").textContent =
    `${used} GB used of ${total} GB`;

  // Update progress bar (showing used space)
  let usedPercentage = 100 - (free / total) * 100;
  document.getElementById("disk-bar").value = usedPercentage.toFixed(1);
}

// -----------------------------------
// Image Modal
// -----------------------------------

function openImageModal(filename, imageUrl) {
  // Set image
  document.getElementById("modal-image").src = imageUrl;

  // Set filename
  document.getElementById("modal-filename").textContent = filename;

  // Set hidden form values
  document.getElementById("select-filename").value = filename;

  document.getElementById("remove-filename").value = filename;

  // Set confirmation text
  document.getElementById("confirmation-filename").textContent = filename;

  // Show normal actions
  document.getElementById("action-buttons").classList.remove("hidden");

  // Hide confirmation
  document.getElementById("remove-confirmation").classList.add("hidden");

  // Show modal
  document.getElementById("image-modal").style.display = "flex";
}

function showRemoveConfirmation() {
  // Hide Select / Remove / Cancel buttons
  document.getElementById("action-buttons").classList.add("hidden");

  // Show confirmation
  document.getElementById("remove-confirmation").classList.remove("hidden");
}

function cancelRemove() {
  // Show normal actions
  document.getElementById("action-buttons").classList.remove("hidden");

  // Hide confirmation
  document.getElementById("remove-confirmation").classList.add("hidden");
}

function closeModal(event) {
  // If called from the background click,
  // only close when the background itself was clicked.
  if (event && event.target !== event.currentTarget) {
    return;
  }

  document.getElementById("image-modal").style.display = "none";
}

// Close modal with Escape key
document.addEventListener("keydown", function (event) {
  if (event.key === "Escape") {
    closeModal();
  }
});

updateDiskSpace();

// -----------------------------------
// Dark Mode
// -----------------------------------
const themeToggle = document.getElementById("theme-toggle");
const themeIcon = document.getElementById("theme-icon");
const themeLabel = document.getElementById("theme-label");

function updateThemeButton() {
  const dark = document.documentElement.classList.contains("dark");

  themeIcon.textContent = dark ? "☀" : "☾";
  themeLabel.textContent = dark ? "Light mode" : "Dark mode";

  themeToggle.setAttribute(
    "aria-label",
    dark ? "Switch to light mode" : "Switch to dark mode",
  );
}

function setTheme(theme) {
  document.documentElement.classList.toggle("dark", theme === "dark");

  localStorage.setItem("theme", theme);
  updateThemeButton();
}

themeToggle.addEventListener("click", () => {
  const dark = document.documentElement.classList.contains("dark");

  setTheme(dark ? "light" : "dark");
});

updateThemeButton();

// --------------
// Alert Bar
// --------------

function handleUrlAlerts() {
  let params = new URLSearchParams(window.location.search);
  let alertType = params.get("alert_type");
  let alertTitle = params.get("alert_title");
  let alertText = params.get("alert_text");
  let alertTimeoutStr = params.get("alert_timeout");

  if (alertType && (alertTitle || alertText)) {
    let alertBar = document.getElementById("alert-bar");
    let titleElem = document.getElementById("alert-title");
    let textElem = document.getElementById("alert-text");
    let closeBtn = document.getElementById("alert-close");

    titleElem.textContent = alertTitle || "";
    textElem.textContent = alertText || "";

    alertBar.classList.remove("hidden", "alert-error", "alert-success");
    if (alertType === "error") {
      alertBar.classList.add("alert-error");
    } else if (alertType === "success") {
      alertBar.classList.add("alert-success");
    } else {
      alertBar.classList.add("alert-message");
    }

    alertBar.classList.remove("hidden");

    // timeout
    let timeoutMs = alertTimeoutStr ? parseInt(alertTimeoutStr) * 1000 : 5000;
    if (!isNaN(timeoutMs)) {
      setTimeout(() => {
        alertBar.classList.add("hidden");
      }, timeoutMs);
    }

    closeBtn.addEventListener("click", () => {
      alertBar.classList.add("hidden");
    });
  }
}

handleUrlAlerts();
