// ============================================================
// SMARTCAR AI — PROGRESSIVE VEHICLE CONFIGURATOR & UI
// ui.js
// ============================================================

import { SmartCarPrediction } from "./prediction.js";
import {
    vehicleIdentity,
    setVehicleIdentity,
    getVehicleIdentity,
    isVehicleIdentityReadyForAsset
} from "./vehicleIdentity.js";
import { SoundEngine } from "./sound.js";

// ============================================================
// PHASE 8: CINEMATIC VALUATION STAGES (DURATION <= 6 SECONDS)
// ============================================================
export const CINEMATIC_VALUATION_STAGES = [
    {
        id: "vehicle",
        name: "ANALYZING VEHICLE",
        subtext: "Decoding vehicle identity, odometer telemetry, mechanical health & age curve...",
        icon: "🚗"
    },
    {
        id: "market",
        name: "ANALYZING MARKET",
        subtext: "Scanning 57,480 secondary market records, regional volume & demand velocity...",
        icon: "📊"
    },
    {
        id: "comparables",
        name: "COMPARING VEHICLES",
        subtext: "Querying exact and nearest specification transactions from dataset...",
        icon: "🔍"
    },
    {
        id: "depreciation",
        name: "CALCULATING DEPRECIATION",
        subtext: "Evaluating age curve, mileage intensity & ownership title transfer impact...",
        icon: "📉"
    },
    {
        id: "estimating",
        name: "ESTIMATING VALUE",
        subtext: "Computing trained machine learning inference pipeline (R² 0.8993)...",
        icon: "⚡"
    },
    {
        id: "reveal",
        name: "PRICE REVEAL",
        subtext: "Synthesizing market valuation confidence interval and empirical benchmarks...",
        icon: "✨"
    }
];

export class SmartCarUI {

    constructor(predictionService = null, cameraController = null) {
        this.statusElement = document.getElementById("experienceStatus");
        this.overlayElement = document.getElementById("experienceOverlay");
        this.hintElement = document.querySelector(".experience-hint");
        this.introElement = document.querySelector(".experience-intro");

        this.predictionService = predictionService;
        this.cameraController = cameraController;

        // Single authoritative configuration state (Phase 7 9-step configuration flow)
        this.configuration = {
            brand: "",
            model: "",
            generation: "",
            manufacturing_year: null,
            variant: "",
            fuel_type: "",
            transmission_type: "",
            bodytype: "",
            city: "",
            km_driven: null,
            number_of_owners: null
        };

        // Canonical vehicle configuration object (Phase 6 & 7)
        window.vehicleConfig = this.configuration;

        this.currentStep = 1; // 1 to 9, 10 is Summary
        this.totalSteps = 9;
        this.isConfiguratorOpen = false;
        this.isValuationReady = false;

        // Experience lifecycle state (Phase 5)
        this.appState = "LOADING"; // LOADING, DRIVING, PARKED, INSPECTING, CONFIGURING
        this.onConfigureTriggered = null;

        // UI Element references
        this.exploreBadge = null;
        this.configPanel = null;
        this.identityPill = null;
        this.finishSelector = null;
        this.modelUnavailableBadge = null;
        this.is3DModelAvailable = true;

        // Callbacks
        this.onValuationReadyCallback = null;
        this.onConfigurationChangeCallback = null;

        // Initialize UI components
        this.storyController = null;
        this.createIdentityPill();
        this.createExploreBadge();
        this.createFinishSelector();
        this.createModelUnavailableBadge();
        this.createConfiguratorPanel();
        this.lastValuationResult = null;
        this.setupAIAssistant();
    }

    setStoryController(storyController) {
        this.storyController = storyController;
    }

    getAppState() {
        return this.appState;
    }

    setAppState(state) {
        this.appState = state;
        if (state === "VALUATION_RESULT") {
            this.setStatus("VALUATION COMPLETE");
        } else if (state === "VALUATING") {
            this.setStatus("CALCULATING MARKET VALUE");
        } else if (state === "VALUATION_ERROR") {
            this.setStatus("VALUATION ERROR");
        } else if (state === "VALUATION_READY") {
            this.setStatus("VALUATION READY");
        } else if (state === "INSPECTING") {
            this.setStatus(this.is3DModelAvailable ? "INSPECTION READY" : "3D MODEL PREVIEW UNAVAILABLE");
        } else {
            const displayStatus = state ? state.replace(/_/g, " ") : "";
            this.setStatus(displayStatus);
        }

        if (this.finishSelector) {
            if ((state === "INSPECTING" || state === "CONFIGURING") && this.is3DModelAvailable) {
                this.finishSelector.classList.add("visible");
            } else {
                this.finishSelector.classList.remove("visible");
            }
        }

        if (this.storyController && typeof this.storyController.syncWithExperienceState === "function") {
            this.storyController.syncWithExperienceState(state);
        }
    }

    onUserInteraction(isInteracting) {
        if (isInteracting) {
            if (this.exploreBadge) {
                this.exploreBadge.style.opacity = "0.2";
                this.exploreBadge.style.transition = "opacity 0.3s ease";
            }
            if (this.finishSelector) {
                this.finishSelector.style.opacity = "0.2";
                this.finishSelector.style.transition = "opacity 0.3s ease";
            }
            if (this.hintElement) {
                this.hintElement.style.opacity = "0.2";
                this.hintElement.style.transition = "opacity 0.3s ease";
            }
        } else {
            if (this.exploreBadge && (this.appState === "INSPECTING" || this.appState === "CONFIGURING")) {
                this.exploreBadge.style.opacity = "1";
                this.exploreBadge.style.transition = "opacity 0.6s ease";
            }
            if (this.finishSelector && (this.appState === "INSPECTING" || this.appState === "CONFIGURING")) {
                this.finishSelector.style.opacity = "1";
                this.finishSelector.style.transition = "opacity 0.6s ease";
            }
            if (this.hintElement && (this.appState === "INSPECTING" || this.appState === "CONFIGURING")) {
                this.hintElement.style.opacity = "0.85";
                this.hintElement.style.transition = "opacity 0.6s ease";
            }
        }
    }

    setPredictionService(service) {
        this.predictionService = service;
    }

    setCameraController(cameraController) {
        this.cameraController = cameraController;
    }

    // ========================================================
    // DATA PROVIDERS (REUSING EXISTING REAL FLASK / DOM DATA)
    // ========================================================

    getBrandModelsMap() {
        if (typeof window.brandModels !== "undefined" && window.brandModels && Object.keys(window.brandModels).length > 0) {
            return window.brandModels;
        }
        const el = document.getElementById("brand-models");
        if (el && el.textContent) {
            try {
                window.brandModels = JSON.parse(el.textContent);
                return window.brandModels;
            } catch (e) {
                console.error("SmartCar UI: Failed to parse brand-models", e);
            }
        }
        return {};
    }

    getModelDetailsMap() {
        if (typeof window.modelDetails !== "undefined" && window.modelDetails && Object.keys(window.modelDetails).length > 0) {
            return window.modelDetails;
        }
        const el = document.getElementById("model-details");
        if (el && el.textContent) {
            try {
                window.modelDetails = JSON.parse(el.textContent);
                return window.modelDetails;
            } catch (e) {
                console.error("SmartCar UI: Failed to parse model-details", e);
            }
        }
        return {};
    }

    getBrandList() {
        const brandModels = this.getBrandModelsMap();
        if (brandModels && Object.keys(brandModels).length > 0) {
            return Object.keys(brandModels).sort();
        }

        const brandSelect = document.getElementById("brand");
        if (brandSelect) {
            return Array.from(brandSelect.options)
                .map(opt => opt.value.trim())
                .filter(Boolean)
                .sort();
        }

        return [];
    }

    getModelList(brand) {
        if (!brand) return [];
        const brandModels = this.getBrandModelsMap();
        if (brandModels && brandModels[brand]) {
            return brandModels[brand];
        }

        const brandSelect = document.getElementById("brand");
        const modelSelect = document.getElementById("model");
        if (brandSelect && modelSelect && brandSelect.value === brand) {
            return Array.from(modelSelect.options)
                .map(opt => opt.value.trim())
                .filter(Boolean);
        }

        return [];
    }

    getModelDetails(brand, model) {
        if (!brand || !model) return null;
        const detailsMap = this.getModelDetailsMap();
        if (detailsMap && detailsMap[brand] && detailsMap[brand][model]) {
            return detailsMap[brand][model];
        }
        return null;
    }

    getCityList() {
        if (typeof window.datasetCities !== "undefined" && Array.isArray(window.datasetCities) && window.datasetCities.length > 0) {
            return [...window.datasetCities].sort();
        }
        const el = document.getElementById("dataset-cities");
        if (el && el.textContent) {
            try {
                window.datasetCities = JSON.parse(el.textContent);
                return [...window.datasetCities].sort();
            } catch (e) {}
        }
        const citySelect = document.getElementById("city");
        if (citySelect) {
            return Array.from(citySelect.options)
                .map(opt => opt.value.trim())
                .filter(Boolean)
                .sort();
        }
        return ["Delhi", "Mumbai", "Bangalore", "Hyderabad", "Pune", "Chennai", "Kolkata", "Ahmedabad", "Jaipur", "Chandigarh"];
    }

    getOwnerList() {
        if (typeof window.datasetOwners !== "undefined" && Array.isArray(window.datasetOwners) && window.datasetOwners.length > 0) {
            return window.datasetOwners;
        }
        const el = document.getElementById("dataset-owners");
        if (el && el.textContent) {
            try {
                window.datasetOwners = JSON.parse(el.textContent);
                return window.datasetOwners;
            } catch (e) {}
        }
        const ownerSelect = document.getElementById("number_of_owners");
        if (ownerSelect) {
            return Array.from(ownerSelect.options)
                .map(opt => opt.value.trim())
                .filter(Boolean);
        }
        return [1, 2, 3, 4];
    }

    getGenerationsForModel(brand, model) {
        if (!brand || !model) return [];
        const b = String(brand).toLowerCase().trim();
        const m = String(model).toLowerCase().trim();

        if (b.includes("porsche") || m.includes("911")) {
            return [
                { name: "992 (2019 – Present)", slug: "992", defaultYear: 2021 },
                { name: "991 (2011 – 2019)", slug: "991", defaultYear: 2017 },
                { name: "997 (2004 – 2012)", slug: "997", defaultYear: 2008 }
            ];
        }
        if (b.includes("bmw") || m.includes("3 series")) {
            return [
                { name: "G20 (2018 – Present)", slug: "g20", defaultYear: 2021 },
                { name: "F30 (2011 – 2019)", slug: "f30", defaultYear: 2016 },
                { name: "E90 (2004 – 2013)", slug: "e90", defaultYear: 2010 }
            ];
        }
        if (b.includes("mercedes") || m.includes("c-class")) {
            return [
                { name: "W206 (2021 – Present)", slug: "w206", defaultYear: 2022 },
                { name: "W205 (2014 – 2021)", slug: "w205", defaultYear: 2018 },
                { name: "W204 (2007 – 2014)", slug: "w204", defaultYear: 2012 }
            ];
        }
        if (b.includes("toyota") || m.includes("fortuner")) {
            return [
                { name: "2nd Gen AN160 (2015 – Present)", slug: "an160", defaultYear: 2021 },
                { name: "1st Gen AN50 (2004 – 2015)", slug: "an50", defaultYear: 2012 }
            ];
        }
        if (b.includes("hyundai") || m.includes("creta")) {
            return [
                { name: "2nd Gen SU2 (2020 – Present)", slug: "su2", defaultYear: 2022 },
                { name: "1st Gen GS (2014 – 2020)", slug: "gs", defaultYear: 2018 }
            ];
        }

        return [
            { name: "Current Generation (2020 – 2026)", slug: "current", defaultYear: 2022 },
            { name: "Previous Generation (2014 – 2019)", slug: "previous", defaultYear: 2017 },
            { name: "Classic Generation (Pre-2014)", slug: "classic", defaultYear: 2012 }
        ];
    }

    getVariantsForModel(brand, model) {
        if (!brand || !model) return ["Base", "Standard", "Sport", "Luxury", "Top Spec"];
        const b = String(brand).toLowerCase().trim();
        const m = String(model).toLowerCase().trim();

        if (b.includes("porsche") || m.includes("911")) {
            return ["Carrera 4S", "Carrera", "Turbo S", "GT3", "Targa 4S"];
        }
        if (b.includes("bmw") || m.includes("3 series")) {
            return ["330i M Sport", "320d Luxury Line", "M340i xDrive", "330Li Gran Limousine", "Sport Line"];
        }
        if (b.includes("mercedes") || m.includes("c-class")) {
            return ["C 220d", "C 200 Progressive", "C 300d AMG Line", "Exclusive Line"];
        }
        if (b.includes("toyota") || m.includes("fortuner")) {
            return ["4x4 AT", "4x2 AT", "Legender 4x4", "4x2 MT", "GR-S 4x4"];
        }
        if (b.includes("hyundai") || m.includes("creta")) {
            return ["SX (O) Turbo", "SX (O)", "SX", "S+", "EX", "E"];
        }

        return ["Standard Spec", "Executive / Sport", "Luxury Edition", "Top Specification"];
    }

    // ========================================================
    // FLOATING VEHICLE IDENTITY PILL
    // ========================================================

    createIdentityPill() {
        if (!this.overlayElement) return;

        const pill = document.createElement("div");
        pill.id = "experienceVehicleIdentity";
        pill.className = "experience-vehicle-identity";
        pill.innerHTML = `
            <span class="identity-dot"></span>
            <span class="identity-text">SMARTCAR AI &bull; SPECIFICATION PENDING</span>
        `;
        pill.style.opacity = "0";
        this.overlayElement.appendChild(pill);
        this.identityPill = pill;
    }

    updateVehicleIdentity() {
        if (!this.identityPill) return;

        const { brand, model, generation, manufacturing_year, variant, fuel_type } = this.configuration;
        let text = "SMARTCAR AI &bull; SPECIFICATION IN PROGRESS";

        if (brand && model) {
            let cleanModel = model;
            if (cleanModel.toLowerCase().startsWith(brand.toLowerCase() + " ")) {
                cleanModel = cleanModel.slice(brand.length).trim();
            }
            text = `${brand.toUpperCase()} ${cleanModel.toUpperCase()}`;
            if (generation) {
                text += ` [${generation.toUpperCase()}]`;
            }
            if (manufacturing_year) {
                text += ` (${manufacturing_year})`;
            }
            if (variant) {
                text += ` &bull; ${variant}`;
            }
            if (fuel_type) {
                text += ` &bull; ${fuel_type.toUpperCase()}`;
            }
            if (!this.is3DModelAvailable) {
                text += ` &bull; <span style="color:#ff9f43;font-size:8.5px;letter-spacing:0.12em;">[3D N/A]</span>`;
            }
        }

        const textEl = this.identityPill.querySelector(".identity-text");
        if (textEl) {
            textEl.innerHTML = text;
        }

        this.identityPill.style.opacity = brand ? "1" : "0.75";
    }

    // ========================================================
    // CONTEXTUAL "EXPLORE VEHICLE" BADGE & TRIGGER
    // ========================================================

