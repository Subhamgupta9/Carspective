// ============================================================
// SMARTCAR AI — HIGH-TECH AUTOMOTIVE HUD & INTERACTIVE CONTROLLER
// hud.js — Full interactive animation and camera/vehicle controls
// ============================================================

import { SoundEngine } from "./sound.js";
import { setVehicleIdentity } from "./vehicleIdentity.js";

export class SmartCarHUD {
    constructor(experience) {
        this.exp = experience;
        this.activeCarId = "porsche-911";
        this.headlightsOn = true;
        this.autoRotateOn = false;
        this.activeColorId = "bronze";
        this.lightingMoodIndex = 0;

        // Lighting mood definitions (Phase 5 profiles)
        this.lightingMoods = [
            { id: "INSPECTION", name: "Studio Inspection", profile: "INSPECTION" },
            { id: "VALUATION",  name: "Valuation Showcase", profile: "VALUATION" },
            { id: "ARRIVAL",    name: "Cinematic Arrival", profile: "ARRIVAL" }
        ];

        // Vehicle Presets with verified Level 2 CarImages assets & dataset details
        this.vehiclePresets = [
            {
                id: "porsche-911",
                brand: "Porsche",
                model: "Porsche 911",
                generation: "992",
                year: 2021,
                variant: "Carrera 4S",
                fuel: "Petrol",
                trans: "Automatic",
                body: "Coupe",
                city: "Mumbai",
                km: 18500,
                owners: 1,
                powerScore: 98,
                healthScore: 94,
                engineTag: "Twin-Turbo 3.0L Flat-6",
                estBasePrice: 21600000
            },
            {
                id: "bmw-3series",
                brand: "BMW",
                model: "3 Series",
                generation: "g20",
                year: 2021,
                variant: "330i M Sport",
                fuel: "Petrol",
                trans: "Automatic",
                body: "Sedan",
                city: "Delhi",
                km: 25000,
                owners: 1,
                powerScore: 89,
                healthScore: 91,
                engineTag: "2.0L TwinPower Turbo",
                estBasePrice: 2800000
            },
            {
                id: "merc-cclass",
                brand: "Mercedes-Benz",
                model: "Mercedes-Benz C-Class",
                generation: "w206",
                year: 2022,
                variant: "C 220d",
                fuel: "Diesel",
                trans: "Automatic",
                body: "Sedan",
                city: "Bangalore",
                km: 21000,
                owners: 1,
                powerScore: 88,
                healthScore: 93,
                engineTag: "2.0L Turbo Diesel EQ-Boost",
                estBasePrice: 5200000
            },
            {
                id: "toyota-fortuner",
                brand: "Toyota",
                model: "Toyota Fortuner",
                generation: "an160",
                year: 2021,
                variant: "4x4 AT",
                fuel: "Diesel",
                trans: "Automatic",
                body: "SUV",
                city: "Pune",
                km: 38000,
                owners: 1,
                powerScore: 84,
                healthScore: 96,
                engineTag: "2.8L D-4D 4x4",
                estBasePrice: 3350000
            },
            {
                id: "hyundai-creta",
                brand: "Hyundai",
                model: "Creta",
                generation: "su2",
                year: 2022,
                variant: "SX(O)",
                fuel: "Petrol",
                trans: "Manual",
                body: "SUV",
                city: "Hyderabad",
                km: 24000,
                owners: 1,
                powerScore: 78,
                healthScore: 92,
                engineTag: "1.5L Smartstream MPi",
                estBasePrice: 1310000
            }
        ];

        this.init();
    }

    init() {
        this.bindGlobalAudioEvents();
        this.bindDirectorControls();
        this.bindPaintSwatches();
        this.bindVehicleDock();
        this.bindNavbarControls();
        this.updateTelemetryCard(this.vehiclePresets[0]);
        console.log("🔥 SmartCar HUD Controller Initialized 🔥");
    }

    // Attach audio hover/clicks to interactive elements
    bindGlobalAudioEvents() {
        document.addEventListener("click", (e) => {
            const btn = e.target.closest("button, .hud-btn, .color-swatch, .dock-card, .nav-link");
            if (btn) {
                SoundEngine.playClick();
            }
        });

        document.addEventListener("mouseover", (e) => {
            const btn = e.target.closest("button, .hud-btn, .color-swatch, .dock-card, .nav-link");
            if (btn && !btn.dataset.hoverSounded) {
                btn.dataset.hoverSounded = "true";
                SoundEngine.playHover();
                setTimeout(() => { delete btn.dataset.hoverSounded; }, 100);
            }
        });
    }

