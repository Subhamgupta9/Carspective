// ============================================================
// SMARTCAR AI — VEHICLE INTERACTION SYSTEM
// interaction.js
// ============================================================

export class SmartCarInteraction {

    constructor(canvas, cameraController) {
        if (!canvas) {
            throw new Error("SmartCarInteraction: Canvas is required.");
        }

        if (!cameraController) {
            throw new Error("SmartCarInteraction: Camera controller is required.");
        }

        this.canvas = canvas;
        this.cameraController = cameraController;

        // Interaction state
        this.isActive = true;
        this.isDragging = false;
        this.lastX = 0;
        this.lastY = 0;
        this.pointerId = null;

        // Multi-touch tracking
        this.activePointers = new Map();
        this.previousPinchDistance = null;

        // Sensitivities calibrated for smooth automotive inspection
        this.rotationSensitivity = 0.0055;
        this.elevationSensitivity = 0.0035;
        this.wheelSensitivity = 0.0016; // Small, controlled zoom increments

        // Activity callbacks for cinematic HUD fading
        this.onInteractionStart = null;
        this.onInteractionEnd = null;
        this.inactivityTimer = null;

        // Bind event handlers
        this.onPointerDown = this.onPointerDown.bind(this);
        this.onPointerMove = this.onPointerMove.bind(this);
        this.onPointerUp = this.onPointerUp.bind(this);
        this.onWheel = this.onWheel.bind(this);

        // Attach listeners
        this.canvas.addEventListener("pointerdown", this.onPointerDown);
        this.canvas.addEventListener("pointermove", this.onPointerMove);
        this.canvas.addEventListener("pointerup", this.onPointerUp);
        this.canvas.addEventListener("pointercancel", this.onPointerUp);
        this.canvas.addEventListener("pointerleave", this.onPointerUp);

        // Wheel event must be non-passive to allow preventDefault()
        // and eliminate unwanted document scrolling while inspecting
        this.canvas.addEventListener("wheel", this.onWheel, { passive: false });

        // Ensure canvas does not trigger default browser touch gestures
        this.canvas.style.touchAction = "none";
    }

    // ========================================================
    // INTERACTION NOTIFICATION (HUD FADING)
    // ========================================================

    notifyInteraction(isStarting) {
        if (isStarting && typeof this.onInteractionStart === "function") {
            this.onInteractionStart();
        }

        clearTimeout(this.inactivityTimer);
        this.inactivityTimer = setTimeout(() => {
            if (typeof this.onInteractionEnd === "function") {
                this.onInteractionEnd();
            }
        }, 1800);
    }

    // ========================================================
    // POINTER DOWN
    // ========================================================

    onPointerDown(event) {
        if (!this.isActive) {
            return;
        }

        this.activePointers.set(event.pointerId, {
            x: event.clientX,
            y: event.clientY
        });

        this.notifyInteraction(true);

        // Two-finger touch (pinch zoom initiation)
        if (this.activePointers.size === 2) {
            this.isDragging = false;
            this.previousPinchDistance = this.getPinchDistance();
            return;
        }

        // Single-finger touch or mouse drag
        if (this.activePointers.size === 1) {
            this.isDragging = true;
            this.pointerId = event.pointerId;
            this.lastX = event.clientX;
            this.lastY = event.clientY;

            if (typeof this.canvas.setPointerCapture === "function") {
                try {
                    this.canvas.setPointerCapture(event.pointerId);
                } catch (e) {
                    // Ignore pointer capture errors on older browsers
                }
            }

            // Natural progression from Chapter 01 (IDLE) into Chapter 02 (INSPECT)
            if (window.smartCarExperience && typeof window.smartCarExperience.getState === "function") {
                if (window.smartCarExperience.getState() === "IDLE" && typeof window.smartCarExperience.startInspection === "function") {
                    window.smartCarExperience.startInspection();
                }
            }
        }
    }

    // ========================================================
    // POINTER MOVE
    // ========================================================