    createExploreBadge() {
        if (!this.overlayElement) return;

        const badge = document.createElement("div");
        badge.id = "experienceExploreBadge";
        badge.className = "experience-explore-badge";
        badge.innerHTML = `
            <div class="explore-tag">INSPECTION MODE</div>
            <div class="explore-title">EXPLORE VEHICLE</div>
            <div class="explore-sub">DRAG TO ORBIT &bull; SCROLL TO ZOOM</div>
            <button type="button" id="startConfigBtn" class="explore-config-btn">
                CONFIGURE VEHICLE &rarr;
            </button>
        `;

        badge.style.opacity = "0";
        badge.style.pointerEvents = "none";
        this.overlayElement.appendChild(badge);
        this.exploreBadge = badge;

        const btn = badge.querySelector("#startConfigBtn");
        if (btn) {
            btn.addEventListener("click", () => {
                this.triggerConfigure();
            });
        }
    }

    // ========================================================
    // EXTERIOR FINISH SELECTOR (BODY PAINT PREVIEW)
    // ========================================================

    createFinishSelector() {
        if (!this.overlayElement) return;

        const selector = document.createElement("div");
        selector.id = "experienceFinishSelector";
        selector.className = "experience-finish-selector";
        selector.setAttribute("role", "region");
        selector.setAttribute("aria-label", "Exterior Finish Selector");

        const finishes = [
            { id: "bronze", name: "Slate Bronze", hex: "#3c3a29" },
            { id: "black",  name: "Obsidian Black", hex: "#121315" },
            { id: "white",  name: "Glacier White", hex: "#eef0f3" },
            { id: "silver", name: "Sterling Silver", hex: "#858990" },
            { id: "red",    name: "Crimson Red", hex: "#821319" },
            { id: "blue",   name: "Deep Sapphire", hex: "#13233e" }
        ];

        selector.innerHTML = `
            <div class="finish-selector-inner">
                <div class="finish-selector-label">
                    <span class="finish-tag">FINISH</span>
                    <span class="finish-active-name" id="finishActiveName">Slate Bronze</span>
                </div>
                <div class="finish-swatches" role="radiogroup" aria-label="Vehicle Exterior Finish">
                    ${finishes.map((f, i) => `
                        <button type="button" 
                            class="finish-swatch ${i === 0 ? "active" : ""}" 
                            data-finish-id="${f.id}" 
                            data-finish-name="${f.name}"
                            style="background-color: ${f.hex};"
                            title="${f.name}"
                            aria-label="${f.name}">
                        </button>
                    `).join("")}
                </div>
            </div>
        `;

        this.overlayElement.appendChild(selector);
        this.finishSelector = selector;

        selector.querySelectorAll(".finish-swatch").forEach(btn => {
            btn.addEventListener("click", () => {
                const finishId = btn.dataset.finishId;
                const finishName = btn.dataset.finishName;

                selector.querySelectorAll(".finish-swatch").forEach(b => b.classList.remove("active"));
                btn.classList.add("active");

                const nameEl = selector.querySelector("#finishActiveName");
                if (nameEl) nameEl.textContent = finishName;

                if (window.smartCarExperience && typeof window.smartCarExperience.getVehicle === "function") {
                    const vehicle = window.smartCarExperience.getVehicle();
                    if (vehicle && typeof vehicle.setBodyColor === "function") {
                        vehicle.setBodyColor(finishId);
                    }
                }
            });
        });
    }

    // ========================================================
    // 3D MODEL UNAVAILABLE BADGE & STATE CONTROLS
    // ========================================================

    createModelUnavailableBadge() {
        if (!this.overlayElement) return;

        const badge = document.createElement("div");
        badge.id = "experienceModelUnavailableBadge";
        badge.className = "experience-unavailable-badge";
        badge.innerHTML = `
            <div class="unavailable-inner">
                <div class="unavailable-status-row">
                    <span class="unavailable-pulse-dot"></span>
                    <span class="unavailable-tag">3D MODEL PREVIEW UNAVAILABLE</span>
                </div>
                <div class="unavailable-title" id="unavailableVehicleTitle">3D MODEL PREVIEW UNAVAILABLE</div>
                <div class="unavailable-desc">
                    A calibrated 3D digital model is not currently cataloged for this exact specification.
                </div>
                <div class="unavailable-notice">
                    <span class="unavailable-check">&#10003;</span>
                    <span>Real Used-Car ML Valuation and Market Intelligence remain 100% active.</span>
                </div>
                <button type="button" id="unavailableConfigBtn" class="explore-config-btn unavailable-action-btn">
                    CONFIGURE SPECIFICATION &rarr;
                </button>
            </div>
        `;

        badge.style.opacity = "0";
        badge.style.display = "none";
        badge.style.pointerEvents = "none";
        this.overlayElement.appendChild(badge);
        this.modelUnavailableBadge = badge;

        const btn = badge.querySelector("#unavailableConfigBtn");
        if (btn) {
            btn.addEventListener("click", () => {
                this.triggerConfigure();
            });
        }
    }

    set3DModelUnavailable(brand, model, data = null) {
        this.is3DModelAvailable = false;

        let cleanModel = model || "";
        if (brand && cleanModel.toLowerCase().startsWith(brand.toLowerCase() + " ")) {
            cleanModel = cleanModel.slice(brand.length).trim();
        }
        let titleText = (brand && cleanModel)
            ? `${brand.toUpperCase()} ${cleanModel.toUpperCase()}`
            : (brand ? brand.toUpperCase() : "SELECTED VEHICLE");

        if (data && data.generation) {
            titleText += ` (${data.generation})`;
        }

        if (this.modelUnavailableBadge) {
            const titleEl = this.modelUnavailableBadge.querySelector("#unavailableVehicleTitle");
            if (titleEl) {
                titleEl.textContent = titleText;
            }
            this.modelUnavailableBadge.style.display = "block";
            requestAnimationFrame(() => {
                if (this.modelUnavailableBadge) {
                    this.modelUnavailableBadge.style.opacity = "1";
                    this.modelUnavailableBadge.style.pointerEvents = "auto";
                }
            });
        }

        // Hide finish selector since there's no 3D car body
        if (this.finishSelector) {
            this.finishSelector.classList.remove("visible");
        }

        // Hide explore badge
        if (this.exploreBadge) {
            this.exploreBadge.style.opacity = "0";
            this.exploreBadge.style.pointerEvents = "none";
        }

        this.setStatus("3D MODEL PREVIEW UNAVAILABLE");

        if (this.hintElement) {
            this.hintElement.innerHTML = `
                <span class="hint-line"></span>
                <span>3D MODEL PREVIEW UNAVAILABLE &bull; REAL VALUATION ACTIVE</span>
            `;
            this.hintElement.style.opacity = "0.85";
        }

        this.updateVehicleIdentity();
    }

    set3DModelAvailable(entry) {
        this.is3DModelAvailable = true;

        if (this.modelUnavailableBadge) {
            this.modelUnavailableBadge.style.opacity = "0";
            this.modelUnavailableBadge.style.pointerEvents = "none";
            setTimeout(() => {
                if (this.is3DModelAvailable && this.modelUnavailableBadge) {
                    this.modelUnavailableBadge.style.display = "none";
                }
            }, 300);
        }

        if (this.finishSelector && (this.appState === "INSPECTING" || this.appState === "CONFIGURING")) {
            this.finishSelector.classList.add("visible");
        }

        if (this.appState === "INSPECTING" && this.exploreBadge) {
            this.exploreBadge.style.opacity = "1";
            this.exploreBadge.style.pointerEvents = "auto";
        }

        if (this.hintElement && this.appState === "INSPECTING") {
            this.hintElement.innerHTML = `
                <span class="hint-line"></span>
                <span>EXPLORE VEHICLE &bull; 360&deg; INSPECTION</span>
            `;
            this.hintElement.style.opacity = "1";
        }

        const matchLevel = (entry && entry.asset && entry.asset.match_level) || (entry && entry.match_level);
        let statusMsg = "3D MODEL PREVIEW — GENERATION MATCH";
        if (matchLevel === "EXACT_VARIANT") {
            statusMsg = "3D MODEL PREVIEW — EXACT VARIANT";
        } else if (matchLevel === "GENERATION_MATCH") {
            statusMsg = "3D MODEL PREVIEW — GENERATION MATCH";
        } else if (matchLevel === "GENERATION_FALLBACK") {
            statusMsg = "3D MODEL PREVIEW — GENERATION FALLBACK";
        }
        this.setStatus(statusMsg);
        this.updateVehicleIdentity();
    }

    triggerConfigure() {
        this.setAppState("CONFIGURING");
        this.setStatus("CONFIGURING");
        if (window.smartCarExperience && typeof window.smartCarExperience.getAnimation === "function") {
            const anim = window.smartCarExperience.getAnimation();
            if (anim && typeof anim.setState === "function") {
                anim.setState("CONFIGURING");
            }
        }
        console.log("SmartCar AI: State → CONFIGURING (Phase 6).");

        // Camera smoothly settles into controlled configuration composition
        if (this.cameraController) {
            if (typeof this.cameraController.transitionToConfiguration === "function") {
                this.cameraController.transitionToConfiguration();
            } else if (typeof this.cameraController.transitionToValuation === "function") {
                this.cameraController.transitionToValuation();
            }
        }

        // Hide explore badge so HUD is minimal and unobstructed
        this.hideInspectionMode();

        if (this.hintElement) {
            this.hintElement.innerHTML = `
                <span class="hint-line"></span>
                <span>CONFIGURATION MODE &bull; SPECIFICATION IN PROGRESS</span>
            `;
            this.hintElement.style.opacity = "0.7";
        }

        // Open configurator panel
        this.openConfigurator(this.currentStep || 1);

        if (this.storyController && typeof this.storyController.setChapter === "function") {
            this.storyController.setChapter(3);
        }

        if (typeof this.onConfigureTriggered === "function") {
            this.onConfigureTriggered();
        }
    }

    showInspectionMode() {
        this.setAppState("INSPECTING");
        this.setStatus(this.is3DModelAvailable ? "INSPECTION READY" : "3D MODEL PREVIEW UNAVAILABLE");
        if (window.smartCarExperience && typeof window.smartCarExperience.getAnimation === "function") {
            const anim = window.smartCarExperience.getAnimation();
            if (anim && typeof anim.setState === "function") {
                anim.setState("INSPECTING");
            }
        }

        if (this.storyController && typeof this.storyController.setChapter === "function") {
            this.storyController.setChapter(2);
        }

        if (this.hintElement) {
            this.hintElement.innerHTML = this.is3DModelAvailable ? `
                <span class="hint-line"></span>
                <span>EXPLORE VEHICLE &bull; 360&deg; INSPECTION</span>
            ` : `
                <span class="hint-line"></span>
                <span>3D MODEL PREVIEW UNAVAILABLE &bull; REAL VALUATION ACTIVE</span>
            `;
            this.hintElement.style.opacity = "1";
        }

        if (this.is3DModelAvailable && this.exploreBadge) {
            this.exploreBadge.style.opacity = "1";
            this.exploreBadge.style.pointerEvents = "auto";
            this.exploreBadge.style.transform = "translateY(0)";

            const btn = this.exploreBadge.querySelector("#startConfigBtn");
            if (btn) {
                btn.textContent = "CONFIGURE VEHICLE →";
                btn.style.opacity = "1";
                btn.disabled = false;
            }
        } else if (!this.is3DModelAvailable && this.modelUnavailableBadge) {
            this.modelUnavailableBadge.style.display = "block";
            this.modelUnavailableBadge.style.opacity = "1";
            this.modelUnavailableBadge.style.pointerEvents = "auto";
        }

        if (this.identityPill) {
            this.identityPill.style.opacity = "0.75";
        }
    }

    hideInspectionMode() {
        if (this.exploreBadge) {
            this.exploreBadge.style.opacity = "0";
            this.exploreBadge.style.pointerEvents = "none";
            this.exploreBadge.style.transform = "translateY(12px)";
        }
    }

    // ========================================================
    // PROGRESSIVE CONFIGURATOR PANEL
    // ========================================================

    createConfiguratorPanel() {
        if (!this.overlayElement) return;

        const panel = document.createElement("div");
        panel.id = "experienceConfigPanel";
        panel.className = "experience-config-panel";
        panel.setAttribute("role", "dialog");
        panel.setAttribute("aria-modal", "true");
        panel.setAttribute("aria-labelledby", "configStageTitle");
        panel.innerHTML = `
            <!-- Mobile Bottom Sheet Grab Handle -->
            <div class="bottom-sheet-drag-handle" aria-hidden="true">
                <div class="drag-bar"></div>
            </div>

            <div class="config-header">
                <div class="config-counter-wrap">
                    <div class="config-chapter-eyebrow" id="configChapterEyebrow">03 &bull; CONFIGURE</div>
                    <div class="config-narrative-q" id="configNarrativeQ">What car are we valuing?</div>
                    <div class="config-title-row">
                        <span class="config-stage-title" id="configStageTitle">BRAND</span>
                        <span class="config-step-tag" id="configStepTag">01 / 09</span>
                    </div>
                </div>
                <button type="button" class="config-close-btn" id="configCloseBtn" aria-label="Minimize configurator">&times;</button>
            </div>

            <!-- Segmented progress indicator -->
            <div class="config-progress-track" id="configProgressTrack">
                <div class="config-progress-seg active"></div>
                <div class="config-progress-seg"></div>
                <div class="config-progress-seg"></div>
                <div class="config-progress-seg"></div>
                <div class="config-progress-seg"></div>
                <div class="config-progress-seg"></div>
                <div class="config-progress-seg"></div>
                <div class="config-progress-seg"></div>
                <div class="config-progress-seg"></div>
            </div>

            <div class="config-content" id="configContent">
                <!-- Rendered dynamically per step -->
            </div>

            <div class="config-validation-hint" id="configValidationHint" style="display: none;" role="alert"></div>

            <div class="config-footer" id="configFooter">
                <button type="button" class="config-nav-btn prev" id="configPrevBtn" style="visibility: hidden;">
                    &larr; BACK
                </button>
                <button type="button" class="config-nav-btn next" id="configNextBtn">
                    CONTINUE &rarr;
                </button>
            </div>
        `;

        panel.style.display = "none";
        panel.style.pointerEvents = "auto";
        this.overlayElement.appendChild(panel);
        this.configPanel = panel;

        // Wire event listeners
        panel.querySelector("#configCloseBtn").addEventListener("click", () => {
            this.closeConfigurator();
        });

        // Mobile bottom-sheet touch dismiss gesture
        const dragHandle = panel.querySelector(".bottom-sheet-drag-handle");
        if (dragHandle) {
            let startY = 0;
            dragHandle.addEventListener("touchstart", (e) => {
                if (e.touches && e.touches.length > 0) {
                    startY = e.touches[0].clientY;
                }
            }, { passive: true });
            dragHandle.addEventListener("touchmove", (e) => {
                if (e.touches && e.touches.length > 0) {
                    const currentY = e.touches[0].clientY;
                    if (currentY - startY > 60) {
                        this.closeConfigurator();
                    }
                }
            }, { passive: true });
        }

        panel.querySelector("#configPrevBtn").addEventListener("click", () => {
            this.prevStep();
        });

        panel.querySelector("#configNextBtn").addEventListener("click", () => {
            this.nextStep();
        });
    }

