// ============================================================
// SMARTCAR AI — APPLICATION CONTROLLER
// app.js
// ============================================================

console.log("🔥 SMARTCAR AI LOADED 🔥");

// ============================================================
// SMARTCAR AI THEME SYSTEM
// ============================================================

(function () {
    const savedTheme = localStorage.getItem("smartcar-theme");
    const systemDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
    const initialTheme = savedTheme || (systemDark ? "dark" : "dark"); // Default to sleek dark automotive aesthetic
    document.documentElement.setAttribute("data-theme", initialTheme);
})();

document.addEventListener("DOMContentLoaded", function () {

    // ----------------------------------------------------
    // LIGHT / DARK MODE TOGGLE
    // ----------------------------------------------------
    const themeToggle = document.getElementById("themeToggle");
    const themeIcon = document.getElementById("themeIcon");

    function updateThemeIcon() {
        const currentTheme = document.documentElement.getAttribute("data-theme");
        if (themeIcon) {
            themeIcon.textContent = currentTheme === "dark" ? "☀️" : "🌙";
        }
    }

    if (themeToggle) {
        updateThemeIcon();
        themeToggle.addEventListener("click", function () {
            const currentTheme = document.documentElement.getAttribute("data-theme");
            const newTheme = currentTheme === "dark" ? "light" : "dark";
            document.documentElement.setAttribute("data-theme", newTheme);
            localStorage.setItem("smartcar-theme", newTheme);
            updateThemeIcon();
        });
    }

    // ----------------------------------------------------
    // AUTOMOTIVE NAVIGATION CONTROLS
    // ----------------------------------------------------
    function setActiveNav(btn) {
        document.querySelectorAll(".navbar .nav-link").forEach(el => el.classList.remove("active"));
        if (btn) btn.classList.add("active");
    }

    // HOME: Return to showroom hero framing
    const homeBtn = document.getElementById("navHomeBtn");
    if (homeBtn) {
        homeBtn.addEventListener("click", function (e) {
            e.preventDefault();
            setActiveNav(this);
            if (window.smartCarExperience) {
                const ui = window.smartCarExperience.getUI();
                if (ui && typeof ui.closeConfigurator === "function") {
                    ui.closeConfigurator();
                }
                const cam = window.smartCarExperience.getCameraController();
                if (cam && typeof cam.reset === "function") {
                    cam.reset();
                }
            }
        });
    }

    // EXPLORE: Switch to 360° vehicle inspection orbit
    const exploreBtn = document.getElementById("navExploreBtn");
    if (exploreBtn) {
        exploreBtn.addEventListener("click", function (e) {
            e.preventDefault();
            setActiveNav(this);
            if (window.smartCarExperience) {
                if (typeof window.smartCarExperience.startInspection === "function") {
                    window.smartCarExperience.startInspection();
                } else {
                    const ui = window.smartCarExperience.getUI();
                    if (ui && typeof ui.showInspectionMode === "function") {
                        ui.showInspectionMode();
                    }
                    const cam = window.smartCarExperience.getCameraController();
                    if (cam && typeof cam.transitionToInspection === "function") {
                        cam.transitionToInspection();
                    }
                }
            }
        });
    }

    // VALUATION: Transition into vehicle configuration state
    const valuationBtn = document.getElementById("navValuationBtn") || document.getElementById("navValuationLink");
    if (valuationBtn) {
        valuationBtn.addEventListener("click", function (e) {
            e.preventDefault();
            setActiveNav(this);
            if (window.smartCarExperience) {
                if (typeof window.smartCarExperience.startConfiguring === "function") {
                    window.smartCarExperience.startConfiguring();
                } else {
                    const ui = window.smartCarExperience.getUI();
                    if (ui && typeof ui.triggerConfigure === "function") {
                        ui.triggerConfigure();
                    }
                }
            }
        });
    }
});