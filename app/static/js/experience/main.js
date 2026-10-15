// ============================================================
// SMARTCAR AI — EXPERIENCE BOOTSTRAP
// main.js
// ============================================================

import * as THREE from "three";
import { SmartCarScene } from "./scene.js";
import { SmartCarCamera } from "./camera.js";
import { SmartCarVehicle } from "./vehicle.js";
import { SmartCarInteraction } from "./interaction.js";
import { VehicleAnimator, SmartCarAnimation, VehicleState } from "./animation.js";
import { SmartCarUI, CINEMATIC_VALUATION_STAGES } from "./ui.js";
import { SmartCarPrediction } from "./prediction.js";
import { SmartCarStory, StoryChapter } from "./story.js";
import { getVehicleIdentity, isVehicleIdentityReadyForAsset } from "./vehicleIdentity.js";
import { SmartCarHUD } from "./hud.js";

// ============================================================
// APPLICATION STATE
// ============================================================

const SmartCarExperience = {
    scene: null,
    cameraController: null,
    vehicle: null,
    interaction: null,
    animation: null,
    ui: null,
    prediction: null,
    story: null,
    initialized: false,
    canvas: null
};

// ============================================================
// INITIALIZE
// ============================================================

function initializeExperience() {
    if (SmartCarExperience.initialized) {
        return;
    }

    const canvas = document.getElementById("experienceCanvas");

    if (!canvas) {
        console.error("SmartCar AI: #experienceCanvas not found.");
        return;
    }

    SmartCarExperience.canvas = canvas;

    try {
        // ----------------------------------------------------
        // PREDICTION SERVICE
        // ----------------------------------------------------
        SmartCarExperience.prediction = new SmartCarPrediction();

        // ----------------------------------------------------
        // SCENE
        // ----------------------------------------------------
        SmartCarExperience.scene = new SmartCarScene(canvas);

        // ----------------------------------------------------
        // CAMERA
        // ----------------------------------------------------
        SmartCarExperience.cameraController = new SmartCarCamera(
            SmartCarExperience.scene.getCamera()
        );

        // ----------------------------------------------------
        // UI
        // ----------------------------------------------------
        SmartCarExperience.ui = new SmartCarUI(
            SmartCarExperience.prediction,
            SmartCarExperience.cameraController
        );

        // ----------------------------------------------------
        // VEHICLE
        // ----------------------------------------------------
        SmartCarExperience.vehicle = new SmartCarVehicle(
            SmartCarExperience.scene.getScene()
        );

        // ----------------------------------------------------
        // INTERACTION
        // ----------------------------------------------------
        SmartCarExperience.interaction = new SmartCarInteraction(
            canvas,
            SmartCarExperience.cameraController
        );

        // Connect interaction activity callbacks to UI HUD fading and animation interrupt
        SmartCarExperience.interaction.onInteractionStart = () => {
            if (SmartCarExperience.animation && typeof SmartCarExperience.animation.interrupt === "function") {
                SmartCarExperience.animation.interrupt();
            }
            if (SmartCarExperience.ui && typeof SmartCarExperience.ui.onUserInteraction === "function") {
                SmartCarExperience.ui.onUserInteraction(true);
            }
        };

        SmartCarExperience.interaction.onInteractionEnd = () => {
            if (SmartCarExperience.ui && typeof SmartCarExperience.ui.onUserInteraction === "function") {
                SmartCarExperience.ui.onUserInteraction(false);
            }
        };

        // ----------------------------------------------------
        // ANIMATION CONTROLLER (PHASE 6 VEHICLE ANIMATOR)
        // ----------------------------------------------------
        SmartCarExperience.animation = new VehicleAnimator(
            SmartCarExperience.vehicle,
            SmartCarExperience.cameraController,
            SmartCarExperience.ui
        );

        // ----------------------------------------------------
        // CINEMATIC STORY CONTROLLER (PHASE 8)
        // ----------------------------------------------------
        SmartCarExperience.story = new SmartCarStory(
            SmartCarExperience.ui,
            SmartCarExperience.cameraController,
            SmartCarExperience.animation
        );

        if (SmartCarExperience.ui && typeof SmartCarExperience.ui.setStoryController === "function") {
            SmartCarExperience.ui.setStoryController(SmartCarExperience.story);
        }
        if (SmartCarExperience.animation && typeof SmartCarExperience.animation.setStoryController === "function") {
            SmartCarExperience.animation.setStoryController(SmartCarExperience.story);
        }

        // ----------------------------------------------------
        // DYNAMIC 3D VEHICLE SELECTION WIRING (LEVEL 2 IDENTITY)
        // ----------------------------------------------------
        if (SmartCarExperience.vehicle && SmartCarExperience.ui) {
            // Configuration change triggers dynamic 3D asset matching/loading when identity is ready
            SmartCarExperience.ui.onConfigurationChange((config) => {
                const identity = getVehicleIdentity();
                if (isVehicleIdentityReadyForAsset()) {
                    // Phase 3: Explicitly dispose previous model hierarchy before loading new vehicle
                    if (typeof SmartCarExperience.vehicle.unloadCurrentVehicle === "function") {
                        SmartCarExperience.vehicle.unloadCurrentVehicle();
                    }
                    SmartCarExperience.vehicle.loadVehicle(identity);
                }
            });

            // Vehicle asset ready callback -> adapt camera framing & restore UI
            SmartCarExperience.vehicle.onAssetReady((entry, boundingBox, metadata) => {
                if (SmartCarExperience.cameraController && typeof SmartCarExperience.cameraController.adaptToVehicle === "function") {
                    SmartCarExperience.cameraController.adaptToVehicle(metadata, boundingBox);
                }
                if (SmartCarExperience.scene && typeof SmartCarExperience.scene.updateContactShadow === "function" && boundingBox) {
                    const size = new THREE.Vector3();
                    boundingBox.getSize(size);
                    const center = new THREE.Vector3();
                    boundingBox.getCenter(center);
                    SmartCarExperience.scene.updateContactShadow(center.z, size.z, size.x);
                }
                if (SmartCarExperience.ui && typeof SmartCarExperience.ui.set3DModelAvailable === "function") {
                    SmartCarExperience.ui.set3DModelAvailable(entry);
                }
            });

            // Vehicle asset unavailable callback -> show controlled unavailable state
            SmartCarExperience.vehicle.onAssetUnavailable((brand, model, data) => {
                if (SmartCarExperience.ui && typeof SmartCarExperience.ui.set3DModelUnavailable === "function") {
                    SmartCarExperience.ui.set3DModelUnavailable(brand, model, data);
                }
            });
        }

        // ----------------------------------------------------
        // INTERACTIVE AUTOMOTIVE HUD CONTROLLER
        // ----------------------------------------------------
        SmartCarExperience.hud = new SmartCarHUD(SmartCarExperience);

        // ----------------------------------------------------
        // SINGLE CENTRAL UPDATE LOOP
        // ----------------------------------------------------
        const sceneInstance = SmartCarExperience.scene;
        const originalUpdate = sceneInstance.update.bind(sceneInstance);

        sceneInstance.update = function(delta) {
            originalUpdate(delta);

            if (SmartCarExperience.vehicle) {
                SmartCarExperience.vehicle.update(delta);
            }

            if (SmartCarExperience.animation) {
                SmartCarExperience.animation.update(delta);
            }

            if (SmartCarExperience.cameraController) {
                SmartCarExperience.cameraController.update(delta);
            }

            if (SmartCarExperience.ui) {
                SmartCarExperience.ui.update(delta);
            }

            if (SmartCarExperience.story) {
                SmartCarExperience.story.update(delta);
            }
        };

        // ----------------------------------------------------
        // READY
        // ----------------------------------------------------
        SmartCarExperience.initialized = true;

        updateStatus("EXPERIENCE INITIALIZED");
        console.log("SmartCar AI: Experience initialized successfully.");

    } catch (error) {
        console.error("SmartCar AI: Experience initialization failed.", error);
        updateStatus("EXPERIENCE ERROR");
    }
}