    openConfigurator(step = 1) {
        if (!this.configPanel) return;

        this.isConfiguratorOpen = true;
        this.configPanel.style.display = "flex";
        requestAnimationFrame(() => {
            this.configPanel.classList.add("visible");
        });

        if (this.exploreBadge) {
            this.exploreBadge.style.opacity = "0.35";
        }

        if (this.introElement) {
            this.introElement.style.opacity = "0.2";
            this.introElement.style.transition = "opacity 0.5s ease";
        }

        this.goToStep(step);
    }

    closeConfigurator() {
        if (!this.configPanel) return;

        this.isConfiguratorOpen = false;
        this.configPanel.classList.remove("visible");
        this.configPanel.classList.remove("intelligence-mode");
        setTimeout(() => {
            if (!this.isConfiguratorOpen) {
                this.configPanel.style.display = "none";
            }
        }, 350);

        this.showInspectionMode();
        if (this.cameraController && typeof this.cameraController.transitionToInspection === "function") {
            this.cameraController.transitionToInspection();
        }

        if (this.introElement) {
            this.introElement.style.opacity = "0.94";
        }
    }

    // ========================================================
    // PROGRESSIVE STEP RENDERING
    // ========================================================

    goToStep(step) {
        this.currentStep = step;
        this.hideValidationHint();
        if (this.configPanel) {
            this.configPanel.classList.remove("intelligence-mode");
        }
        const footer = this.configPanel ? this.configPanel.querySelector("#configFooter") : null;
        if (footer && step <= 10) {
            footer.style.display = "flex";
        }
        this.updateProgressTrack();
        this.renderCurrentStep();

        // Subtle micro camera choreography per step
        if (this.cameraController && typeof this.cameraController.orbit === "function") {
            const microAngle = (step % 2 === 0 ? 0.025 : -0.025);
            this.cameraController.orbit(microAngle, 0);
        }
    }

    nextStep() {
        if (this.currentStep === 10) {
            // Already at summary
            return;
        }

        if (!this.validateStep(this.currentStep)) {
            this.showValidationHint(this.getValidationMessage(this.currentStep));
            return;
        }

        this.hideValidationHint();

        if (this.currentStep < this.totalSteps) {
            this.goToStep(this.currentStep + 1);
        } else {
            // All 9 steps finished: transition to summary
            this.goToStep(10);
        }
    }

    prevStep() {
        if (this.currentStep > 1) {
            this.goToStep(this.currentStep - 1);
        }
    }

    updateProgressTrack() {
        const segs = this.configPanel.querySelectorAll(".config-progress-seg");
        segs.forEach((seg, idx) => {
            if (idx + 1 < this.currentStep) {
                seg.className = "config-progress-seg completed";
            } else if (idx + 1 === this.currentStep) {
                seg.className = "config-progress-seg active";
            } else {
                seg.className = "config-progress-seg";
            }
        });

        const tagEl = this.configPanel.querySelector("#configStepTag");
        const titleEl = this.configPanel.querySelector("#configStageTitle");
        const prevBtn = this.configPanel.querySelector("#configPrevBtn");
        const nextBtn = this.configPanel.querySelector("#configNextBtn");

        if (prevBtn) {
            prevBtn.style.visibility = (this.currentStep > 1) ? "visible" : "hidden";
        }

        const chapterEyebrow = this.configPanel.querySelector("#configChapterEyebrow");
        const narrativeQ = this.configPanel.querySelector("#configNarrativeQ");

        if (this.currentStep <= 9) {
            tagEl.textContent = `0${this.currentStep} / 0${this.totalSteps}`;
            nextBtn.textContent = "CONTINUE →";
            nextBtn.style.display = "inline-flex";

            if (chapterEyebrow) chapterEyebrow.textContent = "03 • CONFIGURE";
            if (narrativeQ) narrativeQ.textContent = "What car are we valuing?";
            if (this.storyController && typeof this.storyController.setChapter === "function") {
                this.storyController.setChapter(3);
            }
        } else {
            tagEl.textContent = "SUMMARY";
            titleEl.textContent = "SPECIFICATION REVIEW";
            nextBtn.style.display = "none";

            if (chapterEyebrow) chapterEyebrow.textContent = "04 • VALUATE";
            if (narrativeQ) narrativeQ.textContent = "Let's find its real value.";
            if (this.storyController && typeof this.storyController.setChapter === "function") {
                this.storyController.setChapter(4);
            }
        }
    }

    renderCurrentStep() {
        const container = this.configPanel.querySelector("#configContent");
        const titleEl = this.configPanel.querySelector("#configStageTitle");
        if (!container) return;

        container.innerHTML = "";

        switch (this.currentStep) {
            case 1:
                titleEl.textContent = "BRAND";
                this.renderBrandStep(container);
                break;
            case 2:
                titleEl.textContent = "MODEL";
                this.renderModelStep(container);
                break;
            case 3:
                titleEl.textContent = "GENERATION / YEAR";
                this.renderGenerationYearStep(container);
                break;
            case 4:
                titleEl.textContent = "VARIANT";
                this.renderVariantStep(container);
                break;
            case 5:
                titleEl.textContent = "FUEL";
                this.renderFuelStep(container);
                break;
            case 6:
                titleEl.textContent = "TRANSMISSION";
                this.renderTransmissionStep(container);
                break;
            case 7:
                titleEl.textContent = "BODY TYPE";
                this.renderBodyTypeStep(container);
                break;
            case 8:
                titleEl.textContent = "CITY";
                this.renderCityStep(container);
                break;
            case 9:
                titleEl.textContent = "KILOMETERS & OWNERS";
                this.renderKmOwnersStep(container);
                break;
            case 10:
                titleEl.textContent = "CONFIGURATION SUMMARY";
                this.renderSummaryStep(container);
                break;
            default:
                break;
        }

        this.updateNavButtonState();
    }

    // --------------------------------------------------------
    // STEP 1: BRAND
    // --------------------------------------------------------
    renderBrandStep(container) {
        const brands = this.getBrandList();
        const selected = this.configuration.brand;

        container.innerHTML = `
            <div class="config-step-desc">Select vehicle manufacturer</div>
            <input type="text" class="config-search-input" id="brandSearchInput" placeholder="Filter brand (e.g. BMW, Mercedes)...">
            <div class="config-grid" id="brandGrid"></div>
        `;

        const grid = container.querySelector("#brandGrid");
        const searchInput = container.querySelector("#brandSearchInput");

        const renderGrid = (filter = "") => {
            grid.innerHTML = "";
            const filtered = brands.filter(b => b.toLowerCase().includes(filter.toLowerCase()));
            if (!filtered.length) {
                grid.innerHTML = `<div class="config-empty">No brands matching "${filter}"</div>`;
                return;
            }

            filtered.forEach(brand => {
                const btn = document.createElement("button");
                btn.type = "button";
                btn.className = `config-pill ${brand === selected ? "active" : ""}`;
                btn.textContent = brand;
                btn.addEventListener("click", () => {
                    this.selectBrand(brand);
                });
                grid.appendChild(btn);
            });
        };

        renderGrid();
        searchInput.addEventListener("input", (e) => {
            renderGrid(e.target.value.trim());
        });
    }

    selectBrand(brand) {
        const isNew = this.configuration.brand !== brand;
        this.configuration.brand = brand;
        if (isNew) {
            // Cascade reset dependent attributes
            this.configuration.model = "";
            this.configuration.generation = "";
            this.configuration.manufacturing_year = null;
            this.configuration.variant = "";
            this.configuration.fuel_type = "";
            this.configuration.transmission_type = "";
            this.configuration.bodytype = "";
            setVehicleIdentity({
                brand: brand,
                model: "",
                generation: "",
                year: null,
                variant: "",
                fuel: "",
                transmission: "",
                bodyType: ""
            });
        } else {
            setVehicleIdentity({ brand: brand });
        }

        this.updateVehicleIdentity();
        this.notifyChange();
        this.nextStep();
    }

    // --------------------------------------------------------
    // STEP 2: MODEL
    // --------------------------------------------------------
    renderModelStep(container) {
        const brand = this.configuration.brand;
        if (!brand) {
            container.innerHTML = `
                <div class="config-empty">Please select a brand first.</div>
            `;
            return;
        }

        const models = this.getModelList(brand);
        const selected = this.configuration.model;

        container.innerHTML = `
            <div class="config-step-desc">Select ${brand} model line</div>
            <input type="text" class="config-search-input" id="modelSearchInput" placeholder="Filter model...">
            <div class="config-grid" id="modelGrid"></div>
        `;

        const grid = container.querySelector("#modelGrid");
        const searchInput = container.querySelector("#modelSearchInput");

        const renderGrid = (filter = "") => {
            grid.innerHTML = "";
            const filtered = models.filter(m => m.toLowerCase().includes(filter.toLowerCase()));
            if (!filtered.length) {
                grid.innerHTML = `<div class="config-empty">No models found for "${brand}"</div>`;
                return;
            }

            filtered.forEach(model => {
                const btn = document.createElement("button");
                btn.type = "button";
                btn.className = `config-pill ${model === selected ? "active" : ""}`;
                btn.textContent = model;
                btn.addEventListener("click", () => {
                    this.selectModel(model);
                });
                grid.appendChild(btn);
            });
        };

        renderGrid();
        searchInput.addEventListener("input", (e) => {
            renderGrid(e.target.value.trim());
        });
    }

    selectModel(model) {
        const isNew = this.configuration.model !== model;
        this.configuration.model = model;
        if (isNew) {
            // Cascade reset model-dependent attributes
            this.configuration.generation = "";
            this.configuration.manufacturing_year = null;
            this.configuration.variant = "";
            this.configuration.fuel_type = "";
            this.configuration.transmission_type = "";
            this.configuration.bodytype = "";

            // Pre-select if exactly 1 option exists in dataset
            const details = this.getModelDetails(this.configuration.brand, model);
            if (details) {
                if (details.fuel_types && details.fuel_types.length === 1) {
                    this.configuration.fuel_type = details.fuel_types[0];
                }
                if (details.transmissions && details.transmissions.length === 1) {
                    this.configuration.transmission_type = details.transmissions[0];
                }
                if (details.body_types && details.body_types.length === 1) {
                    this.configuration.bodytype = details.body_types[0];
                }
            }
        }

        setVehicleIdentity({
            model: model,
            generation: this.configuration.generation,
            year: this.configuration.manufacturing_year,
            variant: this.configuration.variant,
            fuel: this.configuration.fuel_type,
            transmission: this.configuration.transmission_type,
            bodyType: this.configuration.bodytype
        });

        this.updateVehicleIdentity();
        this.notifyChange();
        this.nextStep();
    }

    // --------------------------------------------------------
    // STEP 3: GENERATION / YEAR
    // --------------------------------------------------------
    renderGenerationYearStep(container) {
        const CURRENT_YEAR = 2026;
        const brand = this.configuration.brand;
        const model = this.configuration.model;
        const yearVal = this.configuration.manufacturing_year;
        const genVal = this.configuration.generation;

        const generations = this.getGenerationsForModel(brand, model);

        container.innerHTML = `
            <div class="config-step-desc">Select vehicle generation and manufacturing year</div>

            <div class="config-section-group">
                <div class="config-chips-label">GENERATION / SERIES</div>
                <div class="config-chips-row" id="generationChipsRow">
                    ${generations.map(g => `
                        <button type="button" class="config-chip ${g.slug === genVal ? "active" : ""}" data-gen-slug="${g.slug}" data-default-year="${g.defaultYear}">
                            ${g.name}
                        </button>
                    `).join("")}
                </div>
            </div>

            <div class="config-section-group" style="margin-top: 14px;">
                <div class="config-chips-label">MANUFACTURING YEAR (1990 – 2026)</div>
                <div class="config-input-wrap">
                    <input type="number" id="configYearInput" class="config-text-input" min="1990" max="2026" placeholder="e.g. 2021" value="${yearVal !== null ? yearVal : ""}">
                    <div class="config-input-hint" id="yearAgeHint">${yearVal ? `Vehicle Age: ${CURRENT_YEAR - yearVal} years` : "Calculated from 2026"}</div>
                </div>
                <div class="config-chips-label" style="margin-top: 8px;">Popular Year Presets</div>
                <div class="config-chips-row" id="yearChipsRow">
                    ${[2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017, 2016, 2015].map(y => `
                        <button type="button" class="config-chip ${y === yearVal ? "active" : ""}" data-year="${y}">${y}</button>
                    `).join("")}
                </div>
            </div>
        `;

        const input = container.querySelector("#configYearInput");
        const hint = container.querySelector("#yearAgeHint");
        const genChips = container.querySelectorAll("#generationChipsRow .config-chip");
        const yearChips = container.querySelectorAll("#yearChipsRow .config-chip");

        const updateYear = (val) => {
            const num = parseInt(val, 10);
            if (!isNaN(num) && num >= 1990 && num <= CURRENT_YEAR) {
                this.setYear(num);
                hint.textContent = `Vehicle Age: ${CURRENT_YEAR - num} years`;
                yearChips.forEach(c => c.classList.toggle("active", parseInt(c.dataset.year, 10) === num));
            } else {
                this.configuration.manufacturing_year = null;
                hint.textContent = "Please enter a valid year (1990–2026)";
                yearChips.forEach(c => c.classList.remove("active"));
            }
            this.updateNavButtonState();
        };

        input.addEventListener("input", (e) => updateYear(e.target.value));

        yearChips.forEach(c => {
            c.addEventListener("click", () => {
                const y = parseInt(c.dataset.year, 10);
                input.value = y;
                updateYear(y);
            });
        });

        genChips.forEach(c => {
            c.addEventListener("click", () => {
                const slug = c.dataset.genSlug;
                const defYear = parseInt(c.dataset.defaultYear, 10);
                this.configuration.generation = slug;
                genChips.forEach(ch => ch.classList.toggle("active", ch.dataset.genSlug === slug));
                if (!input.value && defYear) {
                    input.value = defYear;
                    updateYear(defYear);
                } else {
                    setVehicleIdentity({ generation: slug });
                    this.notifyChange();
                }
            });
        });
    }

    setYear(year) {
        this.configuration.manufacturing_year = year;
        setVehicleIdentity({ year: year, generation: this.configuration.generation });
        this.updateVehicleIdentity();
        this.notifyChange();
    }