    // Bind 3D Director Dock (Right Side)
    bindDirectorControls() {
        const cam = this.exp.cameraController;
        const veh = this.exp.vehicle;
        const scene = this.exp.scene;

        // 1. Showroom 360 Spin
        const spinBtn = document.getElementById("hudSpinBtn");
        if (spinBtn) {
            spinBtn.addEventListener("click", () => {
                this.autoRotateOn = !this.autoRotateOn;
                if (cam && typeof cam.setPreset === "function") {
                    if (this.autoRotateOn) {
                        cam.setPreset("TURN_TABLE");
                    } else if (typeof cam.enableAutoRotate === "function") {
                        cam.enableAutoRotate(false);
                    }
                } else if (cam && typeof cam.enableAutoRotate === "function") {
                    cam.enableAutoRotate(this.autoRotateOn);
                }
                spinBtn.classList.toggle("active", this.autoRotateOn);
                this.showToast(this.autoRotateOn ? "360° TURNTABLE ROTATION: ACTIVE" : "TURNTABLE PAUSED");
            });
        }

        // 2. Hero 3/4 Stance
        const heroBtn = document.getElementById("hudHeroBtn");
        if (heroBtn) {
            heroBtn.addEventListener("click", () => {
                if (cam && typeof cam.setPreset === "function") {
                    cam.setPreset("HERO_34");
                } else if (cam && typeof cam.transitionToParkedHero === "function") {
                    cam.transitionToParkedHero(0, 0.75, 3.2);
                }
                this.setActiveDirectorBtn(heroBtn);
                this.showToast("CAMERA: HERO THREE-QUARTER STANCE");
            });
        }

        // 3. Side Profile
        const sideBtn = document.getElementById("hudSideBtn");
        if (sideBtn) {
            sideBtn.addEventListener("click", () => {
                if (cam && typeof cam.setPreset === "function") {
                    cam.setPreset("SIDE");
                } else if (cam && typeof cam.transitionTo === "function") {
                    cam.transitionTo({
                        spherical: { radius: 7.2, theta: Math.PI / 2, phi: 1.34 },
                        target: { x: 0, y: 0.75, z: 3.2 },
                        duration: 1.4,
                        easing: "easeInOutCubic"
                    });
                }
                this.setActiveDirectorBtn(sideBtn);
                this.showToast("CAMERA: AERODYNAMIC SIDE PROFILE");
            });
        }

        // 4. Front Stance & Headlights
        const frontBtn = document.getElementById("hudFrontBtn");
        if (frontBtn) {
            frontBtn.addEventListener("click", () => {
                if (cam && typeof cam.setPreset === "function") {
                    cam.setPreset("FRONT");
                } else if (cam && typeof cam.transitionTo === "function") {
                    cam.transitionTo({
                        spherical: { radius: 5.4, theta: 0.12, phi: 1.38 },
                        target: { x: 0, y: 0.65, z: 3.2 },
                        duration: 1.4,
                        easing: "easeInOutCubic"
                    });
                }
                this.setActiveDirectorBtn(frontBtn);
                this.showToast("CAMERA: FRONT GRILLE & ILLUMINATION");
            });
        }

        // 5. Rear Diffuser View
        const rearBtn = document.getElementById("hudRearBtn");
        if (rearBtn) {
            rearBtn.addEventListener("click", () => {
                if (cam && typeof cam.setPreset === "function") {
                    cam.setPreset("REAR");
                } else if (cam && typeof cam.transitionTo === "function") {
                    cam.transitionTo({
                        spherical: { radius: 5.8, theta: Math.PI - 0.25, phi: 1.35 },
                        target: { x: 0, y: 0.70, z: 3.2 },
                        duration: 1.4,
                        easing: "easeInOutCubic"
                    });
                }
                this.setActiveDirectorBtn(rearBtn);
                this.showToast("CAMERA: REAR STANCE & DIFFUSER");
            });
        }

        // 6. Top Orbital Drone View
        const topBtn = document.getElementById("hudTopBtn");
        if (topBtn) {
            topBtn.addEventListener("click", () => {
                if (cam && typeof cam.setPreset === "function") {
                    cam.setPreset("TOP_DRONE");
                } else if (cam && typeof cam.transitionTo === "function") {
                    cam.transitionTo({
                        spherical: { radius: 8.8, theta: 0.65, phi: 0.70 },
                        target: { x: 0, y: 0.75, z: 3.2 },
                        duration: 1.6,
                        easing: "easeInOutCubic"
                    });
                }
                this.setActiveDirectorBtn(topBtn);
                this.showToast("CAMERA: ORBITAL DRONE PERSPECTIVE");
            });
        }

        // 7. Headlights & Beams Toggle
        const lightBtn = document.getElementById("hudLightBtn");
        if (lightBtn) {
            lightBtn.addEventListener("click", () => {
                this.headlightsOn = !this.headlightsOn;
                if (veh && typeof veh.setHeadlights === "function") {
                    veh.setHeadlights(this.headlightsOn);
                }
                lightBtn.classList.toggle("active", this.headlightsOn);
                this.showToast(this.headlightsOn ? "HEADLIGHTS & BEAMS: ACTIVATED" : "HEADLIGHTS: STANDBY");
            });
        }

        // 8. Studio Lighting Mood Switcher
        const moodBtn = document.getElementById("hudMoodBtn");
        if (moodBtn) {
            moodBtn.addEventListener("click", () => {
                this.lightingMoodIndex = (this.lightingMoodIndex + 1) % this.lightingMoods.length;
                const mood = this.lightingMoods[this.lightingMoodIndex];
                this.applyLightingMood(mood);
                this.showToast(`STUDIO LIGHTING: ${mood.name.toUpperCase()}`);
            });
        }
    }

