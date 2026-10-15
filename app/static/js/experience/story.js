// ============================================================
// SMARTCAR AI — CINEMATIC STORY & CHAPTER SYSTEM
// story.js
// ============================================================

export const StoryChapter = {
    VEHICLE: 1,
    INSPECT: 2,
    CONFIGURE: 3,
    VALUATE: 4,
    REAL_VALUE: 5
};

export const ChapterConfig = {
    [StoryChapter.VEHICLE]: {
        id: 1,
        number: "01",
        title: "THE VEHICLE",
        subtitle: "Every vehicle carries a story.",
        actionText: "INSPECT VEHICLE &rarr;",
        actionId: "storyInspectBtn"
    },
    [StoryChapter.INSPECT]: {
        id: 2,
        number: "02",
        title: "INSPECT",
        subtitle: "Look closer.",
        actionText: "CONTINUE &rarr;",
        actionId: "startConfigBtn" // Preserves canonical trigger for configurator
    },
    [StoryChapter.CONFIGURE]: {
        id: 3,
        number: "03",
        title: "CONFIGURE",
        subtitle: "What car are we valuing?",
        actionText: null,
        actionId: null
    },
    [StoryChapter.VALUATE]: {
        id: 4,
        number: "04",
        title: "VALUATE",
        subtitle: "Let's find its real value.",
        actionText: null, // Primary action handled by configurator step 10
        actionId: null
    },
    [StoryChapter.REAL_VALUE]: {
        id: 5,
        number: "05",
        title: "THE REAL VALUE",
        subtitle: "REAL MARKET ESTIMATE",
        actionText: null,
        actionId: null
    }
};

export class SmartCarStory {

    constructor(uiController = null, cameraController = null, animationController = null) {
        this.uiController = uiController;
        this.cameraController = cameraController;
        this.animationController = animationController;

        this.currentChapter = StoryChapter.VEHICLE;
        this.isTransitioning = false;

        this.overlayElement = document.getElementById("experienceOverlay");
        this.indicatorElement = null;
        this.editorialElement = null;

        // Custom lifecycle listeners
        this.listeners = [];

        this.initDOM();
    }

    setUIController(ui) {
        this.uiController = ui;
    }

    setCameraController(cam) {
        this.cameraController = cam;
    }

    setAnimationController(anim) {
        this.animationController = anim;
    }

    // ========================================================
    // INITIALIZATION & DOM CREATION
    // ========================================================

    initDOM() {
        if (!this.overlayElement) {
            console.warn("SmartCar Story: #experienceOverlay not found.");
            return;
        }

        // Hide legacy static intro if present to give editorial layer full dominance
        const intro = document.querySelector(".experience-intro");
        if (intro) {
            intro.style.display = "none";
        }
        const hint = document.querySelector(".experience-hint");
        if (hint) {
            hint.style.display = "none";
        }

        this.createChapterIndicator();
        this.createEditorialLayer();

        // Render initial Chapter 01
        this.renderChapter(this.currentChapter, true);
    }

    /**
     * Create subtle, minimal chapter indicator: 01 / 02 / 03 / 04 / 05
     */
    createChapterIndicator() {
        const existing = document.getElementById("storyChapterIndicator");
        if (existing) {
            existing.remove();
        }

        const indicator = document.createElement("div");
        indicator.id = "storyChapterIndicator";
        indicator.className = "story-chapter-indicator";
        indicator.setAttribute("role", "navigation");
        indicator.setAttribute("aria-label", "Experience Chapters");

        indicator.innerHTML = `
            <div class="story-indicator-track">
                <button type="button" class="story-indicator-step active" data-chapter="1" title="Chapter 01: The Vehicle">
                    <span class="story-ind-num">01</span>
                    <span class="story-ind-name">THE VEHICLE</span>
                </button>
                <span class="story-ind-sep">/</span>
                <button type="button" class="story-indicator-step" data-chapter="2" title="Chapter 02: Inspect">
                    <span class="story-ind-num">02</span>
                    <span class="story-ind-name">INSPECT</span>
                </button>
                <span class="story-ind-sep">/</span>
                <button type="button" class="story-indicator-step" data-chapter="3" title="Chapter 03: Configure">
                    <span class="story-ind-num">03</span>
                    <span class="story-ind-name">CONFIGURE</span>
                </button>
                <span class="story-ind-sep">/</span>
                <button type="button" class="story-indicator-step" data-chapter="4" title="Chapter 04: Valuate">
                    <span class="story-ind-num">04</span>
                    <span class="story-ind-name">VALUATE</span>
                </button>
                <span class="story-ind-sep">/</span>
                <button type="button" class="story-indicator-step" data-chapter="5" title="Chapter 05: The Real Value">
                    <span class="story-ind-num">05</span>
                    <span class="story-ind-name">THE REAL VALUE</span>
                </button>
            </div>
        `;

        this.overlayElement.appendChild(indicator);
        this.indicatorElement = indicator;

        // Interactive subtle step clicking
        indicator.querySelectorAll(".story-indicator-step").forEach(btn => {
            btn.addEventListener("click", () => {
                const targetChapter = parseInt(btn.dataset.chapter, 10);
                this.requestChapterNavigation(targetChapter);
            });
        });
    }