// ============================================================
// STATUS
// ============================================================

function updateStatus(message) {
    const status = document.getElementById("experienceStatus");
    if (!status) {
        return;
    }
    status.textContent = message;
}

// ============================================================
// DOM READY
// ============================================================

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeExperience);
} else {
    initializeExperience();
}

// ============================================================
// GLOBAL EXPERIENCE API
// ============================================================

window.smartCarExperience = {
    getScene() {
        return SmartCarExperience.scene?.getScene();
    },

    getSceneInstance() {
        return SmartCarExperience.scene;
    },

    getCamera() {
        return SmartCarExperience.scene?.getCamera();
    },

    getCameraController() {
        return SmartCarExperience.cameraController;
    },

    getRenderer() {
        return SmartCarExperience.scene?.getRenderer();
    },

    getVehicle() {
        return SmartCarExperience.vehicle;
    },

    getInteraction() {
        return SmartCarExperience.interaction;
    },

    getAnimation() {
        return SmartCarExperience.animation;
    },

    getUI() {
        return SmartCarExperience.ui;
    },

    getHUD() {
        return SmartCarExperience.hud;
    },

    getConfigurator() {
        return SmartCarExperience.ui;
    },

    getConfiguration() {
        return SmartCarExperience.ui?.getConfiguration();
    },

    get vehicleConfig() {
        return SmartCarExperience.ui?.configuration;
    },

    getPredictionService() {
        return SmartCarExperience.prediction;
    },

    setStatus(message) {
        updateStatus(message);
    },

    getState() {
        return SmartCarExperience.animation?.getState() || SmartCarExperience.ui?.getAppState() || "UNKNOWN";
    },

    getAppState() {
        return SmartCarExperience.ui?.getAppState() || SmartCarExperience.animation?.getState() || "UNKNOWN";
    },

    setState(state) {
        if (SmartCarExperience.animation) {
            SmartCarExperience.animation.setState(state);
        }
        if (SmartCarExperience.ui) {
            SmartCarExperience.ui.setAppState(state);
        }
    },

    startInspection() {
        if (SmartCarExperience.animation) {
            SmartCarExperience.animation.setState("INSPECTING");
        }
        if (SmartCarExperience.ui && typeof SmartCarExperience.ui.showInspectionMode === "function") {
            SmartCarExperience.ui.showInspectionMode();
        }
        if (SmartCarExperience.cameraController && typeof SmartCarExperience.cameraController.transitionToInspection === "function") {
            SmartCarExperience.cameraController.transitionToInspection(0, 0.75, 3.2);
        }
    },

    startConfiguring() {
        if (SmartCarExperience.animation) {
            SmartCarExperience.animation.setState("CONFIGURING");
        }
        if (SmartCarExperience.ui && typeof SmartCarExperience.ui.triggerConfigure === "function") {
            SmartCarExperience.ui.triggerConfigure();
        }
    },

    getStory() {
        return SmartCarExperience.story;
    },

    getChapter() {
        return SmartCarExperience.story?.getChapterNumber() || 1;
    },

    setChapter(chapterId) {
        if (SmartCarExperience.story) {
            SmartCarExperience.story.setChapter(chapterId);
        }
    },

    loadVehicleAsset(brand, model) {
        return SmartCarExperience.vehicle?.loadVehicleAsset(brand, model);
    },

    switchVehicle(identity) {
        if (SmartCarExperience.vehicle) {
            if (typeof SmartCarExperience.vehicle.unloadCurrentVehicle === "function") {
                SmartCarExperience.vehicle.unloadCurrentVehicle();
            }
            return SmartCarExperience.vehicle.loadVehicle(identity);
        }
        return Promise.resolve(false);
    },

    disposeVehicle() {
        if (SmartCarExperience.vehicle && typeof SmartCarExperience.vehicle.unloadCurrentVehicle === "function") {
            SmartCarExperience.vehicle.unloadCurrentVehicle();
        }
    },

    getVehicleLoader() {
        return SmartCarExperience.vehicle?.vehicleLoader;
    },

    getCurrentAsset() {
        return SmartCarExperience.vehicle?.getCurrentAsset();
    },

    hasVehicleAsset() {
        return SmartCarExperience.vehicle?.hasAsset();
    },

    // Phase 5: Premium Automotive Rendering & Camera API
    setLightingProfile(profileName, immediate = false) {
        return SmartCarExperience.scene?.setLightingProfile(profileName, immediate);
    },

    getLightingProfile() {
        return SmartCarExperience.scene?.getLightingProfile();
    },

    getLightingProfiles() {
        return SmartCarExperience.scene?.getLightingProfiles() || [];
    },

    setCameraPreset(presetName, onComplete = null) {
        return SmartCarExperience.cameraController?.setPreset(presetName, onComplete);
    },

    getCameraPreset() {
        return SmartCarExperience.cameraController?.getPreset();
    },

    getCameraPresets() {
        return SmartCarExperience.cameraController?.getPresets() || [];
    },

    autoFrameVehicle(objectOrBox, padding = 1.22) {
        return SmartCarExperience.cameraController?.autoFrameVehicle(objectOrBox, padding);
    },

    // Phase 6: Vehicle Animation & Cinematic Sequences
    playSequence(sequenceName = "arrival") {
        return SmartCarExperience.animation?.playSequence(sequenceName);
    },

    interruptAnimation() {
        return SmartCarExperience.animation?.interrupt();
    },

    getAnimator() {
        return SmartCarExperience.animation;
    },

    isReady() {
        return SmartCarExperience.initialized;
    },

    // Phase 9: Market Intelligence & Comparables API
    fetchMarketIntelligence(brand, model, options = {}) {
        return SmartCarExperience.ui?.fetchMarketIntelligence(brand, model, options);
    },

    // Phase 10: AI Explanation Assistant API
    openAIAssistant(prefilledQuestion = null) {
        return SmartCarExperience.ui?.openAIAssistant(prefilledQuestion);
    },
    closeAIAssistant() {
        return SmartCarExperience.ui?.closeAIAssistant();
    },
    askAI(question) {
        return SmartCarExperience.ui?.askAIAssistant(question);
    },
    getMemoryStats() {
        return SmartCarExperience.vehicle?.getMemoryStats() || null;
    }
};

