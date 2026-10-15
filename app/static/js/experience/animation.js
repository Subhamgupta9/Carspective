// ============================================================
// SMARTCAR AI — CINEMATIC VEHICLE ANIMATOR
// animation.js — Phase 6 Automotive Dynamics & Choreography
// ============================================================

import * as THREE from "three";

// ============================================================
// VEHICLE STATE MACHINE (PHASE 6 CANONICAL)
// ============================================================

export const VehicleState = {
    ARRIVING: "ARRIVING",
    APPROACHING: "APPROACHING",
    BRAKING: "BRAKING",
    PARKING: "PARKING",
    IDLE: "IDLE",
    INSPECTING: "INSPECTING",
    TURNTABLE: "TURNTABLE",

    // Backward-compatible aliases
    DRIVE: "ARRIVING",
    APPROACH: "APPROACHING",
    BRAKE: "BRAKING",
    PARK: "PARKING",
    CONFIGURING: "CONFIGURING",
    VALUATION_READY: "VALUATION_READY",
    VALUATING: "VALUATING",
    VALUATION_RESULT: "VALUATION_RESULT",
    VALUATION_ERROR: "VALUATION_ERROR"
};

// Maximum delta-time clamp: prevents teleportation on browser stalls
const MAX_DELTA = 1.0 / 15.0; // ~66ms, covers down to 15fps

// ============================================================
// VEHICLE ANIMATOR CLASS
// ============================================================

export class VehicleAnimator {

    constructor(vehicle, cameraController = null, uiController = null) {
        this.vehicle = vehicle;
        this.cameraController = cameraController;
        this.uiController = uiController;

        this.state = VehicleState.IDLE;
        this.previousState = VehicleState.IDLE;
        this.stateTime = 0;

        // Continuous elapsed time — never resets, used for micro-vibrations
        // so suspension vibration does not glitch across state transitions
        this.elapsedTime = 0;

        // Pacing & Dynamics calibrated for an 8–12 second arrival sequence
        // Total distance: 31.2m (-28.0m to 3.2m). Total arrival time: ~10.2 seconds.
        this.speed = 0;
        this.targetSpeed = 0;
        this.maxDriveSpeed = 5.6;    // Cruising speed during arrival
        this.approachSpeed = 3.6;    // Controlled approach speed
        this.acceleration = 2.2;     // Smooth acceleration
        this.deceleration = 1.8;     // Natural coastdown deceleration
        this.brakingPower = 6.8;     // Physical braking curve

        // Waypoints along Z (car drives forward towards camera along +Z)
        this.startZ = -28.0;
        this.approachZ = -9.0;
        this.brakeZ = 0.5;
        this.parkZ = 3.2;

        this.cameraEnabled = true;
        this.isPlaying = false;
        this.sequenceInitialized = false;

        // Story Controller integration
        this.storyController = null;

        // Callbacks for external listeners
        this.onInspectionReady = null;

        // Dynamics physics state (smoothed and damped)
        this._suspensionY = 0;
        this._pitch = 0;             // Pitch rotation (brake dive & rebound)
        this._steerAngle = 0;        // Steering angle for front wheels

        // Reusable vectors for zero GC overhead
        this._camPos = new THREE.Vector3();
        this._camTarget = new THREE.Vector3();
    }

    setStoryController(storyController) {
        this.storyController = storyController;
    }

    setUIController(uiController) {
        this.uiController = uiController;
    }

    setCameraController(cameraController) {
        this.cameraController = cameraController;
    }

    getVehicleObject() {
        if (!this.vehicle || typeof this.vehicle.getObject !== "function") {
            return null;
        }
        if (typeof this.vehicle.isReady === "function" && !this.vehicle.isReady()) {
            return null;
        }
        return this.vehicle.getObject();
    }

    getBaseYaw() {
        if (this.vehicle && typeof this.vehicle.getBaseYaw === "function") {
            return this.vehicle.getBaseYaw();
        }
        return -Math.PI / 2;
    }