    onPointerMove(event) {
        if (!this.isActive) {
            return;
        }

        if (this.activePointers.has(event.pointerId)) {
            this.activePointers.set(event.pointerId, {
                x: event.clientX,
                y: event.clientY
            });
        }

        // Multi-touch pinch zoom
        if (this.activePointers.size === 2) {
            const currentDistance = this.getPinchDistance();
            if (this.previousPinchDistance !== null && currentDistance > 0) {
                const diff = this.previousPinchDistance - currentDistance;
                this.cameraController.zoom(diff * this.wheelSensitivity * 2.2);
                this.notifyInteraction(true);
            }
            this.previousPinchDistance = currentDistance;
            return;
        }

        // Single pointer drag (orbit rotation & elevation)
        if (!this.isDragging || event.pointerId !== this.pointerId) {
            // Forward subtle cursor parallax to camera controller
            if (this.cameraController && typeof this.cameraController.setPointerParallax === "function") {
                const normX = (event.clientX / window.innerWidth) * 2 - 1;
                const normY = -(event.clientY / window.innerHeight) * 2 + 1;
                this.cameraController.setPointerParallax(normX, normY);
            }
            return;
        }

        const deltaX = event.clientX - this.lastX;
        const deltaY = event.clientY - this.lastY;

        this.lastX = event.clientX;
        this.lastY = event.clientY;

        // Horizontal delta rotates azimuth theta
        const deltaTheta = -deltaX * this.rotationSensitivity;

        // Vertical delta adjusts polar elevation phi
        const deltaPhi = -deltaY * this.elevationSensitivity;

        this.cameraController.orbit(deltaTheta, deltaPhi);
        this.notifyInteraction(true);
    }

    // ========================================================
    // POINTER UP
    // ========================================================

    onPointerUp(event) {
        this.activePointers.delete(event.pointerId);

        if (typeof this.canvas.releasePointerCapture === "function") {
            try {
                this.canvas.releasePointerCapture(event.pointerId);
            } catch (e) {
                // Ignore if not captured
            }
        }

        if (this.activePointers.size < 2) {
            this.previousPinchDistance = null;
        }

        if (event.pointerId === this.pointerId) {
            this.isDragging = false;
            this.pointerId = null;
            this.cameraController.releaseControl();
            this.notifyInteraction(false);
        }
    }

    // ========================================================
    // MOUSE WHEEL (ZOOM)
    // ========================================================

    onWheel(event) {
        if (!this.isActive) {
            return;
        }

        // Disable document page scrolling when interacting with 3D canvas
        event.preventDefault();

        // Normalize delta across browsers
        const normalizedDelta = Math.sign(event.deltaY) * Math.min(Math.abs(event.deltaY), 100);
        this.cameraController.zoom(normalizedDelta * this.wheelSensitivity);
        this.notifyInteraction(true);

        // Briefly release control after wheel interaction so auto-rotate can resume smoothly
        clearTimeout(this.wheelTimeout);
        this.wheelTimeout = setTimeout(() => {
            this.cameraController.releaseControl();
        }, 800);
    }

    // ========================================================
    // PINCH DISTANCE HELPER
    // ========================================================

    getPinchDistance() {
        const pointers = Array.from(this.activePointers.values());
        if (pointers.length < 2) {
            return 0;
        }

        const dx = pointers[0].x - pointers[1].x;
        const dy = pointers[0].y - pointers[1].y;
        return Math.sqrt(dx * dx + dy * dy);
    }

    // ========================================================
    // ACTIVATION API
    // ========================================================

    activate() {
        this.isActive = true;
        this.canvas.style.cursor = "grab";
    }

    deactivate() {
        this.isActive = false;
        this.isDragging = false;
        this.activePointers.clear();
        this.canvas.style.cursor = "default";
    }

    setEnabled(enabled) {
        if (enabled) {
            this.activate();
        } else {
            this.deactivate();
        }
    }

    // ========================================================
    // DISPOSAL
    // ========================================================

    destroy() {
        this.canvas.removeEventListener("pointerdown", this.onPointerDown);
        this.canvas.removeEventListener("pointermove", this.onPointerMove);
        this.canvas.removeEventListener("pointerup", this.onPointerUp);
        this.canvas.removeEventListener("pointercancel", this.onPointerUp);
        this.canvas.removeEventListener("pointerleave", this.onPointerUp);
        this.canvas.removeEventListener("wheel", this.onWheel);

        clearTimeout(this.wheelTimeout);
        clearTimeout(this.inactivityTimer);
        this.activePointers.clear();
    }
}