    setActiveDirectorBtn(targetBtn) {
        document.querySelectorAll(".director-dock .hud-btn").forEach(b => {
            if (b.id !== "hudSpinBtn" && b.id !== "hudLightBtn" && b.id !== "hudMoodBtn") {
                b.classList.remove("active");
            }
        });
        if (targetBtn) targetBtn.classList.add("active");
    }

    applyLightingMood(mood) {
        if (!this.exp.scene) return;
        const sceneInst = this.exp.scene;
        if (typeof sceneInst.setLightingProfile === "function" && mood.profile) {
            sceneInst.setLightingProfile(mood.profile);
            return;
        }
        if (sceneInst.ambientLight) {
            sceneInst.ambientLight.color.setHex(mood.ambient);
        }
        if (sceneInst.lights) {
            sceneInst.lights.traverse(l => {
                if (l.isDirectionalLight) {
                    l.color.setHex(mood.dir);
                }
            });
        }
        if (sceneInst.renderer) {
            sceneInst.renderer.toneMappingExposure = mood.exposure;
        }
    }

    // Bind Paint Finish Swatches (Floating Bottom Left)
    bindPaintSwatches() {
        const swatches = document.querySelectorAll(".paint-swatch-list .color-swatch");
        swatches.forEach(swatch => {
            swatch.addEventListener("click", () => {
                const colorHex = swatch.getAttribute("data-color");
                const colorId = swatch.getAttribute("data-id") || colorHex;
                const name = swatch.getAttribute("title") || colorId;

                swatches.forEach(s => s.classList.remove("active"));
                swatch.classList.add("active");
                this.activeColorId = colorId;

                if (this.exp.vehicle && typeof this.exp.vehicle.setBodyColor === "function") {
                    this.exp.vehicle.setBodyColor(colorHex);
                }

                this.showToast(`CAR PAINT: ${name.toUpperCase()}`);
            });
        });
    }