    /**
     * Returns world-space Y position for vehicle chassis,
     * combining geometric tire ground contact with suspension offset.
     */
    getGroundY(suspension = 0) {
        let offset = 0;
        if (this.vehicle && typeof this.vehicle.getGroundOffset === "function") {
            offset = this.vehicle.getGroundOffset();
        }
        return offset + suspension;
    }

    // ========================================================
    // MAIN UPDATE LOOP
    // ========================================================

    update(delta) {
        if (!this.vehicle || typeof this.vehicle.isReady !== "function" || !this.vehicle.isReady()) {
            return;
        }

        const vehicleObject = this.getVehicleObject();
        if (!vehicleObject) {
            return;
        }

        const dt = Math.min(delta, MAX_DELTA);

        // Auto-initialize sequence once vehicle finishes loading
        if (!this.sequenceInitialized) {
            this.sequenceInitialized = true;
            this.playSequence("arrival");
        }

        this.stateTime += dt;
        this.elapsedTime += dt;

        switch (this.state) {
            case VehicleState.ARRIVING:
            case "DRIVE":
                this.updateArriving(dt);
                break;

            case VehicleState.APPROACHING:
            case "APPROACH":
                this.updateApproaching(dt);
                break;

            case VehicleState.BRAKING:
            case "BRAKE":
                this.updateBraking(dt);
                break;

            case VehicleState.PARKING:
            case "PARK":
                this.updateParking(dt);
                break;

            case VehicleState.TURNTABLE:
                this.updateTurntable(dt);
                break;

            case VehicleState.INSPECTING:
                this.updateInspecting(dt);
                break;

            case VehicleState.IDLE:
            case VehicleState.CONFIGURING:
            case VehicleState.VALUATION_READY:
            case VehicleState.VALUATING:
            case VehicleState.VALUATION_RESULT:
            case VehicleState.VALUATION_ERROR:
            default:
                this.updateIdle(dt);
                break;
        }

        if (this.isPlaying && this.cameraEnabled) {
            this.updateCamera(dt);
        }
    }

    // ========================================================
    // STATE: ARRIVING (0s - ~4.6s: Entry from distance, steering)
    // ========================================================

    updateArriving(dt) {
        const vehicleObject = this.getVehicleObject();
        if (!vehicleObject) return;

        if (this.vehicle) {
            if (typeof this.vehicle.setHeadlights === "function") this.vehicle.setHeadlights(true);
            if (typeof this.vehicle.setBrakeLights === "function") this.vehicle.setBrakeLights(false);
        }

        // Accelerate smoothly to cruising speed
        this.targetSpeed = this.maxDriveSpeed;
        this.speed = THREE.MathUtils.damp(this.speed, this.targetSpeed, this.acceleration, dt);

        const movement = this.speed * dt;
        vehicleObject.position.z += movement;
        this.rotateWheels(movement);

        // Steering: gentle lane-centering curve upon entering shot
        const steerOscillation = Math.sin(this.stateTime * 1.25) * Math.exp(-this.stateTime * 0.45) * 0.045;
        this._steerAngle = THREE.MathUtils.damp(this._steerAngle, steerOscillation, 8.0, dt);
        if (this.vehicle && typeof this.vehicle.setSteeringAngle === "function") {
            this.vehicle.setSteeringAngle(this._steerAngle);
        }

        // Subtle vehicle yaw alignment with steering
        vehicleObject.position.x = 0;
        vehicleObject.rotation.y = THREE.MathUtils.damp(
            vehicleObject.rotation.y,
            this.getBaseYaw() + this._steerAngle * 0.12,
            6.0,
            dt
        );
        vehicleObject.rotation.z = THREE.MathUtils.damp(vehicleObject.rotation.z, 0, 8.0, dt);

        // Cruise pitch remains level
        this._pitch = THREE.MathUtils.damp(this._pitch, 0, 6.0, dt);
        vehicleObject.rotation.x = this._pitch;

        // Subtle high-frequency road suspension micro-vibration
        const roadTextureVibe = Math.sin(this.elapsedTime * 14.0) * 0.0022;
        this._suspensionY = THREE.MathUtils.damp(this._suspensionY, roadTextureVibe, 10.0, dt);
        vehicleObject.position.y = this.getGroundY(this._suspensionY);

        if (vehicleObject.position.z >= this.approachZ) {
            this.setState(VehicleState.APPROACHING);
        }
    }