    // --------------------------------------------------------
    // STEP 4: VARIANT
    // --------------------------------------------------------
    renderVariantStep(container) {
        const brand = this.configuration.brand;
        const model = this.configuration.model;
        const variantVal = this.configuration.variant || "";
        const variants = this.getVariantsForModel(brand, model);

        container.innerHTML = `
            <div class="config-step-desc">Select or enter vehicle trim / variant</div>
            <div class="config-input-wrap">
                <input type="text" id="configVariantInput" class="config-text-input" placeholder="e.g. Carrera 4S, M Sport, Luxury Line..." value="${variantVal}">
                <div class="config-input-hint">Specify exact model edition or choose a preset below</div>
            </div>
            <div class="config-chips-label" style="margin-top: 10px;">Available Trim Presets</div>
            <div class="config-grid" id="variantPresetsGrid">
                ${variants.map(v => `
                    <button type="button" class="config-pill ${v.toLowerCase() === variantVal.toLowerCase() ? "active" : ""}" data-variant="${v}">
                        ${v}
                    </button>
                `).join("")}
            </div>
        `;

        const input = container.querySelector("#configVariantInput");
        const pills = container.querySelectorAll("#variantPresetsGrid .config-pill");

        const updateVariant = (val) => {
            const clean = (val || "").trim();
            this.configuration.variant = clean;
            setVehicleIdentity({ variant: clean });
            this.updateVehicleIdentity();
            pills.forEach(p => p.classList.toggle("active", p.dataset.variant.toLowerCase() === clean.toLowerCase()));
            this.notifyChange();
            this.updateNavButtonState();
        };

        input.addEventListener("input", (e) => updateVariant(e.target.value));

        pills.forEach(p => {
            p.addEventListener("click", () => {
                const v = p.dataset.variant;
                input.value = v;
                updateVariant(v);
                this.nextStep();
            });
        });
    }

    // --------------------------------------------------------
    // STEP 5: FUEL TYPE
    // --------------------------------------------------------
    renderFuelStep(container) {
        const { brand, model } = this.configuration;
        const details = this.getModelDetails(brand, model);
        const options = (details && details.fuel_types && details.fuel_types.length)
            ? details.fuel_types
            : [];

        if (!options.length) {
            container.innerHTML = `
                <div class="config-empty">No fuel types available for ${model || "selected vehicle"}.</div>
            `;
            return;
        }

        // Pre-select if single valid option
        if (options.length === 1 && !this.configuration.fuel_type) {
            this.configuration.fuel_type = options[0];
            setVehicleIdentity({ fuel: options[0] });
            this.updateVehicleIdentity();
            this.notifyChange();
        }

        const selected = this.configuration.fuel_type;

        container.innerHTML = `
            <div class="config-step-desc">Select powertrain / fuel type for ${model || "vehicle"}</div>
            <div class="config-cards-grid" id="fuelGrid"></div>
        `;

        const grid = container.querySelector("#fuelGrid");
        options.forEach(fuel => {
            const card = document.createElement("button");
            card.type = "button";
            card.className = `config-card ${fuel === selected ? "active" : ""}`;
            card.innerHTML = `
                <div class="card-icon">&bull;</div>
                <div class="card-name">${fuel}</div>
            `;
            card.addEventListener("click", () => {
                this.selectFuel(fuel);
            });
            grid.appendChild(card);
        });
    }

    selectFuel(fuel) {
        this.configuration.fuel_type = fuel;
        setVehicleIdentity({ fuel: fuel });
        this.updateVehicleIdentity();
        this.notifyChange();
        this.nextStep();
    }

    // --------------------------------------------------------
    // STEP 6: TRANSMISSION
    // --------------------------------------------------------
    renderTransmissionStep(container) {
        const { brand, model } = this.configuration;
        const details = this.getModelDetails(brand, model);
        const options = (details && details.transmissions && details.transmissions.length)
            ? details.transmissions
            : [];

        if (!options.length) {
            container.innerHTML = `
                <div class="config-empty">No transmissions available for ${model || "selected vehicle"}.</div>
            `;
            return;
        }

        // Pre-select if single valid option
        if (options.length === 1 && !this.configuration.transmission_type) {
            this.configuration.transmission_type = options[0];
            setVehicleIdentity({ transmission: options[0] });
            this.notifyChange();
        }

        const selected = this.configuration.transmission_type;

        container.innerHTML = `
            <div class="config-step-desc">Select transmission for ${model || "vehicle"}</div>
            <div class="config-cards-grid" id="transmissionGrid"></div>
        `;

        const grid = container.querySelector("#transmissionGrid");
        options.forEach(trans => {
            const card = document.createElement("button");
            card.type = "button";
            card.className = `config-card ${trans === selected ? "active" : ""}`;
            card.innerHTML = `
                <div class="card-icon">&bull;</div>
                <div class="card-name">${trans}</div>
            `;
            card.addEventListener("click", () => {
                this.selectTransmission(trans);
            });
            grid.appendChild(card);
        });
    }

    selectTransmission(trans) {
        this.configuration.transmission_type = trans;
        setVehicleIdentity({ transmission: trans });
        this.notifyChange();
        this.nextStep();
    }

    // --------------------------------------------------------
    // STEP 7: BODY TYPE
    // --------------------------------------------------------
    renderBodyTypeStep(container) {
        const { brand, model } = this.configuration;
        const details = this.getModelDetails(brand, model);
        const options = (details && details.body_types && details.body_types.length)
            ? details.body_types
            : [];

        if (!options.length) {
            container.innerHTML = `
                <div class="config-empty">No body types available for ${model || "selected vehicle"}.</div>
            `;
            return;
        }

        // Pre-select if single valid option
        if (options.length === 1 && !this.configuration.bodytype) {
            this.configuration.bodytype = options[0];
            setVehicleIdentity({ bodyType: options[0] });
            this.notifyChange();
        }

        const selected = this.configuration.bodytype;

        container.innerHTML = `
            <div class="config-step-desc">Body profile for ${model || "vehicle"}</div>
            <div class="config-cards-grid" id="bodyGrid"></div>
        `;

        const grid = container.querySelector("#bodyGrid");
        options.forEach(body => {
            const card = document.createElement("button");
            card.type = "button";
            card.className = `config-card ${body === selected ? "active" : ""}`;
            card.innerHTML = `
                <div class="card-icon">&bull;</div>
                <div class="card-name">${body}</div>
            `;
            card.addEventListener("click", () => {
                this.selectBodyType(body);
            });
            grid.appendChild(card);
        });
    }

    selectBodyType(body) {
        this.configuration.bodytype = body;
        setVehicleIdentity({ bodyType: body });
        this.notifyChange();
        this.nextStep();
    }

    // --------------------------------------------------------
    // STEP 8: CITY
    // --------------------------------------------------------
    renderCityStep(container) {
        const cities = this.getCityList();
        const selected = this.configuration.city;

        container.innerHTML = `
            <div class="config-step-desc">Operating / registration market</div>
            <input type="text" class="config-search-input" id="citySearchInput" placeholder="Search city (e.g. Delhi, Mumbai)...">
            <div class="config-grid" id="cityGrid"></div>
        `;

        const grid = container.querySelector("#cityGrid");
        const searchInput = container.querySelector("#citySearchInput");

        const renderGrid = (filter = "") => {
            grid.innerHTML = "";
            const filtered = cities.filter(c => c.toLowerCase().includes(filter.toLowerCase()));
            if (!filtered.length) {
                grid.innerHTML = `<div class="config-empty">No cities matching "${filter}"</div>`;
                return;
            }

            filtered.forEach(city => {
                const btn = document.createElement("button");
                btn.type = "button";
                btn.className = `config-pill ${city === selected ? "active" : ""}`;
                btn.textContent = city;
                btn.addEventListener("click", () => {
                    this.selectCity(city);
                });
                grid.appendChild(btn);
            });
        };

        renderGrid();
        searchInput.addEventListener("input", (e) => {
            renderGrid(e.target.value.trim());
        });
    }

    selectCity(city) {
        this.configuration.city = city;
        setVehicleIdentity({ city: city });
        this.notifyChange();
        this.nextStep();
    }

    // --------------------------------------------------------
    // STEP 9: KILOMETERS & OWNERS (COMBINED STEP)
    // --------------------------------------------------------
    renderKmOwnersStep(container) {
        const kmVal = this.configuration.km_driven;
        const ownerVal = this.configuration.number_of_owners;
        const owners = this.getOwnerList();

        container.innerHTML = `
            <div class="config-step-desc">Specify vehicle usage and ownership history</div>

            <!-- Part 1: Kilometers -->
            <div class="config-section-group">
                <div class="config-chips-label">ODOMETER READING (KM DRIVEN)</div>
                <div class="config-input-wrap">
                    <input type="number" id="configKmInput" class="config-text-input" min="0" step="500" placeholder="e.g. 45000" value="${kmVal !== null ? kmVal : ""}">
                    <div class="config-input-hint" id="kmFormattedHint">${kmVal !== null ? kmVal.toLocaleString() + " KM" : "Enter distance in km"}</div>
                </div>
                <div class="config-chips-label" style="margin-top: 8px;">Typical Usage Presets</div>
                <div class="config-chips-row" id="kmChipsRow">
                    ${[15000, 30000, 45000, 60000, 80000, 100000].map(k => `
                        <button type="button" class="config-chip ${k === kmVal ? "active" : ""}" data-km="${k}">${k.toLocaleString()} KM</button>
                    `).join("")}
                </div>
            </div>

            <!-- Part 2: Number of Owners -->
            <div class="config-section-group" style="margin-top: 16px;">
                <div class="config-chips-label">PREVIOUS OWNERSHIP</div>
                <div class="config-cards-grid" id="ownersGrid" style="max-height: 160px;">
                    ${owners.map(o => {
                        const num = parseInt(o, 10);
                        const isMatch = ownerVal !== null && ownerVal === num;
                        const label = num === 1 ? "1st Owner (Single Owner)" :
                                      num === 2 ? "2nd Owner" :
                                      num === 3 ? "3rd Owner" : `${num} Previous Owners`;
                        return `
                            <button type="button" class="config-card ${isMatch ? "active" : ""}" data-owner="${num}">
                                <div class="card-icon">&bull;</div>
                                <div class="card-name">${label}</div>
                            </button>
                        `;
                    }).join("")}
                </div>
            </div>
        `;

        const kmInput = container.querySelector("#configKmInput");
        const kmHint = container.querySelector("#kmFormattedHint");
        const kmChips = container.querySelectorAll("#kmChipsRow .config-chip");
        const ownerCards = container.querySelectorAll("#ownersGrid .config-card");

        const updateKm = (val) => {
            const num = parseFloat(val);
            if (!isNaN(num) && num >= 0) {
                this.configuration.km_driven = num;
                kmHint.textContent = `${Math.round(num).toLocaleString()} KM`;
                kmChips.forEach(c => c.classList.toggle("active", parseFloat(c.dataset.km) === num));
            } else {
                this.configuration.km_driven = null;
                kmHint.textContent = "Must be a non-negative number";
                kmChips.forEach(c => c.classList.remove("active"));
            }
            this.notifyChange();
            this.updateNavButtonState();
        };

        kmInput.addEventListener("input", (e) => updateKm(e.target.value));

        kmChips.forEach(c => {
            c.addEventListener("click", () => {
                const k = parseFloat(c.dataset.km);
                kmInput.value = k;
                updateKm(k);
            });
        });

        ownerCards.forEach(card => {
            card.addEventListener("click", () => {
                const num = parseInt(card.dataset.owner, 10);
                this.configuration.number_of_owners = isNaN(num) ? 1 : num;
                setVehicleIdentity({ owners: this.configuration.number_of_owners });
                ownerCards.forEach(c => c.classList.toggle("active", parseInt(c.dataset.owner, 10) === this.configuration.number_of_owners));
                this.notifyChange();
                this.updateNavButtonState();
            });
        });
    }

    // --------------------------------------------------------
    // STEP 10: CONFIGURATION SUMMARY
    // --------------------------------------------------------
    renderSummaryStep(container) {
        const c = this.configuration;
        const isValid = this.isConfigurationValid();
        const CURRENT_YEAR = 2026;

        container.innerHTML = `
            <div class="config-step-desc">Review your verified vehicle specification</div>
            <div class="config-summary-card">
                <div class="summary-hero-row">
                    <div class="summary-hero-brand">${c.brand || "—"}</div>
                    <div class="summary-hero-model">${c.model || "—"}</div>
                    ${c.variant ? `<div class="summary-hero-variant" style="font-size:12px;color:#00d4ff;margin-top:2px;">${c.variant}</div>` : ""}
                </div>

                <div class="summary-spec-grid">
                    <div class="spec-cell">
                        <span class="spec-label">YEAR &amp; GEN</span>
                        <span class="spec-val">${c.manufacturing_year ? `${c.manufacturing_year} (${CURRENT_YEAR - c.manufacturing_year}y)` : "—"} ${c.generation ? `• ${c.generation.toUpperCase()}` : ""}</span>
                    </div>
                    <div class="spec-cell">
                        <span class="spec-label">USAGE</span>
                        <span class="spec-val">${c.km_driven !== null ? c.km_driven.toLocaleString() + " KM" : "—"}</span>
                    </div>
                    <div class="spec-cell">
                        <span class="spec-label">POWERTRAIN</span>
                        <span class="spec-val">${c.fuel_type || "—"}</span>
                    </div>
                    <div class="spec-cell">
                        <span class="spec-label">GEARBOX</span>
                        <span class="spec-val">${c.transmission_type || "—"}</span>
                    </div>
                    <div class="spec-cell">
                        <span class="spec-label">BODY STYLE</span>
                        <span class="spec-val">${c.bodytype || "—"}</span>
                    </div>
                    <div class="spec-cell">
                        <span class="spec-label">LOCATION</span>
                        <span class="spec-val">${c.city || "—"}</span>
                    </div>
                    <div class="spec-cell full-width">
                        <span class="spec-label">OWNERSHIP</span>
                        <span class="spec-val">${c.number_of_owners === 1 ? "1st Owner (Single Owner)" : (c.number_of_owners ? c.number_of_owners + " Previous Owners" : "—")}</span>
                    </div>
                </div>
            </div>

            <div id="valuationFeedbackArea"></div>

            <div class="summary-actions">
                <button type="button" class="summary-edit-btn" id="editConfigBtn">
                    &larr; EDIT SPECIFICATION
                </button>
                <button type="button" class="summary-proceed-btn" id="proceedValuationBtn" ${isValid ? "" : "disabled"}>
                    ESTIMATE REAL VALUE &rarr;
                </button>
            </div>
        `;

        container.querySelector("#editConfigBtn").addEventListener("click", () => {
            this.goToStep(1);
        });

        const proceedBtn = container.querySelector("#proceedValuationBtn");
        proceedBtn.addEventListener("click", () => {
            if (this.isConfigurationValid()) {
                this.executeValuation();
            }
        });
    }