    /**
     * Create minimal editorial typography overlay.
     */
    createEditorialLayer() {
        const existing = document.getElementById("storyEditorialLayer");
        if (existing) {
            existing.remove();
        }

        const layer = document.createElement("div");
        layer.id = "storyEditorialLayer";
        layer.className = "story-editorial-layer";

        layer.innerHTML = `
            <div class="story-editorial-card" id="storyEditorialCard">
                <div class="story-editorial-tag" id="storyEditorialTag">01</div>
                <h1 class="story-editorial-title" id="storyEditorialTitle">THE VEHICLE</h1>
                <div class="story-editorial-sub" id="storyEditorialSub">Every vehicle carries a story.</div>
                <div class="story-editorial-actions" id="storyEditorialActions"></div>
            </div>
        `;

        this.overlayElement.appendChild(layer);
        this.editorialElement = layer;
    }

    // ========================================================
    // STATE & CHAPTER SYNCHRONIZATION
    // ========================================================

    getChapter() {
        return {
            chapter: this.currentChapter,
            ...ChapterConfig[this.currentChapter]
        };
    }

    getChapterNumber() {
        return this.currentChapter;
    }

    /**
     * Transition cleanly to a target chapter.
     */
    setChapter(targetChapter, options = {}) {
        const ch = Number(targetChapter);
        if (isNaN(ch) || ch < 1 || ch > 5) {
            console.warn(`SmartCar Story: Invalid chapter ${targetChapter}`);
            return;
        }

        if (this.currentChapter === ch && !options.force) {
            return;
        }

        const prevChapter = this.currentChapter;
        this.currentChapter = ch;
        console.log(`SmartCar Story: Chapter ${prevChapter} → Chapter ${ch} (${ChapterConfig[ch].title})`);

        this.renderChapter(ch);

        // Drive deliberate automotive hero camera compositions per chapter
        if (this.cameraController) {
            if (ch === StoryChapter.VEHICLE) {
                if (typeof this.cameraController.transitionToParkedHero === "function") {
                    this.cameraController.transitionToParkedHero();
                }
            } else if (ch === StoryChapter.INSPECT) {
                if (typeof this.cameraController.transitionToInspection === "function") {
                    this.cameraController.transitionToInspection();
                }
            } else if (ch === StoryChapter.CONFIGURE) {
                if (typeof this.cameraController.transitionToConfiguration === "function") {
                    this.cameraController.transitionToConfiguration();
                }
            } else if (ch === StoryChapter.VALUATE) {
                if (typeof this.cameraController.transitionToValuation === "function") {
                    this.cameraController.transitionToValuation();
                }
            } else if (ch === StoryChapter.REAL_VALUE) {
                if (typeof this.cameraController.transitionToFinalValue === "function") {
                    this.cameraController.transitionToFinalValue();
                }
            }
        }

        // Drive matching lighting profiles per chapter
        if (typeof window !== "undefined" && window.smartCarExperience) {
            const sceneInstance = window.smartCarExperience.getSceneInstance();
            if (sceneInstance && typeof sceneInstance.setLightingProfile === "function") {
                if (ch === StoryChapter.VEHICLE || ch === StoryChapter.INSPECT || ch === StoryChapter.CONFIGURE) {
                    sceneInstance.setLightingProfile("INSPECTION");
                } else if (ch === StoryChapter.VALUATE) {
                    sceneInstance.setLightingProfile("VALUATION");
                } else if (ch === StoryChapter.REAL_VALUE) {
                    sceneInstance.setLightingProfile("RESULT");
                }
            }
        }

        // Notify registered subscribers
        this.notifyListeners(ch, prevChapter);
    }