    // ========================================================
    // STATE: APPROACHING (~4.6s - ~7.0s: Controlled coastdown)
    // ========================================================

    updateApproaching(dt) {
        const vehicleObject = this.getVehicleObject();
        if (!vehicleObject) return;

        if (this.vehicle) {
            if (typeof this.vehicle.setHeadlights === "function") this.vehicle.setHeadlights(true);
            if (typeof this.vehicle.setBrakeLights === "function") this.vehicle.setBrakeLights(false);
        }

        // Coastdown deceleration toward brake entry speed
        const distToBrake = Math.max(0, this.brakeZ - vehicleObject.position.z);
        const approachSpan = this.brakeZ - this.approachZ;
        const progress = THREE.MathUtils.clamp(1.0 - (distToBrake / approachSpan), 0, 1);
        this.targetSpeed = THREE.MathUtils.lerp(this.maxDriveSpeed, this.approachSpeed, progress);
        this.speed = THREE.MathUtils.damp(this.speed, this.targetSpeed, this.deceleration, dt);

        const movement = this.speed * dt;
        vehicleObject.position.z += movement;
        this.rotateWheels(movement);

        // Front wheels straighten completely
        this._steerAngle = THREE.MathUtils.damp(this._steerAngle, 0, 7.0, dt);
        if (this.vehicle && typeof this.vehicle.setSteeringAngle === "function") {
            this.vehicle.setSteeringAngle(this._steerAngle);
        }

        vehicleObject.position.x = 0;
        vehicleObject.rotation.y = THREE.MathUtils.damp(vehicleObject.rotation.y, this.getBaseYaw(), 8.0, dt);
        vehicleObject.rotation.z = THREE.MathUtils.damp(vehicleObject.rotation.z, 0, 8.0, dt);

        this._pitch = THREE.MathUtils.damp(this._pitch, 0, 6.0, dt);
        vehicleObject.rotation.x = this._pitch;

        const roadTextureVibe = Math.sin(this.elapsedTime * 11.0) * 0.0018;
        this._suspensionY = THREE.MathUtils.damp(this._suspensionY, roadTextureVibe, 10.0, dt);
        vehicleObject.position.y = this.getGroundY(this._suspensionY);

        if (vehicleObject.position.z >= this.brakeZ) {
            this.setState(VehicleState.BRAKING);
        }
    }

    // ========================================================
    // STATE: BRAKING (~7.0s - ~8.8s: Deceleration, dive, brake lights)
    // ========================================================

    updateBraking(dt) {
        const vehicleObject = this.getVehicleObject();
        if (!vehicleObject) return;

        if (this.vehicle) {
            if (typeof this.vehicle.setHeadlights === "function") this.vehicle.setHeadlights(true);
            if (typeof this.vehicle.setBrakeLights === "function") this.vehicle.setBrakeLights(true);
        }

        const totalBrakeDist = this.parkZ - this.brakeZ;
        const remaining = Math.max(0, this.parkZ - vehicleObject.position.z);
        const progress = THREE.MathUtils.clamp(1.0 - (remaining / totalBrakeDist), 0, 1);

        // Smooth square-root physical braking curve
        const idealSpeed = this.approachSpeed * Math.sqrt(Math.max(0, 1.0 - progress));
        this.targetSpeed = idealSpeed;
        this.speed = THREE.MathUtils.damp(this.speed, idealSpeed, this.brakingPower, dt);

        const movement = this.speed * dt;
        if (movement > 0.00005) {
            vehicleObject.position.z = Math.min(vehicleObject.position.z + movement, this.parkZ);
            this.rotateWheels(movement);
        }

        vehicleObject.position.x = 0;
        vehicleObject.rotation.y = THREE.MathUtils.damp(vehicleObject.rotation.y, this.getBaseYaw(), 8.0, dt);
        vehicleObject.rotation.z = THREE.MathUtils.damp(vehicleObject.rotation.z, 0, 8.0, dt);

        // Front-end pitch compression (brake dive)
        const targetDive = (this.speed / this.maxDriveSpeed) * 0.016;
        this._pitch = THREE.MathUtils.damp(this._pitch, targetDive, 5.5, dt);
        vehicleObject.rotation.x = this._pitch;

        // Suspension settles during braking
        this._suspensionY = THREE.MathUtils.damp(this._suspensionY, 0, 7.0, dt);
        vehicleObject.position.y = this.getGroundY(this._suspensionY);

        if (remaining <= 0.03 || (this.speed <= 0.10 && remaining <= 0.12) || vehicleObject.position.z >= (this.parkZ - 0.015)) {
            this.setState(VehicleState.PARKING);
        }
    }