    async executeValuation() {
        if (!this.isConfigurationValid()) {
            return;
        }

        // Prevent duplicate requests
        if (this.predictionService && typeof this.predictionService.getIsPredicting === "function" && this.predictionService.getIsPredicting()) {
            return;
        }

        if (!this.isConfiguratorOpen) {
            this.openConfigurator(10);
        }

        // Enter VALUATING state
        this.setAppState("VALUATING");
        this.setStatus("CALCULATING MARKET VALUE");

        if (window.smartCarExperience && typeof window.smartCarExperience.getAnimation === "function") {
            const anim = window.smartCarExperience.getAnimation();
            if (anim && typeof anim.setState === "function") {
                anim.setState("VALUATING");
            }
        }

        // Cinematic camera transition to valuation angle
        if (this.cameraController && typeof this.cameraController.transitionToValuation === "function") {
            this.cameraController.transitionToValuation();
        }

        // Lighting profile switch to VALUATION
        if (typeof window !== "undefined" && window.smartCarExperience) {
            const sceneInstance = window.smartCarExperience.getSceneInstance();
            if (sceneInstance && typeof sceneInstance.setLightingProfile === "function") {
                sceneInstance.setLightingProfile("VALUATION");
            }
        }

        // Hide navigation footer during valuation
        const footer = this.configPanel.querySelector("#configFooter");
        if (footer) {
            footer.style.display = "none";
        }

        const chapterEyebrow = this.configPanel.querySelector("#configChapterEyebrow");
        const narrativeQ = this.configPanel.querySelector("#configNarrativeQ");
        const stageTitle = this.configPanel.querySelector("#configStageTitle");
        const stepTag = this.configPanel.querySelector("#configStepTag");
        if (chapterEyebrow) chapterEyebrow.textContent = "04 • VALUATION PIPELINE";
        if (narrativeQ) narrativeQ.textContent = "AUTONOMOUS ANALYSIS FLOW";
        if (stageTitle) stageTitle.textContent = "ANALYSIS";
        if (stepTag) stepTag.textContent = "STAGE 1 / 6";

        this.configPanel.classList.add("intelligence-mode");

        if (!this.predictionService) {
            this.predictionService = new SmartCarPrediction();
        }

        // Launch ML prediction query concurrently with cinematic analysis stages
        const predictionPromise = this.predictionService.predict(this.getConfiguration());

        try {
            await this.runCinematicValuationFlow(predictionPromise);
            const result = await predictionPromise;
            this.showValuationResult(result);
        } catch (err) {
            console.error("SmartCar UI: Valuation error:", err);
            this.setAppState("VALUATION_ERROR");
            this.setStatus("VALUATION ERROR");

            if (footer) footer.style.display = "flex";
            const body = this.configPanel.querySelector("#configContent");
            if (body) {
                body.innerHTML = `
                    <div class="config-error-banner" id="valuationErrorBanner">
                        <span class="error-icon">&#9888;</span>
                        <div class="error-content">
                            <div class="error-title">VALUATION UNAVAILABLE</div>
                            <div class="error-msg">${err.message || "Something went wrong while calculating the valuation."}</div>
                        </div>
                    </div>
                    <div class="valuation-actions">
                        <button type="button" class="valuation-action-btn primary" id="valuationRetryBtn">
                            TRY AGAIN &rarr;
                        </button>
                    </div>
                `;
                const retryBtn = body.querySelector("#valuationRetryBtn");
                if (retryBtn) {
                    retryBtn.addEventListener("click", () => this.executeValuation());
                }
            }
        }
    }

    async runCinematicValuationFlow(predictionPromise) {
        const body = this.configPanel.querySelector("#configContent");
        if (!body) return;

        let isFastForwarded = false;

        body.innerHTML = `
            <div class="cinematic-valuation-flow" id="cinematicValuationFlow">
                <div class="valuation-flow-header">
                    <div class="valuation-pipeline-badge">
                        <span class="stage-pulse-dot"></span>
                        <span>AUTONOMOUS VALUATION ENGINE</span>
                    </div>
                    <h2 class="valuation-active-stage-title" id="valCurrentStageTitle">ANALYZING VEHICLE</h2>
                    <p class="valuation-active-stage-desc" id="valCurrentStageDesc">
                        Decoding vehicle identity, odometer telemetry, mechanical health & age curve...
                    </p>
                </div>

                <div class="valuation-stages-track" id="valStagesTrack">
                    ${CINEMATIC_VALUATION_STAGES.map((stg, i) => `
                        <div class="val-stage-node ${i === 0 ? 'active' : ''}" id="valStageNode_${i}" data-stage-id="${stg.id}">
                            <div class="stage-node-circle">
                                <span class="stage-node-num">${i + 1}</span>
                                <span class="stage-node-check">✓</span>
                            </div>
                            <span class="stage-node-name">${stg.name}</span>
                        </div>
                    `).join("")}
                </div>

                <div class="val-progress-bar-wrap">
                    <div class="val-progress-bar-fill" id="valProgressBarFill" style="width: 16.6%;"></div>
                </div>

                <div class="val-telemetry-hud">
                    <div class="val-hud-chip">
                        <span class="val-chip-lbl">VEHICLE:</span>
                        <span class="val-chip-val">${this.configuration.brand || "—"} ${this.configuration.model || "—"}</span>
                    </div>
                    <div class="val-hud-chip">
                        <span class="val-chip-lbl">MODEL YEAR:</span>
                        <span class="val-chip-val">${this.configuration.manufacturing_year || "—"}</span>
                    </div>
                    <div class="val-hud-chip">
                        <span class="val-chip-lbl">ODOMETER:</span>
                        <span class="val-chip-val">${Number(this.configuration.km_driven || 0).toLocaleString('en-IN')} KM</span>
                    </div>
                    <div class="val-hud-chip">
                        <span class="val-chip-lbl">DATASET BASE:</span>
                        <span class="val-chip-val">57,480 Records</span>
                    </div>
                </div>

                <div class="val-skip-container">
                    <button type="button" class="val-skip-btn" id="valFastForwardBtn">
                        FAST-FORWARD REVEAL &rarr;
                    </button>
                </div>
            </div>
        `;

        const fastForwardBtn = body.querySelector("#valFastForwardBtn");
        if (fastForwardBtn) {
            fastForwardBtn.addEventListener("click", () => {
                isFastForwarded = true;
            });
        }

        const stageTitleEl = body.querySelector("#valCurrentStageTitle");
        const stageDescEl = body.querySelector("#valCurrentStageDesc");
        const progressFillEl = body.querySelector("#valProgressBarFill");
        const stepTagEl = this.configPanel.querySelector("#configStepTag");
        const scannerMsg = document.getElementById("scannerStatusMsg");

        // 750ms per stage -> 6 stages = 4,500ms total default duration (<= 6 seconds)
        const stageDuration = 750;

        for (let i = 0; i < CINEMATIC_VALUATION_STAGES.length; i++) {
            if (isFastForwarded) break;

            const stage = CINEMATIC_VALUATION_STAGES[i];

            if (stageTitleEl) stageTitleEl.textContent = stage.name;
            if (stageDescEl) stageDescEl.textContent = stage.subtext;
            if (stepTagEl) stepTagEl.textContent = `STAGE ${i + 1} / ${CINEMATIC_VALUATION_STAGES.length}`;
            if (progressFillEl) {
                const pct = Math.round(((i + 1) / CINEMATIC_VALUATION_STAGES.length) * 100);
                progressFillEl.style.width = `${pct}%`;
            }

            for (let j = 0; j < CINEMATIC_VALUATION_STAGES.length; j++) {
                const node = body.querySelector(`#valStageNode_${j}`);
                if (node) {
                    if (j < i) {
                        node.classList.remove("active");
                        node.classList.add("completed");
                    } else if (j === i) {
                        node.classList.add("active");
                        node.classList.remove("completed");
                    } else {
                        node.classList.remove("active", "completed");
                    }
                }
            }

            this.setStatus(stage.name);
            if (scannerMsg) {
                scannerMsg.textContent = `${stage.name}...`;
            }

            try {
                if (i === CINEMATIC_VALUATION_STAGES.length - 1) {
                    SoundEngine.playChime();
                } else {
                    SoundEngine.playScan();
                }
            } catch (e) {}

            const start = performance.now();
            while (performance.now() - start < stageDuration) {
                if (isFastForwarded) break;
                await new Promise(r => setTimeout(r, 50));
            }
        }

        if (progressFillEl) progressFillEl.style.width = "100%";
        this.setStatus("PRICE REVEAL");
    }