    /**
     * Synchronize story chapter based on authoritative experience state.
     */
    syncWithExperienceState(state, context = {}) {
        if (!state) return;

        switch (state) {
            case "ARRIVING":
            case "APPROACHING":
            case "BRAKING":
            case "PARKING":
            case "DRIVE":
            case "APPROACH":
            case "BRAKE":
            case "PARK":
                this.setChapter(StoryChapter.VEHICLE);
                break;

            case "IDLE":
                // In IDLE, if user hasn't explicitly entered inspection, stay on Chapter 01
                if (this.currentChapter !== StoryChapter.INSPECT && 
                    this.currentChapter !== StoryChapter.CONFIGURE && 
                    this.currentChapter !== StoryChapter.VALUATE && 
                    this.currentChapter !== StoryChapter.REAL_VALUE) {
                    this.setChapter(StoryChapter.VEHICLE);
                }
                break;

            case "INSPECTING":
            case "TURNTABLE":
                this.setChapter(StoryChapter.INSPECT);
                break;

            case "CONFIGURING":
                if (context && context.step === 10) {
                    this.setChapter(StoryChapter.VALUATE);
                } else {
                    this.setChapter(StoryChapter.CONFIGURE);
                }
                break;

            case "VALUATION_READY":
            case "VALUATING":
                this.setChapter(StoryChapter.VALUATE);
                break;

            case "VALUATION_RESULT":
                this.setChapter(StoryChapter.REAL_VALUE);
                break;

            default:
                break;
        }
    }

    // ========================================================
    // CHAPTER RENDERING & EDITORIAL TRANSITIONS
    // ========================================================

    renderChapter(chapterId, immediate = false) {
        const config = ChapterConfig[chapterId];
        if (!config) return;

        // 1. Update Chapter Indicator UI
        if (this.indicatorElement) {
            const steps = this.indicatorElement.querySelectorAll(".story-indicator-step");
            steps.forEach(step => {
                const stepCh = parseInt(step.dataset.chapter, 10);
                step.classList.remove("active", "completed", "pending");
                if (stepCh === chapterId) {
                    step.classList.add("active");
                } else if (stepCh < chapterId) {
                    step.classList.add("completed");
                } else {
                    step.classList.add("pending");
                }
            });
        }

        // 2. Update Editorial Typography Layer
        const card = document.getElementById("storyEditorialCard");
        const tagEl = document.getElementById("storyEditorialTag");
        const titleEl = document.getElementById("storyEditorialTitle");
        const subEl = document.getElementById("storyEditorialSub");
        const actionsEl = document.getElementById("storyEditorialActions");

        if (!card || !tagEl || !titleEl || !subEl || !actionsEl) return;

        const updateContent = () => {
            tagEl.textContent = config.number;
            titleEl.textContent = config.title;
            subEl.textContent = config.subtitle;
            actionsEl.innerHTML = "";

            // Custom actions per chapter
            if (chapterId === StoryChapter.VEHICLE) {
                // Chapter 01 action: Inspect
                const btn = document.createElement("button");
                btn.type = "button";
                btn.className = "story-action-btn primary";
                btn.id = "storyInspectBtn";
                btn.innerHTML = `LOOK CLOSER &rarr;`;
                btn.addEventListener("click", () => {
                    this.enterInspection();
                });
                actionsEl.appendChild(btn);

                // Ensure editorial layer is visible
                this.editorialElement.style.display = "block";
                this.editorialElement.classList.remove("minimized");
            }
            else if (chapterId === StoryChapter.INSPECT) {
                // Chapter 02 action: Continue to configuration
                const btn = document.createElement("button");
                btn.type = "button";
                btn.className = "story-action-btn primary";
                btn.id = "startConfigBtn"; // Reuses standard ID for test compatibility
                btn.innerHTML = `CONTINUE &rarr;`;
                btn.addEventListener("click", () => {
                    this.enterConfiguration();
                });
                actionsEl.appendChild(btn);

                this.editorialElement.style.display = "block";
                this.editorialElement.classList.remove("minimized");
            }
            else if (chapterId === StoryChapter.CONFIGURE) {
                // In configuration, minimize background editorial layer to give stage to configurator
                this.editorialElement.classList.add("minimized");
            }
            else if (chapterId === StoryChapter.VALUATE) {
                // In valuation preview, minimize background editorial layer (configurator step 10 is active)
                this.editorialElement.classList.add("minimized");
            }
            else if (chapterId === StoryChapter.REAL_VALUE) {
                // In real value climax, minimize background editorial layer (valuation price reveal is active)
                this.editorialElement.classList.add("minimized");
            }
        };

        if (immediate) {
            updateContent();
            card.style.opacity = "1";
            card.style.transform = "translateY(0)";
        } else {
            // Smooth editorial entrance & exit
            card.style.opacity = "0";
            card.style.transform = "translateY(8px)";
            card.style.transition = "opacity 0.25s ease, transform 0.25s ease";

            setTimeout(() => {
                updateContent();
                requestAnimationFrame(() => {
                    card.style.opacity = "1";
                    card.style.transform = "translateY(0)";
                });
            }, 200);
        }
    }