// ============================================================
// PHASE 6 GLOBAL CANONICAL API: window.__SMARTCAR__
// ============================================================

window.__SMARTCAR__ = {
    get animator() {
        return SmartCarExperience.animation;
    },
    get experience() {
        return window.smartCarExperience;
    },
    get scene() {
        return SmartCarExperience.scene;
    },
    get camera() {
        return SmartCarExperience.cameraController;
    },
    get vehicle() {
        return SmartCarExperience.vehicle;
    },
    get ui() {
        return SmartCarExperience.ui;
    },
    get hud() {
        return SmartCarExperience.hud;
    },
    get valuationStages() {
        return CINEMATIC_VALUATION_STAGES;
    },
    runValuationFlow() {
        if (SmartCarExperience.ui && typeof SmartCarExperience.ui.executeValuation === "function") {
            return SmartCarExperience.ui.executeValuation();
        }
    },
    fetchMarketIntelligence(brand, model, options = {}) {
        if (SmartCarExperience.ui && typeof SmartCarExperience.ui.fetchMarketIntelligence === "function") {
            return SmartCarExperience.ui.fetchMarketIntelligence(brand, model, options);
        }
        return Promise.reject(new Error("UI not initialized"));
    },
    openAIAssistant(prefilledQuestion = null) {
        if (SmartCarExperience.ui && typeof SmartCarExperience.ui.openAIAssistant === "function") {
            return SmartCarExperience.ui.openAIAssistant(prefilledQuestion);
        }
    },
    closeAIAssistant() {
        if (SmartCarExperience.ui && typeof SmartCarExperience.ui.closeAIAssistant === "function") {
            return SmartCarExperience.ui.closeAIAssistant();
        }
    },
    askAI(question) {
        if (SmartCarExperience.ui && typeof SmartCarExperience.ui.askAIAssistant === "function") {
            return SmartCarExperience.ui.askAIAssistant(question);
        }
        return Promise.reject(new Error("UI not initialized"));
    },
    getMemoryStats() {
        return SmartCarExperience.vehicle?.getMemoryStats() || null;
    }
};