    // ========================================================
    // STATE: PARKING (~8.8s - ~10.2s: Rebound bounce, camera handoff)
    // ========================================================

    updateParking(dt) {
        const vehicleObject = this.getVehicleObject();
        if (!vehicleObject) return;

        this.speed = 0;

        // Settle smoothly to precise parkZ
        vehicleObject.position.z = THREE.MathUtils.damp(vehicleObject.position.z, this.parkZ, 8.0, dt);
        vehicleObject.position.x = 0;

        // Harmonic rebound bounce settling
        const pitchBounce = -0.007 * Math.exp(-this.stateTime * 3.5) * Math.cos(this.stateTime * 6.5);
        this._pitch = THREE.MathUtils.damp(this._pitch, pitchBounce, 8.0, dt);
        vehicleObject.rotation.x = this._pitch;

        const suspensionBounce = 0.0025 * Math.exp(-this.stateTime * 3.5) * Math.sin(this.stateTime * 6.5);
        this._suspensionY = THREE.MathUtils.damp(this._suspensionY, suspensionBounce, 8.0, dt);
        vehicleObject.position.y = this.getGroundY(this._suspensionY);

        vehicleObject.rotation.y = THREE.MathUtils.damp(vehicleObject.rotation.y, this.getBaseYaw(), 6.0, dt);
        vehicleObject.rotation.z = THREE.MathUtils.damp(vehicleObject.rotation.z, 0, 6.0, dt);

        // Keep brake lights illuminated during weight transfer (0.6s), then release
        if (this.vehicle && typeof this.vehicle.setBrakeLights === "function") {
            this.vehicle.setBrakeLights(this.stateTime < 0.6);
        }

        // Camera handoff to Hero three-quarter composition
        if (this.stateTime >= 1.4) {
            if (this.cameraController) {
                if (typeof this.cameraController.setPreset === "function") {
                    this.cameraController.setPreset("HERO_34");
                } else if (typeof this.cameraController.transitionToParkedHero === "function") {
                    this.cameraController.transitionToParkedHero(0, 0.75, this.parkZ);
                }
            }

            if (typeof this.onInspectionReady === "function") {
                this.onInspectionReady();
            }

            this.isPlaying = false;
            this.setState(VehicleState.IDLE);
        }
    }

    // ========================================================
    // STATE: IDLE (Stationary showcase breathing)
    // ========================================================