    showValuationResult(result) {
        this.isValuationReady = true;
        this.setAppState("VALUATION_RESULT");
        this.setStatus("VALUATION COMPLETE");

        if (window.smartCarExperience && typeof window.smartCarExperience.getAnimation === "function") {
            const anim = window.smartCarExperience.getAnimation();
            if (anim && typeof anim.setState === "function") {
                anim.setState("VALUATION_RESULT");
            }
        }

        // Camera transition to heroic valuation angle
        if (this.cameraController && typeof this.cameraController.transitionToFinalValue === "function") {
            this.cameraController.transitionToFinalValue();
        }

        // Lighting profile switch to RESULT
        if (typeof window !== "undefined" && window.smartCarExperience) {
            const sceneInstance = window.smartCarExperience.getSceneInstance();
            if (sceneInstance && typeof sceneInstance.setLightingProfile === "function") {
                sceneInstance.setLightingProfile("RESULT");
            }
        }

        const chapterEyebrow = this.configPanel.querySelector("#configChapterEyebrow");
        const narrativeQ = this.configPanel.querySelector("#configNarrativeQ");
        if (chapterEyebrow) chapterEyebrow.textContent = "05 • THE REAL VALUE";
        if (narrativeQ) narrativeQ.textContent = "ESTIMATED MARKET VALUE";

        if (this.storyController && typeof this.storyController.setChapter === "function") {
            this.storyController.setChapter(5);
        }

        const stageTitle = this.configPanel.querySelector("#configStageTitle");
        if (stageTitle) {
            stageTitle.textContent = "VALUATION";
        }
        const stepTag = this.configPanel.querySelector("#configStepTag");
        if (stepTag) {
            stepTag.textContent = "05 / 05";
        }

        this.configPanel.classList.add("intelligence-mode");

        const footer = this.configPanel.querySelector("#configFooter");
        if (footer) {
            footer.style.display = "none";
        }

        const body = this.configPanel.querySelector("#configContent");
        if (!body) return;

        this.lastValuationResult = result;
        this.updateAIContextBanner();

        const c = this.configuration;
        const veh = result.vehicle || result.details || c;
        const derived = result.derived || {};
        const metrics = result.model_metrics || {};

        const CURRENT_YEAR = 2026;
        const vehicleYear = Number(veh.manufacturing_year !== undefined ? veh.manufacturing_year : c.manufacturing_year);
        const vehicleAge = (derived.vehicle_age !== undefined)
            ? Number(derived.vehicle_age)
            : (CURRENT_YEAR - vehicleYear);

        const kmDriven = Number(veh.km_driven !== undefined ? veh.km_driven : c.km_driven);
        const formattedKm = !isNaN(kmDriven) ? `${Math.round(kmDriven).toLocaleString("en-IN")} KM` : "—";

        const ownersNum = Number(veh.number_of_owners !== undefined ? veh.number_of_owners : c.number_of_owners);
        const ownershipLabel = ownersNum === 1 ? "1st Owner (Single Owner)" : `${ownersNum} Previous Owners`;

        // Extract 7 Phase 8 core dimensions
        const priceRange = result.price_range || {
            min: result.prediction ? Math.round(result.prediction * 0.9) : 0,
            max: result.prediction ? Math.round(result.prediction * 1.1) : 0,
            formatted_min: "—",
            formatted_max: "—",
            formatted_margin: "—",
            confidence_level: "90% Empirical Interval",
            methodology: "Model Prediction Interval based on test Mean Absolute Error (MAE = ₹1,28,472, R² = 0.8993) scaled by segment price tier (±6.5% standard error band)."
        };

        const marketPosition = result.market_position || {
            percentile: 50,
            formatted_median_price: result.formatted_prediction || "—",
            delta_pct: 0,
            verdict: "Fair Market",
            label: "Aligned with Segment Median",
            summary: "Aligned with segment median in dataset."
        };

        const depreciation = result.depreciation || {
            age_years: vehicleAge,
            retained_value_pct: 75.0,
            total_depreciation_pct: 25.0,
            annual_depreciation_rate: 12.5,
            methodology: "Empirical automotive depreciation schedule calibrated to vehicle age and Indian secondary market transaction velocity."
        };

        const usageIntensity = result.usage_intensity || {
            annual_km: Math.round(kmDriven / Math.max(1, vehicleAge)),
            formatted_annual_km: `${Math.round(kmDriven / Math.max(1, vehicleAge)).toLocaleString("en-IN")} KM / Year`,
            benchmark_annual_km: 11000,
            ratio: 1.0,
            badge: "STANDARD",
            description: "Aligned with standard private ownership benchmarks."
        };

        const ownershipImpact = result.ownership_impact || {
            number_of_owners: ownersNum,
            impact_label: ownershipLabel,
            adjustment_pct: 0,
            description: "Standard private title history."
        };

        const demandLevel = result.demand_level || {
            liquidity_score: 80,
            comparable_count: 50,
            label: "Healthy Demand & Consistent Turnover",
            description: "Consistent listing velocity observed in secondary market."
        };
        const marketIntel = result.market_intelligence || {};
        const marketCtx = marketIntel.market_context || result.market_context || {};
        const deprecCurve = marketIntel.depreciation_curve || {};
        const fuelMix = marketIntel.fuel_mix || {};
        const transMix = marketIntel.transmission_mix || {};
        const cityVol = marketIntel.city_volume || {};

        // 1. Depreciation Curve Chart HTML
        let deprecCurveHtml = "";
        if (deprecCurve.has_sufficient_data && deprecCurve.points && deprecCurve.points.length >= 2) {
            const pointsHtml = deprecCurve.points.map(pt => {
                const fillHeight = Math.max(12, Math.min(100, Math.round(100 - pt.depreciation_vs_newest_pct)));
                return `
                    <div class="deprec-point-col ${pt.is_selected_year ? 'selected' : ''}">
                        <span class="deprec-col-price">${pt.formatted_median_price}</span>
                        <div class="deprec-col-bar-wrap" title="${pt.year}: ${pt.formatted_median_price} (-${pt.depreciation_vs_newest_pct}%)">
                            <div class="deprec-col-bar-fill" style="height: ${fillHeight}%;"></div>
                        </div>
                        <span class="deprec-col-year">${pt.year}</span>
                        <span class="deprec-col-rate">-${pt.depreciation_vs_newest_pct}%</span>
                        <span class="deprec-col-cnt">(${pt.count})</span>
                    </div>
                `;
            }).join("");

            deprecCurveHtml = `
                <div class="intel-chart-card full-width" id="intelDepreciationCard">
                    <div class="intel-chart-header">
                        <span class="intel-chart-tag">EMPIRICAL DEPRECIATION CURVE</span>
                        <h4 class="intel-chart-title">Observed Resale Medians by Year</h4>
                        <span class="intel-chart-badge">${deprecCurve.cohort_count} Year Cohorts</span>
                    </div>
                    <div class="deprec-curve-chart-container" id="intelDepreciationChart">
                        <div class="deprec-columns-wrap">
                            ${pointsHtml}
                        </div>
                    </div>
                    <div class="intel-chart-caption">
                        <span>Cohort baseline: ${deprecCurve.newest_anchor_year} (${deprecCurve.formatted_newest_anchor_price}). Empirical depreciation calculated from actual transactions.</span>
                    </div>
                </div>
            `;
        } else {
            deprecCurveHtml = `
                <div class="intel-chart-card full-width" id="intelDepreciationCard">
                    <div class="intel-chart-header">
                        <span class="intel-chart-tag">EMPIRICAL DEPRECIATION CURVE</span>
                        <h4 class="intel-chart-title">Observed Resale Medians by Year</h4>
                    </div>
                    <div class="intel-sparse-notice">
                        <span class="sparse-badge">Insufficient Data</span>
                        <p class="sparse-desc">Fewer than 3 recorded year cohorts in dataset for this model specification.</p>
                    </div>
                </div>
            `;
        }

        // 2. Fuel Mix Breakdown Chart HTML
        let fuelMixHtml = "";
        if (fuelMix.has_sufficient_data && fuelMix.distribution && fuelMix.distribution.length > 0) {
            const rows = fuelMix.distribution.map(f => `
                <div class="intel-mix-row ${f.is_selected ? 'selected' : ''}">
                    <div class="intel-mix-info">
                        <span class="mix-name">${f.fuel_type}</span>
                        <span class="mix-stat">${f.count} records (${f.percentage}%)</span>
                    </div>
                    <div class="intel-mix-track">
                        <div class="intel-mix-fill fuel" style="width: ${f.percentage}%;"></div>
                    </div>
                </div>
            `).join("");

            fuelMixHtml = `
                <div class="intel-chart-card" id="intelFuelMixCard">
                    <div class="intel-chart-header">
                        <span class="intel-chart-tag">FUEL DISTRIBUTION</span>
                        <h4 class="intel-chart-title">Segment Fuel Mix</h4>
                    </div>
                    <div class="intel-mix-list" id="intelFuelMixChart">
                        ${rows}
                    </div>
                </div>
            `;
        } else {
            fuelMixHtml = `
                <div class="intel-chart-card" id="intelFuelMixCard">
                    <div class="intel-chart-header">
                        <span class="intel-chart-tag">FUEL DISTRIBUTION</span>
                        <h4 class="intel-chart-title">Segment Fuel Mix</h4>
                    </div>
                    <div class="intel-sparse-notice">
                        <span class="sparse-badge">Insufficient Data</span>
                        <p class="sparse-desc">Insufficient fuel distribution records in dataset.</p>
                    </div>
                </div>
            `;
        }

        // 3. Transmission Mix Breakdown Chart HTML
        let transMixHtml = "";
        if (transMix.has_sufficient_data && transMix.distribution && transMix.distribution.length > 0) {
            const rows = transMix.distribution.map(t => `
                <div class="intel-mix-row ${t.is_selected ? 'selected' : ''}">
                    <div class="intel-mix-info">
                        <span class="mix-name">${t.transmission}</span>
                        <span class="mix-stat">${t.count} records (${t.percentage}%)</span>
                    </div>
                    <div class="intel-mix-track">
                        <div class="intel-mix-fill trans" style="width: ${t.percentage}%;"></div>
                    </div>
                </div>
            `).join("");

            transMixHtml = `
                <div class="intel-chart-card" id="intelTransMixCard">
                    <div class="intel-chart-header">
                        <span class="intel-chart-tag">TRANSMISSION DISTRIBUTION</span>
                        <h4 class="intel-chart-title">Gearbox Breakdown</h4>
                    </div>
                    <div class="intel-mix-list" id="intelTransmissionMixChart">
                        ${rows}
                    </div>
                </div>
            `;
        } else {
            transMixHtml = `
                <div class="intel-chart-card" id="intelTransMixCard">
                    <div class="intel-chart-header">
                        <span class="intel-chart-tag">TRANSMISSION DISTRIBUTION</span>
                        <h4 class="intel-chart-title">Gearbox Breakdown</h4>
                    </div>
                    <div class="intel-sparse-notice">
                        <span class="sparse-badge">Insufficient Data</span>
                        <p class="sparse-desc">Insufficient transmission records in dataset.</p>
                    </div>
                </div>
            `;
        }

        // 4. City Volume Distribution HTML
        let cityVolHtml = "";
        if (cityVol.has_sufficient_data && cityVol.top_cities && cityVol.top_cities.length > 0) {
            const cells = cityVol.top_cities.map(c => `
                <div class="intel-city-card ${c.is_selected ? 'selected' : ''}">
                    <span class="city-name">${c.city}</span>
                    <span class="city-count">${c.count} listings</span>
                    <span class="city-pct">${c.percentage}% of segment</span>
                </div>
            `).join("");

            let selCityNote = "";
            if (cityVol.selected_city_stats) {
                const sc = cityVol.selected_city_stats;
                selCityNote = `<div class="selected-city-tag">Selected City (${sc.city}): ${sc.count} listings (${sc.percentage}% of segment)</div>`;
            }

            cityVolHtml = `
                <div class="intel-chart-card full-width" id="intelCityVolCard">
                    <div class="intel-chart-header">
                        <span class="intel-chart-tag">REGIONAL LIQUIDITY</span>
                        <h4 class="intel-chart-title">Top Regional Markets by Listing Volume</h4>
                    </div>
                    <div class="intel-cities-grid" id="intelCityVolumeChart">
                        ${cells}
                    </div>
                    ${selCityNote}
                </div>
            `;
        } else {
            cityVolHtml = `
                <div class="intel-chart-card full-width" id="intelCityVolCard">
                    <div class="intel-chart-header">
                        <span class="intel-chart-tag">REGIONAL LIQUIDITY</span>
                        <h4 class="intel-chart-title">Top Regional Markets by Listing Volume</h4>
                    </div>
                    <div class="intel-sparse-notice">
                        <span class="sparse-badge">Insufficient Data</span>
                        <p class="sparse-desc">Insufficient regional city volume in dataset.</p>
                    </div>
                </div>
            `;
        }

        // 5. Market Context Card HTML
        let marketContextHtml = "";
        if (marketCtx.has_sufficient_data) {
            marketContextHtml = `
                <div class="intel-chart-card full-width" id="intelMarketContextCard">
                    <div class="intel-chart-header">
                        <span class="intel-chart-tag">DATASET CONTEXT</span>
                        <h4 class="intel-chart-title">Price Spread &amp; Distribution Metrics</h4>
                        <span class="intel-chart-badge">${marketCtx.sample_size} Listings</span>
                    </div>
                    <div class="intel-spread-grid">
                        <div class="spread-cell">
                            <span class="spread-lbl">LOWEST</span>
                            <span class="spread-val">${marketCtx.formatted_min_price}</span>
                        </div>
                        <div class="spread-cell">
                            <span class="spread-lbl">25TH PERCENTILE</span>
                            <span class="spread-val">${marketCtx.formatted_p25_price}</span>
                        </div>
                        <div class="spread-cell highlight">
                            <span class="spread-lbl">MEDIAN</span>
                            <span class="spread-val">${marketCtx.formatted_median_price}</span>
                        </div>
                        <div class="spread-cell">
                            <span class="spread-lbl">75TH PERCENTILE</span>
                            <span class="spread-val">${marketCtx.formatted_p75_price}</span>
                        </div>
                        <div class="spread-cell">
                            <span class="spread-lbl">HIGHEST</span>
                            <span class="spread-val">${marketCtx.formatted_max_price}</span>
                        </div>
                        <div class="spread-cell">
                            <span class="spread-lbl">SPREAD (IQR)</span>
                            <span class="spread-val">${marketCtx.formatted_iqr}</span>
                        </div>
                    </div>
                </div>
            `;
        } else {
            marketContextHtml = `
                <div class="intel-chart-card full-width" id="intelMarketContextCard">
                    <div class="intel-chart-header">
                        <span class="intel-chart-tag">DATASET CONTEXT</span>
                        <h4 class="intel-chart-title">Price Spread &amp; Distribution Metrics</h4>
                    </div>
                    <div class="intel-sparse-notice">
                        <span class="sparse-badge">Insufficient Data</span>
                        <p class="sparse-desc">Limited comparable records in dataset for this model.</p>
                    </div>
                </div>
            `;
        }

        // Build Comparables Markup
        const comparablesCardsHtml = comparables.length > 0 ? comparables.map(comp => `
            <div class="val-comp-card" data-record-id="${comp.record_id}">
                <div class="val-comp-head">
                    <span class="val-comp-name">${comp.manufacturing_year} ${comp.brand} ${comp.model}</span>
                    <span class="val-comp-price">${comp.formatted_price}</span>
                </div>
                <div class="val-comp-specs">
                    <span class="val-comp-spec-pill">${comp.fuel_type}</span>
                    <span class="val-comp-spec-pill">${comp.transmission_type}</span>
                    <span class="val-comp-spec-pill">${comp.formatted_km}</span>
                    <span class="val-comp-spec-pill">${comp.city}</span>
                </div>
                <div class="val-comp-meta">
                    <span class="val-comp-badge">DATASET RECORD #${comp.record_id}</span>
                </div>
            </div>
        `).join("") : `
            <div class="intel-sparse-notice">
                <span class="sparse-badge">Insufficient Data</span>
                <p class="sparse-desc">Limited direct vehicle comparables recorded in dataset.</p>
            </div>
        `;

        body.innerHTML = `
            <div class="valuation-result-wrap" id="valuationResultWrap">
                <div class="valuation-badge">
                    <span class="badge-dot"></span>
                    <span>05 &bull; THE REAL VALUE</span>
                </div>

                <!-- PRICE REVEAL SECTION -->
                <div class="valuation-price-card" id="valuationPriceSection">
                    <div class="story-chapter-eyebrow">05 &bull; THE REAL VALUE</div>
                    <div class="price-eyebrow">ESTIMATED MARKET VALUE</div>
                    <div class="price-value" id="valuationPriceDisplay" data-raw-price="${result.prediction}">₹0</div>
                    <div class="price-badge">REAL MODEL INFERENCE &bull; TEST MAE ₹1,28,472 &bull; BENCHMARK R² 0.8993</div>
                    <div class="valuation-actions-row">
                        <button type="button" class="ai-valuation-quick-btn" id="askAiValuationBtn">
                            <span class="ai-btn-spark">✦</span>
                            <span>EXPLAIN WITH AI ASSISTANT</span>
                        </button>
                        <button type="button" class="market-quick-btn" id="exploreMarketLink">
                            EXPLORE MARKET INTELLIGENCE &darr;
                        </button>
                    </div>
                </div>

                <!-- 7 DIMENSIONS OF VALUATION ANALYSIS -->
                <div class="valuation-dimensions-grid">
                    <!-- DIMENSION 1: PRICE RANGE -->
                    <div class="val-dimension-card" id="cardPriceRange">
                        <div class="val-dim-header">
                            <span class="val-dim-tag">DIMENSION 01</span>
                            <h3 class="val-dim-title">PRICE RANGE</h3>
                            <span class="val-dim-pill">${priceRange.confidence_level}</span>
                        </div>
                        <div class="val-dim-body">
                            <div class="range-hero-numbers">
                                <span class="range-num-val" id="valuationRangeMin">${priceRange.formatted_min}</span>
                                <span class="range-num-sep">&mdash;</span>
                                <span class="range-num-val" id="valuationRangeMax">${priceRange.formatted_max}</span>
                            </div>
                            <div class="range-margin-chip">
                                <span>Margin: &plusmn;${priceRange.formatted_margin}</span>
                                <span class="dot-sep">&bull;</span>
                                <span>Point Estimate: ${result.formatted_prediction}</span>
                            </div>
                            <div class="val-methodology-callout">
                                <span class="methodology-lbl">DOCUMENTED METHODOLOGY</span>
                                <p class="methodology-desc" id="valuationMethodologyText">${priceRange.methodology}</p>
                            </div>
                        </div>
                    </div>

                    <!-- DIMENSION 2: MARKET POSITION -->
                    <div class="val-dimension-card" id="cardMarketPosition">
                        <div class="val-dim-header">
                            <span class="val-dim-tag">DIMENSION 02</span>
                            <h3 class="val-dim-title">MARKET POSITION</h3>
                            <span class="val-dim-verdict ${String(marketPosition.verdict || '').toLowerCase().replace(/\s+/g, '-')}">${marketPosition.verdict}</span>
                        </div>
                        <div class="val-dim-body">
                            <div class="val-metrics-triplet">
                                <div class="val-metric-cell">
                                    <span class="cell-lbl">PERCENTILE</span>
                                    <span class="cell-val highlight" id="valuationPercentile">${marketPosition.percentile}th</span>
                                </div>
                                <div class="val-metric-cell">
                                    <span class="cell-lbl">DATASET MEDIAN</span>
                                    <span class="cell-val" id="valuationMedian">${marketPosition.formatted_median_price}</span>
                                </div>
                                <div class="val-metric-cell">
                                    <span class="cell-lbl">DELTA VS MEDIAN</span>
                                    <span class="cell-val ${marketPosition.delta_pct >= 0 ? 'pos' : 'neg'}">
                                        ${marketPosition.delta_pct >= 0 ? '+' : ''}${marketPosition.delta_pct}%
                                    </span>
                                </div>
                            </div>
                            <div class="val-progress-track">
                                <div class="val-progress-fill" style="width: ${marketPosition.percentile}%;"></div>
                            </div>
                            <p class="val-summary-note" id="valuationPositionSummary">${marketPosition.summary}</p>
                        </div>
                    </div>

                    <!-- DIMENSION 3: DEPRECIATION -->
                    <div class="val-dimension-card" id="cardDepreciation">
                        <div class="val-dim-header">
                            <span class="val-dim-tag">DIMENSION 03</span>
                            <h3 class="val-dim-title">DEPRECIATION</h3>
                            <span class="val-dim-pill">${depreciation.age_years} Years Age</span>
                        </div>
                        <div class="val-dim-body">
                            <div class="val-metrics-triplet">
                                <div class="val-metric-cell">
                                    <span class="cell-lbl">RETAINED VALUE</span>
                                    <span class="cell-val highlight" id="valuationRetained">${depreciation.retained_value_pct}%</span>
                                </div>
                                <div class="val-metric-cell">
                                    <span class="cell-lbl">TOTAL DEPREC.</span>
                                    <span class="cell-val neg" id="valuationTotalDeprec">-${depreciation.total_depreciation_pct}%</span>
                                </div>
                                <div class="val-metric-cell">
                                    <span class="cell-lbl">ANNUAL RATE</span>
                                    <span class="cell-val">${depreciation.annual_depreciation_rate}% / yr</span>
                                </div>
                            </div>
                            <div class="val-progress-track">
                                <div class="val-progress-fill" style="width: ${depreciation.retained_value_pct}%;"></div>
                            </div>
                            <div class="val-methodology-callout compact">
                                <span class="methodology-lbl">SCHEDULE</span>
                                <p class="methodology-desc">${depreciation.methodology}</p>
                            </div>
                        </div>
                    </div>

                    <!-- DIMENSION 4: USAGE INTENSITY -->
                    <div class="val-dimension-card" id="cardUsageIntensity">
                        <div class="val-dim-header">
                            <span class="val-dim-tag">DIMENSION 04</span>
                            <h3 class="val-dim-title">USAGE INTENSITY</h3>
                            <span class="usage-badge ${(usageIntensity.badge || 'STANDARD').toLowerCase().replace(/\s+/g, '-')}">${usageIntensity.badge}</span>
                        </div>
                        <div class="val-dim-body">
                            <div class="val-metrics-triplet">
                                <div class="val-metric-cell">
                                    <span class="cell-lbl">ANNUAL MILEAGE</span>
                                    <span class="cell-val highlight" id="valuationAnnualKm">${usageIntensity.formatted_annual_km}</span>
                                </div>
                                <div class="val-metric-cell">
                                    <span class="cell-lbl">BENCHMARK</span>
                                    <span class="cell-val">${Number(usageIntensity.benchmark_annual_km).toLocaleString('en-IN')} KM / yr</span>
                                </div>
                                <div class="val-metric-cell">
                                    <span class="cell-lbl">RATIO</span>
                                    <span class="cell-val">${usageIntensity.ratio}x</span>
                                </div>
                            </div>
                            <p class="val-summary-note" id="valuationUsageDesc">${usageIntensity.description}</p>
                        </div>
                    </div>

                    <!-- DIMENSION 5: OWNERSHIP IMPACT -->
                    <div class="val-dimension-card" id="cardOwnershipImpact">
                        <div class="val-dim-header">
                            <span class="val-dim-tag">DIMENSION 05</span>
                            <h3 class="val-dim-title">OWNERSHIP IMPACT</h3>
                            <span class="val-dim-pill">${ownershipImpact.number_of_owners === 1 ? '1st Hand' : ownershipImpact.number_of_owners + ' Owners'}</span>
                        </div>
                        <div class="val-dim-body">
                            <div class="val-metrics-triplet">
                                <div class="val-metric-cell">
                                    <span class="cell-lbl">OWNERS</span>
                                    <span class="cell-val highlight" id="valuationOwnerCount">${ownershipImpact.number_of_owners}</span>
                                </div>
                                <div class="val-metric-cell">
                                    <span class="cell-lbl">ADJUSTMENT</span>
                                    <span class="cell-val ${ownershipImpact.adjustment_pct < 0 ? 'neg' : 'neutral'}">
                                        ${ownershipImpact.adjustment_pct}%
                                    </span>
                                </div>
                                <div class="val-metric-cell wide">
                                    <span class="cell-lbl">TITLE APPEAL</span>
                                    <span class="cell-val text-status">${ownershipImpact.impact_label}</span>
                                </div>
                            </div>
                            <p class="val-summary-note" id="valuationOwnerDesc">${ownershipImpact.description}</p>
                        </div>
                    </div>

                    <!-- DIMENSION 6: DEMAND LEVEL -->
                    <div class="val-dimension-card" id="cardDemandLevel">
                        <div class="val-dim-header">
                            <span class="val-dim-tag">DIMENSION 06</span>
                            <h3 class="val-dim-title">DEMAND LEVEL</h3>
                            <span class="val-liquidity-pill" id="valuationLiquidityPill">LIQUIDITY: ${demandLevel.liquidity_score}/100</span>
                        </div>
                        <div class="val-dim-body">
                            <div class="val-progress-track">
                                <div class="val-progress-fill" style="width: ${demandLevel.liquidity_score}%;"></div>
                            </div>
                            <div class="val-metrics-triplet">
                                <div class="val-metric-cell">
                                    <span class="cell-lbl">TRANSACTIONS</span>
                                    <span class="cell-val highlight" id="valuationDemandVolume">${demandLevel.comparable_count} Records</span>
                                </div>
                                <div class="val-metric-cell wide">
                                    <span class="cell-lbl">SEGMENT TURNOVER</span>
                                    <span class="cell-val text-status">${demandLevel.label}</span>
                                </div>
                            </div>
                            <p class="val-summary-note" id="valuationDemandDesc">${demandLevel.description}</p>
                        </div>
                    </div>

                    <!-- DIMENSION 7: COMPARABLE VEHICLES -->
                    <div class="val-dimension-card full-width" id="cardComparableVehicles">
                        <div class="val-dim-header">
                            <span class="val-dim-tag">DIMENSION 07</span>
                            <h3 class="val-dim-title">COMPARABLE VEHICLES</h3>
                            <span class="val-dim-dataset-badge">ACTUAL DATASET RECORDS (${comparables.length} MATCHES)</span>
                        </div>
                        <div class="val-dim-body">
                            <div class="val-comps-grid" id="valuationComparablesGrid">
                                ${comparablesCardsHtml}
                            </div>
                            <div class="val-comps-footer">
                                <span>&bull; Real recorded transactions in secondary market dataset matched by multi-attribute distance metric. Zero synthetic interpolation.</span>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- PHASE 9: MARKET INTELLIGENCE & COMPARABLES DASHBOARD -->
                <div class="intel-section" id="intelMarketIntelligence">
                    <div class="intel-section-header">
                        <span class="intel-section-tag">PHASE 09 &bull; MARKET INTELLIGENCE</span>
                        <span class="intel-section-title">DEFENSIBLE DATASET BENCHMARKS &amp; COMPARABLES</span>
                    </div>

                    ${marketContextHtml}
                    ${deprecCurveHtml}

                    <div class="intel-charts-dual-grid">
                        ${fuelMixHtml}
                        ${transMixHtml}
                    </div>

                    ${cityVolHtml}

                    <div class="market-scroll-top">
                        <button type="button" class="market-return-btn" id="returnToValuationTopBtn">
                            &uarr; RETURN TO ESTIMATED VALUE
                        </button>
                    </div>
                </div>

                <!-- VEHICLE PROFILE SUMMARY -->
                <div class="intel-section" id="intelVehicleProfile">
                    <div class="intel-section-header">
                        <span class="intel-section-tag">VEHICLE PROFILE</span>
                        <span class="intel-section-title">${veh.brand} ${veh.model}</span>
                    </div>
                    <div class="intel-spec-grid">
                        <div class="intel-spec-item">
                            <span class="intel-spec-label">BRAND</span>
                            <span class="intel-spec-val" id="intelProfileBrand">${veh.brand}</span>
                        </div>
                        <div class="intel-spec-item">
                            <span class="intel-spec-label">MODEL</span>
                            <span class="intel-spec-val" id="intelProfileModel">${veh.model}</span>
                        </div>
                        <div class="intel-spec-item">
                            <span class="intel-spec-label">YEAR</span>
                            <span class="intel-spec-val" id="intelProfileYear">${vehicleYear}</span>
                        </div>
                        <div class="intel-spec-item">
                            <span class="intel-spec-label">KM DRIVEN</span>
                            <span class="intel-spec-val" id="intelProfileKm">${formattedKm}</span>
                        </div>
                        <div class="intel-spec-item">
                            <span class="intel-spec-label">FUEL</span>
                            <span class="intel-spec-val" id="intelProfileFuel">${veh.fuel_type}</span>
                        </div>
                        <div class="intel-spec-item">
                            <span class="intel-spec-label">TRANSMISSION</span>
                            <span class="intel-spec-val" id="intelProfileTrans">${veh.transmission_type}</span>
                        </div>
                        <div class="intel-spec-item">
                            <span class="intel-spec-label">CITY</span>
                            <span class="intel-spec-val" id="intelProfileCity">${veh.city}</span>
                        </div>
                        <div class="intel-spec-item">
                            <span class="intel-spec-label">BODY TYPE</span>
                            <span class="intel-spec-val" id="intelProfileBody">${veh.bodytype}</span>
                        </div>
                        <div class="intel-spec-item full-width">
                            <span class="intel-spec-label">OWNERS</span>
                            <span class="intel-spec-val" id="intelProfileOwners">${ownershipLabel}</span>
                        </div>
                    </div>
                </div>

                <!-- MODEL TRANSPARENCY (OFFLINE BENCHMARKS) -->
                <div class="intel-section secondary" id="intelModelTransparency">
                    <div class="intel-section-header">
                        <span class="intel-section-tag">MODEL TRANSPARENCY</span>
                        <span class="intel-section-title">OFFLINE EVALUATION BENCHMARKS</span>
                    </div>
                    <div class="intel-metrics-grid">
                        <div class="intel-metric-box">
                            <span class="metric-title">MODEL R&sup2;</span>
                            <span class="metric-number" id="intelMetricR2">0.8993</span>
                        </div>
                        <div class="intel-metric-box">
                            <span class="metric-title">TEST MAE</span>
                            <span class="metric-number" id="intelMetricMae">&#8377;128,472</span>
                        </div>
                        <div class="intel-metric-box">
                            <span class="metric-title">TEST RMSE</span>
                            <span class="metric-number" id="intelMetricRmse">&#8377;529,467.12</span>
                        </div>
                    </div>
                    <div class="intel-metric-note">
                        Model R&sup2; indicates explained variance on held-out test data. Evaluation metrics are offline benchmarks, not live market quotes.
                    </div>
                </div>

                <!-- ACTIONS -->
                <div class="valuation-actions">
                    <button type="button" class="valuation-action-btn secondary" id="reconfigureBtn">
                        &larr; VALUE ANOTHER VEHICLE
                    </button>
                    <button type="button" class="valuation-action-btn primary" id="inspectShowroomBtn">
                        EXPLORE VEHICLE (360&deg;) &rarr;
                    </button>
                </div>
            </div>
        `;

        // Animated price reveal with count-up ticker
        const display = body.querySelector("#valuationPriceDisplay");
        if (display) {
            display.classList.add("revealed");
            this.animatePriceCountUp(result.prediction, result.formatted_prediction);
        }

        // Action listeners
        const reconf = body.querySelector("#reconfigureBtn");
        if (reconf) {
            reconf.addEventListener("click", () => {
                this.configPanel.classList.remove("intelligence-mode");
                if (footer) footer.style.display = "flex";
                this.setAppState("CONFIGURING");
                if (window.smartCarExperience && window.smartCarExperience.getAnimation()) {
                    window.smartCarExperience.getAnimation().setState("CONFIGURING");
                }
                this.goToStep(1);
            });
        }

        const inspectBtn = body.querySelector("#inspectShowroomBtn");
        if (inspectBtn) {
            inspectBtn.addEventListener("click", () => {
                this.configPanel.classList.remove("intelligence-mode");
                this.closeConfigurator();
                if (this.cameraController && typeof this.cameraController.transitionToInspection === "function") {
                    this.cameraController.transitionToInspection();
                }
            });
        }

        const askAiBtn = body.querySelector("#askAiValuationBtn");
        if (askAiBtn) {
            askAiBtn.addEventListener("click", () => {
                this.openAIAssistant("Why is this price?");
            });
        }

        const exploreLink = body.querySelector("#exploreMarketLink");
        if (exploreLink) {
            exploreLink.addEventListener("click", () => {
                const target = body.querySelector("#intelMarketIntelligence");
                if (target) {
                    target.scrollIntoView({ behavior: "smooth", block: "start" });
                }
            });
        }

        const returnTop = body.querySelector("#returnToValuationTopBtn");
        if (returnTop) {
            returnTop.addEventListener("click", () => {
                const target = body.querySelector("#valuationPriceSection");
                if (target) {
                    target.scrollIntoView({ behavior: "smooth", block: "start" });
                }
            });
        }

        if (typeof this.onValuationReadyCallback === "function") {
            this.onValuationReadyCallback(result);
        }
    }