    // Bind Vehicle Showcase Dock (Bottom Center)
    bindVehicleDock() {
        const cards = document.querySelectorAll(".vehicle-dock-cards .dock-card");
        cards.forEach(card => {
            card.addEventListener("click", () => {
                const presetId = card.getAttribute("data-preset-id");

                if (presetId === "custom") {
                    // Open the 9-step configurator
                    if (this.exp.ui && typeof this.exp.ui.triggerConfigure === "function") {
                        this.exp.ui.triggerConfigure();
                    }
                    return;
                }

                const preset = this.vehiclePresets.find(p => p.id === presetId);
                if (!preset) return;

                cards.forEach(c => c.classList.remove("active"));
                card.classList.add("active");
                this.activeCarId = presetId;

                // 1. Play cybernetic swap sound
                SoundEngine.playCarSwap();

                // 2. Trigger holographic laser scanline
                this.triggerScannerAnimation(`SWAPPING VEHICLE TO ${preset.brand.toUpperCase()} ${preset.model.toUpperCase()}`);

                // 3. Load Level 2 3D Model with clean previous model disposal
                if (this.exp.vehicle) {
                    if (typeof this.exp.vehicle.unloadCurrentVehicle === "function") {
                        this.exp.vehicle.unloadCurrentVehicle();
                    }
                    if (typeof this.exp.vehicle.loadVehicle === "function") {
                        this.exp.vehicle.loadVehicle({
                            brand: preset.brand,
                            model: preset.model,
                            year: preset.year,
                            fuel: preset.fuel,
                            transmission: preset.trans,
                            bodyType: preset.body
                        });
                    }
                }

                // 4. Sync configuration in UI for instant 1-click valuation
                if (this.exp.ui) {
                    this.exp.ui.configuration = {
                        brand: preset.brand,
                        model: preset.model,
                        generation: preset.generation || "",
                        manufacturing_year: preset.year,
                        variant: preset.variant || "Standard",
                        km_driven: preset.km,
                        fuel_type: preset.fuel,
                        transmission_type: preset.trans,
                        city: preset.city,
                        bodytype: preset.body,
                        number_of_owners: preset.owners
                    };
                    setVehicleIdentity({
                        brand: preset.brand,
                        model: preset.model,
                        generation: preset.generation || "",
                        manufacturing_year: preset.year,
                        variant: preset.variant || "Standard",
                        fuel_type: preset.fuel,
                        transmission_type: preset.trans,
                        city: preset.city,
                        bodytype: preset.body,
                        owners: preset.owners
                    });
                    if (typeof this.exp.ui.updateVehicleIdentity === "function") {
                        this.exp.ui.updateVehicleIdentity();
                    }
                }

                // 5. Update Telemetry Card with skeleton transition
                this.showTelemetrySkeleton();
                setTimeout(() => {
                    this.updateTelemetryCard(preset);
                }, 120);
                this.showToast(`ACTIVE VEHICLE: ${preset.brand} ${preset.model} (${preset.year})`);
            });
        });
    }

    showTelemetrySkeleton() {
        const skel = document.getElementById("telemetrySkeleton");
        const content = document.getElementById("telemetryContent");
        if (skel) skel.classList.remove("hidden");
        if (content) content.classList.add("hidden");
    }

    hideTelemetrySkeleton() {
        const skel = document.getElementById("telemetrySkeleton");
        const content = document.getElementById("telemetryContent");
        if (skel) skel.classList.add("hidden");
        if (content) content.classList.remove("hidden");
    }

    // Update Top-Left Telemetry Card
    updateTelemetryCard(preset) {
        if (!preset) return;

        const titleEl = document.getElementById("hudVehicleTitle");
        const subtitleEl = document.getElementById("hudVehicleSubtitle");
        const powerBar = document.getElementById("hudPowerFill");
        const powerVal = document.getElementById("hudPowerVal");
        const healthBar = document.getElementById("hudHealthFill");
        const healthVal = document.getElementById("hudHealthVal");
        const engineEl = document.getElementById("hudEngineTag");
        const estPriceEl = document.getElementById("hudEstBallpark");

        if (titleEl) titleEl.textContent = `${preset.brand} ${preset.model}`;
        if (subtitleEl) subtitleEl.textContent = `${preset.year} • ${preset.body} • ${preset.fuel}`;
        if (powerBar) powerBar.style.width = `${preset.powerScore}%`;
        if (powerVal) powerVal.textContent = `${preset.powerScore}/100`;
        if (healthBar) healthBar.style.width = `${preset.healthScore}%`;
        if (healthVal) healthVal.textContent = `${preset.healthScore}%`;
        if (engineEl) engineEl.textContent = preset.engineTag || "Verified Powertrain";

        if (estPriceEl && preset.estBasePrice) {
            estPriceEl.textContent = `Est. ₹${(preset.estBasePrice / 100000).toFixed(1)} Lakh`;
        }

        this.hideTelemetrySkeleton();
    }