    updateIdle(dt) {
        const vehicleObject = this.getVehicleObject();
        if (!vehicleObject) return;

        this.speed = 0;

        if (this.vehicle) {
            if (typeof this.vehicle.setHeadlights === "function") this.vehicle.setHeadlights(true);
            if (typeof this.vehicle.setBrakeLights === "function") this.vehicle.setBrakeLights(false);
            if (typeof this.vehicle.setSteeringAngle === "function") this.vehicle.setSteeringAngle(0);
        }

        // Imperceptible idle showroom micro-breathing (0.0008m)
        const breathing = Math.sin(this.elapsedTime * 1.8) * 0.0008;
        this._suspensionY = THREE.MathUtils.damp(this._suspensionY, breathing, 4.0, dt);
        vehicleObject.position.y = this.getGroundY(this._suspensionY);

        vehicleObject.position.x = 0;
        vehicleObject.position.z = this.parkZ;

        vehicleObject.rotation.y = THREE.MathUtils.damp(vehicleObject.rotation.y, this.getBaseYaw(), 4.0, dt);
        this._pitch = THREE.MathUtils.damp(this._pitch, 0, 4.0, dt);
        vehicleObject.rotation.x = this._pitch;
        vehicleObject.rotation.z = THREE.MathUtils.damp(vehicleObject.rotation.z, 0, 4.0, dt);
    }

    // ========================================================
    // STATE: INSPECTING (Interactive orbit inspection)
    // ========================================================

    updateInspecting(dt) {
        this.updateIdle(dt);
    }

    // ========================================================
    // STATE: TURNTABLE (Continuous seamless 360° rotation)
    // ========================================================

    updateTurntable(dt) {
        this.updateIdle(dt);
        if (this.cameraController && typeof this.cameraController.enableAutoRotate === "function") {
            this.cameraController.enableAutoRotate(true);
        }
    }

    rotateWheels(distance) {
        if (this.vehicle && typeof this.vehicle.rotateWheels === "function") {
            this.vehicle.rotateWheels(distance);
        }
    }

    // ========================================================
    // CINEMATIC CAMERA CHOREOGRAPHY
    // ========================================================

    updateCamera(dt) {
        const vehicleObject = this.getVehicleObject();
        if (!this.cameraController || !vehicleObject) return;

        const carZ = vehicleObject.position.z;
        const totalDistance = this.parkZ - this.startZ;
        const traveled = carZ - this.startZ;
        const progress = THREE.MathUtils.clamp(traveled / totalDistance, 0, 1);

        // Smoothly interpolate tracking perspective with progress
        const camX = THREE.MathUtils.lerp(7.2, 6.2, progress);
        const camY = THREE.MathUtils.lerp(3.2, 2.5, progress);
        const camZ = THREE.MathUtils.lerp(10.5, 8.8, progress);

        this.cameraController.cinematicPosition(camX, camY, camZ, 0, 0.75, carZ);
    }

    // ========================================================
    // STATE MACHINE TRANSITIONS
    // ========================================================