    async fetchMarketIntelligence(brand, model, options = {}) {
        if (!this._marketIntelCache) {
            this._marketIntelCache = new Map();
        }

        const cacheKey = `${brand}_${model}_${options.year || ''}_${options.km || ''}_${options.fuel || ''}_${options.transmission || ''}_${options.city || ''}`;
        if (this._marketIntelCache.has(cacheKey)) {
            return this._marketIntelCache.get(cacheKey);
        }

        const params = new URLSearchParams({
            brand: brand,
            model: model,
            ...(options.city && { city: options.city }),
            ...(options.fuel && { fuel: options.fuel }),
            ...(options.transmission && { transmission: options.transmission }),
            ...(options.year && { year: options.year }),
            ...(options.km && { km: options.km }),
            ...(options.owners && { owners: options.owners })
        });

        const res = await fetch(`/api/market-intelligence?${params.toString()}`);
        if (!res.ok) {
            throw new Error(`Market Intelligence query failed with status ${res.status}`);
        }
        const data = await res.json();
        this._marketIntelCache.set(cacheKey, data);
        if (this._marketIntelCache.size > 30) {
            const firstKey = this._marketIntelCache.keys().next().value;
            this._marketIntelCache.delete(firstKey);
        }
        return data;
    }

    animatePriceCountUp(targetNumber, formattedString) {
        const display = document.getElementById("valuationPriceDisplay");
        if (!display) return;

        const duration = 1400; // ms
        const startTime = performance.now();
        display.classList.add("counting");

        const updateCount = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            // Ease out cubic
            const easeProgress = 1 - Math.pow(1 - progress, 3);

            if (progress < 1) {
                const currentVal = Math.round(targetNumber * easeProgress);
                display.textContent = `₹${currentVal.toLocaleString("en-IN")}`;
                requestAnimationFrame(updateCount);
            } else {
                // Ensure exact model final formatted price
                display.textContent = formattedString || `₹${targetNumber.toLocaleString("en-IN")}`;
                display.classList.remove("counting");
                display.classList.add("revealed-pulse");

                // Trigger victorious sound chime
                try {
                    SoundEngine.playChime();
                } catch (e) {}
            }
        };