    // Bind Navbar Audio & Quick Valuation Controls
    bindNavbarControls() {
        // Audio Toggle
        const audioBtn = document.getElementById("hudAudioToggle");
        if (audioBtn) {
            const updateAudioIcon = () => {
                const muted = SoundEngine.isMuted();
                audioBtn.innerHTML = muted ? `<span>🔇</span><span>SOUND OFF</span>` : `<span>🔊</span><span>SOUND ON</span>`;
                audioBtn.classList.toggle("muted", muted);
            };
            updateAudioIcon();
            audioBtn.addEventListener("click", () => {
                SoundEngine.toggleMute();
                updateAudioIcon();
                this.showToast(SoundEngine.isMuted() ? "AUDIO MUTED" : "SYNTH AUDIO ACTIVATED");
            });
        }

        // Quick Valuate Button in Navbar
        const instantValuateBtn = document.getElementById("hudInstantValuateBtn");
        if (instantValuateBtn) {
            instantValuateBtn.addEventListener("click", () => {
                this.executeInstantValuation();
            });
        }

        // Instant Valuate from Telemetry Card
        const telemetryValuateBtn = document.getElementById("hudTelemetryValuateBtn");
        if (telemetryValuateBtn) {
            telemetryValuateBtn.addEventListener("click", () => {
                this.executeInstantValuation();
            });
        }
    }

    // Run instant valuation with holographic scanning flair
    executeInstantValuation() {
        if (!this.exp.ui) return;

        // Ensure configuration is populated from active preset if not already configured
        const preset = this.vehiclePresets.find(p => p.id === this.activeCarId) || this.vehiclePresets[0];
        if (!this.exp.ui.configuration.brand || !this.exp.ui.configuration.model) {
            this.exp.ui.configuration = {
                brand: preset.brand,
                model: preset.model,
                generation: preset.generation || "",
                manufacturing_year: preset.year,
                variant: preset.variant || "Standard",
                km_driven: preset.km,
                fuel_type: preset.fuel,
                transmission_type: preset.trans,
                city: preset.city,
                bodytype: preset.body,
                number_of_owners: preset.owners
            };
            setVehicleIdentity({
                brand: preset.brand,
                model: preset.model,
                generation: preset.generation || "",
                manufacturing_year: preset.year,
                variant: preset.variant || "Standard",
                fuel_type: preset.fuel,
                transmission_type: preset.trans,
                city: preset.city,
                bodytype: preset.body,
                owners: preset.owners
            });
            if (typeof this.exp.ui.updateVehicleIdentity === "function") {
                this.exp.ui.updateVehicleIdentity();
            }
        }

        SoundEngine.playScan();
        this.triggerScannerAnimation("COMPUTING REAL ML VALUATION (R² 0.8993)...", 1400);

        setTimeout(() => {
            if (typeof this.exp.ui.openConfigurator === "function") {
                this.exp.ui.openConfigurator(10); // Go straight to review & calculate
            }
            if (typeof this.exp.ui.executeValuation === "function") {
                this.exp.ui.executeValuation();
            }
        }, 600);
    }

    // Holographic Scanner Overlay
    triggerScannerAnimation(message = "SCANNING VEHICLE SPECIFICATIONS...", duration = 1200) {
        const scanner = document.getElementById("hologramScannerOverlay");
        const scanMsg = document.getElementById("scannerStatusMsg");

        if (scanner) {
            if (scanMsg) scanMsg.textContent = message;
            scanner.classList.add("active");
            setTimeout(() => {
                scanner.classList.remove("active");
            }, duration);
        }
    }

    // Toast Notification Banner
    showToast(text) {
        let toast = document.getElementById("hudToast");
        if (!toast) {
            toast = document.createElement("div");
            toast.id = "hudToast";
            toast.className = "hud-toast";
            document.body.appendChild(toast);
        }

        toast.textContent = text;
        toast.classList.add("visible");
        clearTimeout(this._toastTimer);
        this._toastTimer = setTimeout(() => {
            toast.classList.remove("visible");
        }, 2200);
    }
}