    setState(newState) {
        if (this.state === newState) return;

        this.previousState = this.state;
        this.state = newState;
        this.stateTime = 0;

        console.log(`VehicleAnimator: State → ${newState}`);

        // Update UI status
        if (this.uiController && typeof this.uiController.setStatus === "function") {
            switch (newState) {
                case VehicleState.ARRIVING:
                    this.uiController.setStatus("VEHICLE ARRIVING");
                    break;
                case VehicleState.APPROACHING:
                    this.uiController.setStatus("APPROACHING");
                    break;
                case VehicleState.BRAKING:
                    this.uiController.setStatus("BRAKING");
                    break;
                case VehicleState.PARKING:
                    this.uiController.setStatus("PARKING");
                    break;
                case VehicleState.IDLE:
                    this.uiController.setStatus("INSPECTION READY");
                    break;
                case VehicleState.INSPECTING:
                    this.uiController.setStatus("INSPECTION MODE");
                    if (typeof this.uiController.setAppState === "function") {
                        this.uiController.setAppState("INSPECTING");
                    }
                    break;
                case VehicleState.TURNTABLE:
                    this.uiController.setStatus("360° SHOWROOM TURNTABLE");
                    break;
                case VehicleState.CONFIGURING:
                    this.uiController.setStatus("CONFIGURING");
                    if (typeof this.uiController.setAppState === "function") {
                        this.uiController.setAppState("CONFIGURING");
                    }
                    break;
                case VehicleState.VALUATION_READY:
                    this.uiController.setStatus("VALUATION READY");
                    if (typeof this.uiController.setAppState === "function") {
                        this.uiController.setAppState("VALUATION_READY");
                    }
                    break;
                case VehicleState.VALUATING:
                    this.uiController.setStatus("CALCULATING MARKET VALUE");
                    if (typeof this.uiController.setAppState === "function") {
                        this.uiController.setAppState("VALUATING");
                    }
                    break;
                case VehicleState.VALUATION_RESULT:
                    this.uiController.setStatus("VALUATION COMPLETE");
                    if (typeof this.uiController.setAppState === "function") {
                        this.uiController.setAppState("VALUATION_RESULT");
                    }
                    break;
                default:
                    break;
            }
        }

        // Synchronize story controller
        if (this.storyController && typeof this.storyController.syncWithExperienceState === "function") {
            this.storyController.syncWithExperienceState(newState);
        }

        // Synchronize dynamic scene lighting
        if (typeof window !== "undefined" && window.smartCarExperience) {
            const sceneInstance = window.smartCarExperience.getSceneInstance();
            if (sceneInstance && typeof sceneInstance.setLightingProfile === "function") {
                if (newState === VehicleState.ARRIVING || newState === VehicleState.APPROACHING || newState === VehicleState.BRAKING) {
                    sceneInstance.setLightingProfile("ARRIVAL");
                } else if (newState === VehicleState.PARKING || newState === VehicleState.IDLE || newState === VehicleState.INSPECTING || newState === VehicleState.TURNTABLE) {
                    sceneInstance.setLightingProfile("INSPECTION");
                } else if (newState === VehicleState.VALUATION_READY || newState === VehicleState.VALUATING) {
                    sceneInstance.setLightingProfile("VALUATION");
                } else if (newState === VehicleState.VALUATION_RESULT) {
                    sceneInstance.setLightingProfile("RESULT");
                }
            }
        }
    }

    // ========================================================
    // SEQUENCES & PUBLIC API (PHASE 6)
    // ========================================================

    prepareForSequence() {
        const vehicleObject = this.getVehicleObject();
        if (!vehicleObject) return;

        this._suspensionY = 0;
        this._pitch = 0;
        this._steerAngle = 0;
        this.elapsedTime = 0;

        vehicleObject.position.set(0, this.getGroundY(0), this.startZ);
        vehicleObject.rotation.set(0, this.getBaseYaw(), 0);

        this.speed = 0;
        this.targetSpeed = 0;

        if (this.vehicle) {
            if (typeof this.vehicle.setHeadlights === "function") this.vehicle.setHeadlights(true);
            if (typeof this.vehicle.setBrakeLights === "function") this.vehicle.setBrakeLights(false);
            if (typeof this.vehicle.resetWheels === "function") this.vehicle.resetWheels();
            if (typeof this.vehicle.setSteeringAngle === "function") this.vehicle.setSteeringAngle(0);
        }

        if (this.cameraController && typeof this.cameraController.cinematicPosition === "function") {
            this.cameraController.cinematicPosition(7.2, 3.2, 10.5, 0, 0.75, this.startZ);
        }

        if (typeof window !== "undefined" && window.smartCarExperience) {
            const sceneInstance = window.smartCarExperience.getSceneInstance();
            if (sceneInstance && typeof sceneInstance.setLightingProfile === "function") {
                sceneInstance.setLightingProfile("ARRIVAL");
            }
        }
    }