    // ========================================================
    // USER ACTIONS & INTENT
    // ========================================================

    enterInspection() {
        console.log("SmartCar Story: User entered inspection mode (Chapter 02).");

        if (this.cameraController && typeof this.cameraController.transitionToInspection === "function") {
            this.cameraController.transitionToInspection(0, 0.75, 3.2);
        }

        if (this.animationController && typeof this.animationController.setState === "function") {
            this.animationController.setState("INSPECTING");
        }

        if (this.uiController && typeof this.uiController.setAppState === "function") {
            this.uiController.setAppState("INSPECTING");
        }

        this.setChapter(StoryChapter.INSPECT);
    }

    enterConfiguration() {
        console.log("SmartCar Story: User continued to configuration (Chapter 03).");

        if (this.uiController && typeof this.uiController.triggerConfigure === "function") {
            this.uiController.triggerConfigure();
        }

        this.setChapter(StoryChapter.CONFIGURE);
    }

    requestChapterNavigation(targetChapter) {
        if (targetChapter === this.currentChapter) return;

        switch (targetChapter) {
            case StoryChapter.VEHICLE:
                if (this.uiController && typeof this.uiController.closeConfigurator === "function") {
                    this.uiController.closeConfigurator();
                }
                if (this.animationController && typeof this.animationController.idle === "function") {
                    this.animationController.idle();
                }
                this.setChapter(StoryChapter.VEHICLE);
                break;

            case StoryChapter.INSPECT:
                if (this.uiController && typeof this.uiController.closeConfigurator === "function") {
                    this.uiController.closeConfigurator();
                }
                this.enterInspection();
                break;

            case StoryChapter.CONFIGURE:
                this.enterConfiguration();
                break;

            case StoryChapter.VALUATE:
                if (this.uiController) {
                    if (this.uiController.isConfigurationValid()) {
                        this.uiController.openConfigurator(10);
                        this.setChapter(StoryChapter.VALUATE);
                    } else {
                        this.enterConfiguration();
                    }
                }
                break;

            case StoryChapter.REAL_VALUE:
                if (this.uiController && this.uiController.isValuationReady) {
                    this.setChapter(StoryChapter.REAL_VALUE);
                } else if (this.uiController && this.uiController.isConfigurationValid()) {
                    this.uiController.openConfigurator(10);
                    this.setChapter(StoryChapter.VALUATE);
                } else {
                    this.enterConfiguration();
                }
                break;

            default:
                break;
        }
    }

    // ========================================================
    // SUBSCRIPTION & EVENT LISTENER HOOKS
    // ========================================================

    subscribe(callback) {
        if (typeof callback === "function") {
            this.listeners.push(callback);
        }
    }

    unsubscribe(callback) {
        this.listeners = this.listeners.filter(cb => cb !== callback);
    }

    notifyListeners(newChapter, oldChapter) {
        for (const cb of this.listeners) {
            try {
                cb(newChapter, oldChapter);
            } catch (err) {
                console.error("SmartCar Story: Listener error:", err);
            }
        }
    }

    update(delta) {
        // Optional frame updates (keeps single render loop clean)
    }
}