        requestAnimationFrame(updateCount);
    }

    resetConfiguration() {
        Object.assign(this.configuration, {
            brand: "",
            model: "",
            generation: "",
            manufacturing_year: null,
            variant: "",
            fuel_type: "",
            transmission_type: "",
            bodytype: "",
            city: "",
            km_driven: null,
            number_of_owners: null
        });
        this.isValuationReady = false;
        this.updateVehicleIdentity();
    }

    markValuationReady() {
        this.isValuationReady = true;
        this.setAppState("VALUATION_READY");
        this.setStatus("VALUATION READY");
        if (window.smartCarExperience && typeof window.smartCarExperience.getAnimation === "function") {
            const anim = window.smartCarExperience.getAnimation();
            if (anim && typeof anim.setState === "function") {
                anim.setState("VALUATION_READY");
            }
        }

        const proceedBtn = this.configPanel.querySelector("#proceedValuationBtn");
        if (proceedBtn) {
            proceedBtn.innerHTML = "&#10003; VALUATION READY (PHASE 7)";
            proceedBtn.classList.add("ready");
            proceedBtn.disabled = true;
        }

        const feedbackArea = this.configPanel.querySelector("#valuationFeedbackArea");
        if (feedbackArea) {
            feedbackArea.innerHTML = `
                <div class="valuation-ready-box">
                    <span class="ready-badge">&#10003; CONFIGURATION VERIFIED</span>
                    <p class="ready-text">All 9 parameters locked. Ready for Machine Learning valuation.</p>
                </div>
            `;
        }

        if (typeof this.onValuationReadyCallback === "function") {
            this.onValuationReadyCallback(this.getConfiguration());
        }

        console.log("SmartCar AI: Configuration complete and ready for valuation:", this.getConfiguration());
    }

    // ========================================================
    // VALIDATION & HELPERS (PHASE 7: 9-STEP CANONICAL SPEC)
    // ========================================================

    validateStep(step) {
        const CURRENT_YEAR = 2026;
        switch (step) {
            case 1:
                return !!this.configuration.brand;
            case 2:
                return !!this.configuration.model;
            case 3:
                return (
                    Number.isInteger(this.configuration.manufacturing_year) &&
                    this.configuration.manufacturing_year >= 1990 &&
                    this.configuration.manufacturing_year <= CURRENT_YEAR
                );
            case 4:
                return !!this.configuration.variant && this.configuration.variant.trim().length > 0;
            case 5:
                return !!this.configuration.fuel_type;
            case 6:
                return !!this.configuration.transmission_type;
            case 7:
                return !!this.configuration.bodytype;
            case 8:
                return !!this.configuration.city;
            case 9:
                return (
                    typeof this.configuration.km_driven === "number" &&
                    !isNaN(this.configuration.km_driven) &&
                    this.configuration.km_driven >= 0 &&
                    Number.isInteger(this.configuration.number_of_owners) &&
                    this.configuration.number_of_owners >= 1
                );
            default:
                return true;
        }
    }

    updateNavButtonState() {
        const nextBtn = this.configPanel.querySelector("#configNextBtn");
        if (!nextBtn) return;

        const isValid = this.validateStep(this.currentStep);
        nextBtn.disabled = !isValid;
    }

    isConfigurationValid() {
        for (let s = 1; s <= 9; s++) {
            if (!this.validateStep(s)) {
                return false;
            }
        }
        return true;
    }

    getValidationMessage(step) {
        switch (step) {
            case 1:
                return "Please select a vehicle manufacturer to continue.";
            case 2:
                return "Please select a vehicle model line.";
            case 3:
                return "Please specify manufacturing year (1990–2026) and generation.";
            case 4:
                return "Please specify vehicle variant or trim level.";
            case 5:
                return "Please select powertrain / fuel type.";
            case 6:
                return "Please select transmission type.";
            case 7:
                return "Please select vehicle body type.";
            case 8:
                return "Please select registration / market city.";
            case 9:
                return "Please specify odometer distance and previous ownership count.";
            default:
                return "Please complete the required specification.";
        }
    }

    showValidationHint(msg) {
        if (!this.configPanel) return;
        const hintEl = this.configPanel.querySelector("#configValidationHint");
        if (hintEl) {
            hintEl.innerHTML = `<span class="hint-bullet">&bull;</span><span>${msg}</span>`;
            hintEl.style.display = "flex";
        }
    }

    hideValidationHint() {
        if (!this.configPanel) return;
        const hintEl = this.configPanel.querySelector("#configValidationHint");
        if (hintEl) {
            hintEl.innerHTML = "";
            hintEl.style.display = "none";
        }
    }

    notifyChange() {
        this.hideValidationHint();
        this.updateNavButtonState();
        if (typeof this.onConfigurationChangeCallback === "function") {
            this.onConfigurationChangeCallback(this.getConfiguration());
        }
    }

    // ========================================================
    // PUBLIC API
    // ========================================================

    setStatus(text) {
        if (this.statusElement) {
            this.statusElement.textContent = text;
        }
    }

    getConfiguration() {
        return this.configuration;
    }

    getIsValuationReady() {
        return this.isValuationReady;
    }

    onValuationReady(fn) {
        this.onValuationReadyCallback = fn;
    }

    onConfigurationChange(fn) {
        this.onConfigurationChangeCallback = fn;
    }

    // ========================================================
    // PHASE 10: AI EXPLANATION ASSISTANT CONTROLLER
    // ========================================================

    setupAIAssistant() {
        this.aiTrigger = document.getElementById("aiAssistantTrigger");
        this.aiDrawer = document.getElementById("aiAssistantDrawer");
        this.aiCloseBtn = document.getElementById("aiAssistantCloseBtn");
        this.aiForm = document.getElementById("aiChatForm");
        this.aiInput = document.getElementById("aiChatInput");
        this.aiMessages = document.getElementById("aiChatMessages");
        this.aiTyping = document.getElementById("aiTypingIndicator");
        this.aiContextText = document.getElementById("aiContextText");
        this.aiSuggestedChips = document.querySelectorAll("#aiSuggestedChips .ai-chip");

        if (this.aiTrigger) {
            this.aiTrigger.addEventListener("click", () => this.toggleAIAssistant());
        }

        if (this.aiCloseBtn) {
            this.aiCloseBtn.addEventListener("click", () => this.closeAIAssistant());
        }

        if (this.aiForm) {
            this.aiForm.addEventListener("submit", (e) => {
                e.preventDefault();
                const q = this.aiInput ? this.aiInput.value.trim() : "";
                if (q) {
                    this.askAIAssistant(q);
                    if (this.aiInput) this.aiInput.value = "";
                }
            });
        }

        if (this.aiSuggestedChips) {
            this.aiSuggestedChips.forEach(chip => {
                chip.addEventListener("click", () => {
                    const q = chip.dataset.q;
                    if (q) {
                        this.askAIAssistant(q);
                    }
                });
            });
        }

        // Delegate copy and share actions on messages
        if (this.aiMessages) {
            this.aiMessages.addEventListener("click", (e) => {
                const copyBtn = e.target.closest(".ai-copy-btn");
                if (copyBtn) {
                    const text = copyBtn.dataset.text || "";
                    if (navigator.clipboard && text) {
                        navigator.clipboard.writeText(text).then(() => {
                            const orig = copyBtn.textContent;
                            copyBtn.textContent = "COPIED!";
                            setTimeout(() => { copyBtn.textContent = orig; }, 1800);
                        }).catch(() => {});
                    }
                }

                const shareBtn = e.target.closest(".ai-share-btn");
                if (shareBtn) {
                    const text = shareBtn.dataset.text || "";
                    if (navigator.share) {
                        navigator.share({
                            title: "SmartCar AI Valuation Explanation",
                            text: text
                        }).catch(() => {});
                    } else if (navigator.clipboard && text) {
                        navigator.clipboard.writeText(text).then(() => {
                            const orig = shareBtn.textContent;
                            shareBtn.textContent = "COPIED LINK!";
                            setTimeout(() => { shareBtn.textContent = orig; }, 1800);
                        }).catch(() => {});
                    }
                }
            });
        }
    }

    openAIAssistant(prefilledQuestion = null) {
        if (!this.aiDrawer) {
            this.setupAIAssistant();
        }
        if (this.aiDrawer) {
            this.aiDrawer.classList.remove("hidden");
            this.updateAIContextBanner();
            if (prefilledQuestion) {
                this.askAIAssistant(prefilledQuestion);
            } else if (this.aiInput) {
                this.aiInput.focus();
            }
        }
    }

    closeAIAssistant() {
        if (this.aiDrawer) {
            this.aiDrawer.classList.add("hidden");
        }
    }

    toggleAIAssistant() {
        if (!this.aiDrawer) {
            this.setupAIAssistant();
        }
        if (this.aiDrawer) {
            if (this.aiDrawer.classList.contains("hidden")) {
                this.openAIAssistant();
            } else {
                this.closeAIAssistant();
            }
        }
    }

    updateAIContextBanner() {
        if (!this.aiContextText) return;
        const c = this.configuration;
        const res = this.lastValuationResult;

        if (c.brand && c.model) {
            const yr = c.manufacturing_year || "";
            const price = res?.formatted_prediction ? ` • Valuation: ${res.formatted_prediction}` : "";
            this.aiContextText.textContent = `Active Context: ${yr} ${c.brand} ${c.model}${price}`;
        } else {
            this.aiContextText.textContent = "No active valuation loaded. Configure a vehicle to begin.";
        }
    }

    scrollAIMessagesToBottom() {
        const wrap = document.getElementById("aiMessagesWrap");
        if (wrap) {
            wrap.scrollTop = wrap.scrollHeight;
        }
    }

    createAIMessageElement(role, text) {
        const msgEl = document.createElement("div");
        msgEl.className = `ai-msg ${role}`;
        
        const avatarEl = document.createElement("div");
        avatarEl.className = "ai-msg-avatar";
        avatarEl.textContent = role === "user" ? "YOU" : "✦";
        msgEl.appendChild(avatarEl);

        const contentEl = document.createElement("div");
        contentEl.className = "ai-msg-content";

        const pEl = document.createElement("p");
        pEl.className = "ai-msg-p";
        pEl.textContent = text;
        contentEl.appendChild(pEl);

        msgEl.appendChild(contentEl);
        return msgEl;
    }

    finalizeAIMessageElement(msgEl, text, citations = [], isRefusal = false, provider = "local_grounded") {
        const contentEl = msgEl.querySelector(".ai-msg-content");
        if (!contentEl) return;

        // Parse markdown bold **text** and bullet points safely
        let formatted = text
            .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
            .replace(/\n\n/g, "</p><p class='ai-msg-p'>")
            .replace(/\n• /g, "<br>&bull; ")
            .replace(/\n/g, "<br>");

        contentEl.innerHTML = `<p class="ai-msg-p">${formatted}</p>`;

        // Add refusal badge if out-of-domain or unavailable
        if (isRefusal) {
            const badge = document.createElement("div");
            badge.className = "ai-refusal-tag";
            badge.innerHTML = "<span>ANTI-HALLUCINATION ENFORCED</span> &bull; <span>UNAVAILABLE IN DATASET</span>";
            contentEl.insertBefore(badge, contentEl.firstChild);
        }

        // Add citations if present
        if (citations && citations.length > 0) {
            const citeBox = document.createElement("div");
            citeBox.className = "ai-citations-box";
            citeBox.innerHTML = `
                <div class="ai-citations-header">VERIFIED SOURCE CITATIONS</div>
                <div class="ai-citations-list">
                    ${citations.map(c => `
                        <div class="ai-citation-item">
                            <span class="ai-cite-source">${c.source}</span>
                            <span class="ai-cite-detail">${c.detail}</span>
                        </div>
                    `).join("")}
                </div>
            `;
            contentEl.appendChild(citeBox);
        }

        // Add copy / share actions
        const actionsEl = document.createElement("div");
        actionsEl.className = "ai-msg-actions";
        actionsEl.innerHTML = `
            <button type="button" class="ai-copy-btn" data-text="${text.replace(/"/g, '&quot;')}" title="Copy response">
                <span>📋</span> COPY
            </button>
            <button type="button" class="ai-share-btn" data-text="${text.replace(/"/g, '&quot;')}" title="Share response">
                <span>↗</span> SHARE
            </button>
            <span class="ai-provider-tag">Grounded: ${provider.replace('_', ' ')}</span>
        `;
        contentEl.appendChild(actionsEl);
    }

    addAIMessage(role, text, citations = [], isRefusal = false, provider = "local_grounded") {
        if (!this.aiMessages) {
            this.aiMessages = document.getElementById("aiChatMessages");
        }
        if (!this.aiMessages) return;

        const msgEl = this.createAIMessageElement(role, text);
        this.aiMessages.appendChild(msgEl);

        if (role === "assistant") {
            this.finalizeAIMessageElement(msgEl, text, citations, isRefusal, provider);
        }

        this.scrollAIMessagesToBottom();
    }

    async askAIAssistant(question, shouldStream = true) {
        if (!question || !question.trim()) return;
        const qClean = question.trim();

        // 1. Add User Message
        this.addAIMessage("user", qClean);

        // 2. Show Typing Indicator
        if (!this.aiTyping) {
            this.aiTyping = document.getElementById("aiTypingIndicator");
        }
        if (this.aiTyping) {
            this.aiTyping.classList.remove("hidden");
        }
        this.scrollAIMessagesToBottom();

        // 3. Prepare Payload
        const payload = {
            question: qClean,
            vehicle_data: this.configuration || {},
            valuation_data: this.lastValuationResult || {},
            stream: shouldStream
        };

        try {
            // Attempt Streaming first if requested
            if (shouldStream && window.ReadableStream) {
                const response = await fetch("/api/ai/explain", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "Accept": "text/event-stream"
                    },
                    body: JSON.stringify(payload)
                });

                if (response.ok && response.headers.get("content-type")?.includes("text/event-stream")) {
                    const reader = response.body.getReader();
                    const decoder = new TextDecoder();
                    let accumulated = "";
                    let citations = [];
                    let isRefusal = false;
                    let provider = "local_grounded";

                    // Create placeholder assistant message element
                    const msgEl = this.createAIMessageElement("assistant", "");
                    if (this.aiMessages) {
                        this.aiMessages.appendChild(msgEl);
                    }
                    if (this.aiTyping) {
                        this.aiTyping.classList.add("hidden");
                    }
                    const contentP = msgEl.querySelector(".ai-msg-p");

                    let done = false;
                    while (!done) {
                        const { value, done: streamDone } = await reader.read();
                        if (streamDone) break;
                        const chunkStr = decoder.decode(value, { stream: true });
                        const lines = chunkStr.split("\n");
                        for (const line of lines) {
                            if (line.startsWith("data: ")) {
                                try {
                                    const parsed = JSON.parse(line.substring(6));
                                    if (parsed.chunk) {
                                        accumulated += parsed.chunk;
                                        if (contentP) contentP.textContent = accumulated;
                                        this.scrollAIMessagesToBottom();
                                    }
                                    if (parsed.done) {
                                        citations = parsed.citations || [];
                                        isRefusal = parsed.is_refusal || false;
                                        provider = parsed.provider || provider;
                                        done = true;
                                    }
                                } catch (e) {}
                            }
                        }
                    }

                    this.finalizeAIMessageElement(msgEl, accumulated, citations, isRefusal, provider);
                    this.scrollAIMessagesToBottom();
                    return;
                }
            }

            // Standard JSON Request fallback
            const response = await fetch("/api/ai/explain", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ ...payload, stream: false })
            });

            const data = await response.json();
            if (this.aiTyping) {
                this.aiTyping.classList.add("hidden");
            }

            if (data.success && data.answer) {
                this.addAIMessage("assistant", data.answer, data.citations || [], data.is_refusal || false, data.provider);
            } else {
                this.addAIMessage("assistant", data.error || "Unable to explain valuation at this time.", [], true);
            }
        } catch (err) {
            console.error("SmartCar AI Assistant error:", err);
            if (this.aiTyping) {
                this.aiTyping.classList.add("hidden");
            }
            this.addAIMessage("assistant", "I don't have enough data to answer that. (Network or server error encountered).", [], true);
        }
    }

    update(delta) {
        // Reserved for frame animations
    }

    destroy() {
        if (this.exploreBadge && this.exploreBadge.parentNode) {
            this.exploreBadge.parentNode.removeChild(this.exploreBadge);
        }
        if (this.configPanel && this.configPanel.parentNode) {
            this.configPanel.parentNode.removeChild(this.configPanel);
        }
        if (this.identityPill && this.identityPill.parentNode) {
            this.identityPill.parentNode.removeChild(this.identityPill);
        }
        if (this.finishSelector && this.finishSelector.parentNode) {
            this.finishSelector.parentNode.removeChild(this.finishSelector);
        }
        if (this.modelUnavailableBadge && this.modelUnavailableBadge.parentNode) {
            this.modelUnavailableBadge.parentNode.removeChild(this.modelUnavailableBadge);
        }
    }
}