    playSequence(sequenceName = "arrival") {
        const seq = (sequenceName || "arrival").toLowerCase().trim();
        console.log(`VehicleAnimator: playSequence('${seq}')`);

        if (seq === "arrival" || seq === "arriving") {
            this.prepareForSequence();
            this.isPlaying = true;
            this.sequenceInitialized = true;
            this.setState(VehicleState.ARRIVING);
            return true;
        }

        if (seq === "turntable") {
            this.isPlaying = false;
            this.speed = 0;
            this.targetSpeed = 0;
            this._suspensionY = 0;
            this._pitch = 0;

            const vehicleObject = this.getVehicleObject();
            if (vehicleObject) {
                vehicleObject.position.set(0, this.getGroundY(0), this.parkZ);
                vehicleObject.rotation.set(0, this.getBaseYaw(), 0);
            }

            if (this.vehicle) {
                if (typeof this.vehicle.setHeadlights === "function") this.vehicle.setHeadlights(true);
                if (typeof this.vehicle.setBrakeLights === "function") this.vehicle.setBrakeLights(false);
                if (typeof this.vehicle.resetWheels === "function") this.vehicle.resetWheels();
            }

            if (this.cameraController) {
                if (typeof this.cameraController.setPreset === "function") {
                    this.cameraController.setPreset("TURN_TABLE");
                } else if (typeof this.cameraController.enableAutoRotate === "function") {
                    this.cameraController.enableAutoRotate(true);
                }
            }

            this.setState(VehicleState.TURNTABLE);
            return true;
        }

        if (seq === "inspecting" || seq === "inspection") {
            this.enterInspection();
            return true;
        }

        if (seq === "braking" || seq === "brake") {
            this.setState(VehicleState.BRAKING);
            return true;
        }

        if (seq === "parking" || seq === "park") {
            this.setState(VehicleState.PARKING);
            return true;
        }

        console.warn(`VehicleAnimator: Unknown sequence '${sequenceName}'.`);
        return false;
    }

    /**
     * Interrupt active animation immediately and enter inspection mode.
     */
    interrupt() {
        if (this.state === VehicleState.INSPECTING || this.state === VehicleState.IDLE) {
            return;
        }
        console.log("VehicleAnimator: Animation interrupted by user -> entering inspection mode.");
        this.enterInspection();
    }

    enterInspection() {
        this.isPlaying = false;
        this.speed = 0;
        this.targetSpeed = 0;
        this._suspensionY = 0;
        this._pitch = 0;
        this._steerAngle = 0;

        const vehicleObject = this.getVehicleObject();
        if (vehicleObject) {
            vehicleObject.position.set(0, this.getGroundY(0), this.parkZ);
            vehicleObject.rotation.set(0, this.getBaseYaw(), 0);
        }

        if (this.vehicle) {
            if (typeof this.vehicle.setHeadlights === "function") this.vehicle.setHeadlights(true);
            if (typeof this.vehicle.setBrakeLights === "function") this.vehicle.setBrakeLights(false);
            if (typeof this.vehicle.resetWheels === "function") this.vehicle.resetWheels();
            if (typeof this.vehicle.setSteeringAngle === "function") this.vehicle.setSteeringAngle(0);
        }

        if (this.cameraController) {
            if (typeof this.cameraController.setPreset === "function") {
                this.cameraController.setPreset("HERO_34");
            } else if (typeof this.cameraController.transitionToInspection === "function") {
                this.cameraController.transitionToInspection(0, 0.75, this.parkZ);
            }
        }

        this.setState(VehicleState.INSPECTING);
    }

    playCinematicSequence() {
        return this.playSequence("arrival");
    }

    drive() {
        return this.playSequence("arrival");
    }

    park() {
        return this.playSequence("parking");
    }

    idle() {
        this.isPlaying = false;
        this.speed = 0;
        this.targetSpeed = 0;

        if (this.vehicle && typeof this.vehicle.setBrakeLights === "function") {
            this.vehicle.setBrakeLights(false);
        }

        if (this.cameraController && typeof this.cameraController.transitionToInspection === "function") {
            this.cameraController.transitionToInspection(0, 0.75, this.parkZ);
        }

        this.setState(VehicleState.IDLE);
    }

    stop() {
        this.enterInspection();
    }

    setCameraEnabled(enabled) {
        this.cameraEnabled = enabled;
    }

    getState() {
        return this.state;
    }

    getSpeed() {
        return this.speed;
    }
}

// Backward-compatible alias
export const SmartCarAnimation = VehicleAnimator;
