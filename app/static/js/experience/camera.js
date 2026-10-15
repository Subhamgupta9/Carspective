// ============================================================
// SMARTCAR AI — CINEMATIC & INSPECTION CAMERA SYSTEM
// camera.js — Phase 12 Advanced Automotive Visualization
// ============================================================

import * as THREE from "three";

// Easing functions
const EASING = {
    easeInOutCubic: (t) => t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2,
    easeOutCubic: (t) => 1 - Math.pow(1 - t, 3),
    easeInOutQuad: (t) => t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2,
    easeOutQuad: (t) => 1 - (1 - t) * (1 - t),
    linear: (t) => t
};

// ============================================================
// CAMERA PRESETS (PHASE 5 AUTOMOTIVE COMPOSITION)
// ============================================================

export const CAMERA_PRESETS = {
    HERO_34: {
        name: "HERO_34",
        label: "Hero 3/4 Stance",
        spherical: {
            radiusMultiplier: 1.0,
            theta: 0.75, // ~43 deg front three-quarter
            phi: 1.30    // ~74 deg eye level
        },
        duration: 1.6,
        easing: "easeInOutCubic"
    },
    SIDE: {
        name: "SIDE",
        label: "Aerodynamic Side Profile",
        spherical: {
            radiusMultiplier: 1.05,
            theta: Math.PI / 2, // 90 deg lateral profile
            phi: 1.36           // ~78 deg low athletic stance
        },
        duration: 1.5,
        easing: "easeInOutCubic"
    },
    FRONT: {
        name: "FRONT",
        label: "Front Grille & Lighting",
        spherical: {
            radiusMultiplier: 0.88,
            theta: 0.05, // Direct front
            phi: 1.36    // ~78 deg eye level grille stance
        },
        duration: 1.4,
        easing: "easeInOutCubic"
    },
    REAR: {
        name: "REAR",
        label: "Rear Stance & Diffuser",
        spherical: {
            radiusMultiplier: 0.92,
            theta: Math.PI - 0.05, // Direct rear
            phi: 1.34              // ~76 deg rear diffuser & lights
        },
        duration: 1.5,
        easing: "easeInOutCubic"
    },
    TOP_DRONE: {
        name: "TOP_DRONE",
        label: "Top Orbital Drone",
        spherical: {
            radiusMultiplier: 1.25,
            theta: 0.65,
            phi: 0.52   // ~30 deg high angle bird's-eye view looking down
        },
        duration: 1.6,
        easing: "easeInOutCubic"
    },
    TURN_TABLE: {
        name: "TURN_TABLE",
        label: "Showroom 360 Turntable",
        spherical: {
            radiusMultiplier: 1.0,
            theta: null, // Maintain current azimuth
            phi: 1.30
        },
        duration: 1.2,
        easing: "easeInOutCubic",
        autoRotate: true
    }
};

export class SmartCarCamera {

    constructor(camera) {
        if (!camera) {
            throw new Error("SmartCarCamera: Camera is required.");
        }

        this.camera = camera;

        // Target position the camera is tracking / orbiting around
        this.target = new THREE.Vector3(0, 0.75, 0);
        this.lookTarget = new THREE.Vector3(0, 0.75, 0);

        // Desired Cartesian position (used during cinematic tracking shots)
        this.position = new THREE.Vector3(6.8, 3.0, 9.5);

        // Spherical coordinates
        // theta: horizontal azimuth angle (rotation around vehicle in XZ plane)
        // phi: polar elevation angle from vertical +Y
        // radius: distance from target
        this.theta = Math.atan2(this.position.x - this.target.x, this.position.z - this.target.z);
        const dist = this.position.distanceTo(this.target);
        this.radius = dist;
        this.phi = Math.acos(THREE.MathUtils.clamp((this.position.y - this.target.y) / Math.max(dist, 0.001), -1, 1));

        this.targetTheta = this.theta;
        this.targetPhi = this.phi;
        this.targetRadius = this.radius;

        // Check for reduced motion preference
        this.prefersReducedMotion = typeof window !== "undefined" &&
            window.matchMedia &&
            window.matchMedia("(prefers-reduced-motion: reduce)").matches;

        // Active Preset & Framing
        this.currentPreset = "HERO_34";
        this.baseFramedDistance = 7.2;

        // Camera States
        this.isCinematic = false;
        this.isInspection = false;
        this.isUserControlled = false;
        this.autoRotate = !this.prefersReducedMotion;

        // Smooth active transition tracking
        this.activeTransition = null;

        // Subtle environmental pointer parallax
        this.parallaxTarget = new THREE.Vector2(0, 0);
        this.parallaxCurrent = new THREE.Vector2(0, 0);
        this.parallaxEnabled = !this.prefersReducedMotion;

        // Clamping constraints for inspection mode
        // minRadius: 4.8m prevents camera from clipping vehicle geometry
        // maxRadius: 11.0m keeps vehicle well framed within environment lighting
        this.minRadius = 4.8;
        this.maxRadius = 11.0;

        // Elevation clamping:
        // minPhi: 38 deg (~0.66 rad) prevents unnatural overhead flip
        // maxPhi: 83 deg (~1.45 rad) ensures camera stays safely above asphalt
        this.minPhi = THREE.MathUtils.degToRad(38);
        this.maxPhi = THREE.MathUtils.degToRad(83);

        // Smoothing & dynamics
        this.autoRotationSpeed = 0.040; // Subtle, elegant showroom drift
        this.damping = 6.5;             // Smooth exponential damping

        // Reusable vectors for zero GC allocations during frame loops
        this._tempVecPos = new THREE.Vector3();
        this._tempVecTarget = new THREE.Vector3();

        // Initialize camera transform
        this.camera.position.copy(this.position);
        this.camera.lookAt(this.target);
    }

    // ========================================================
    // MAIN UPDATE LOOP
    // ========================================================

    update(delta) {
        // ----------------------------------------------------
        // 1. ACTIVE PROGRAMMATIC TRANSITION
        // ----------------------------------------------------
        if (this.activeTransition) {
            const tr = this.activeTransition;
            tr.elapsed += delta;
            const progress = tr.duration > 0
                ? Math.min(tr.elapsed / tr.duration, 1.0)
                : 1.0;

            const t = this.prefersReducedMotion ? 1.0 : tr.easingFn(progress);

            if (tr.isSpherical) {
                // Spherical interpolation: orbits smoothly around vehicle center
                this.radius = THREE.MathUtils.lerp(tr.startRadius, tr.targetRadius, t);
                this.theta = THREE.MathUtils.lerp(tr.startTheta, tr.targetTheta, t);
                this.phi = THREE.MathUtils.lerp(tr.startPhi, tr.targetPhi, t);

                this.targetRadius = this.radius;
                this.targetTheta = this.theta;
                this.targetPhi = this.phi;

                this.lookTarget.lerpVectors(tr.startTarget, tr.endTarget, t);
                this.target.copy(tr.endTarget);

                const sinPhi = Math.sin(this.phi);
                const cosPhi = Math.cos(this.phi);
                const sinTheta = Math.sin(this.theta);
                const cosTheta = Math.cos(this.theta);

                const x = this.lookTarget.x + this.radius * sinPhi * sinTheta;
                const y = this.lookTarget.y + this.radius * cosPhi;
                const z = this.lookTarget.z + this.radius * sinPhi * cosTheta;

                this.camera.position.set(x, y, z);
                this.camera.lookAt(this.lookTarget);
            } else {
                // Cartesian interpolation: smoothly moves position & target in world space
                this.camera.position.lerpVectors(tr.startPos, tr.endPos, t);
                this.lookTarget.lerpVectors(tr.startTarget, tr.endTarget, t);
                this.target.copy(tr.endTarget);
                this.camera.lookAt(this.lookTarget);

                this.syncSphericalFromCurrentPosition();
            }

            if (progress >= 1.0) {
                const onComplete = tr.onComplete;
                this.activeTransition = null;
                this.syncSphericalFromCurrentPosition();
                if (typeof onComplete === "function") {
                    onComplete();
                }
            }
            return;
        }

        // ----------------------------------------------------
        // 2. CINEMATIC TRACKING (e.g. DRIVE, BRAKE)
        // ----------------------------------------------------
        if (this.isCinematic) {
            this.camera.position.lerp(this.position, THREE.MathUtils.clamp(delta * 4.0, 0.02, 0.25));
            this.lookTarget.lerp(this.target, THREE.MathUtils.clamp(delta * 5.0, 0.03, 0.3));
            this.camera.lookAt(this.lookTarget);

            this.syncSphericalFromCurrentPosition();
            return;
        }

        // ----------------------------------------------------
        // 3. INSPECTION & ORBIT MODE
        // ----------------------------------------------------
        if (this.autoRotate && !this.isUserControlled && !this.prefersReducedMotion) {
            this.targetTheta += this.autoRotationSpeed * delta;
        }

        // Smooth exponential damping
        const factor = THREE.MathUtils.clamp(delta * this.damping, 0.01, 0.35);
        this.theta = THREE.MathUtils.damp(this.theta, this.targetTheta, this.damping, delta);
        this.phi = THREE.MathUtils.damp(this.phi, this.targetPhi, this.damping, delta);
        this.radius = THREE.MathUtils.damp(this.radius, this.targetRadius, this.damping, delta);

        // Subtle pointer parallax applied to target lookAt
        if (this.parallaxEnabled && !this.isUserControlled && !this.prefersReducedMotion) {
            this.parallaxCurrent.x = THREE.MathUtils.damp(this.parallaxCurrent.x, this.parallaxTarget.x, 2.5, delta);
            this.parallaxCurrent.y = THREE.MathUtils.damp(this.parallaxCurrent.y, this.parallaxTarget.y, 2.5, delta);
        } else {
            this.parallaxCurrent.x = THREE.MathUtils.damp(this.parallaxCurrent.x, 0, 4.0, delta);
            this.parallaxCurrent.y = THREE.MathUtils.damp(this.parallaxCurrent.y, 0, 4.0, delta);
        }

        this._tempVecTarget.copy(this.target);
        this._tempVecTarget.x += this.parallaxCurrent.x;
        this._tempVecTarget.y += this.parallaxCurrent.y;

        this.lookTarget.lerp(this._tempVecTarget, factor);

        // Convert spherical coordinates to Cartesian
        const sinPhi = Math.sin(this.phi);
        const cosPhi = Math.cos(this.phi);
        const sinTheta = Math.sin(this.theta);
        const cosTheta = Math.cos(this.theta);

        const x = this.lookTarget.x + this.radius * sinPhi * sinTheta;
        const y = this.lookTarget.y + this.radius * cosPhi;
        const z = this.lookTarget.z + this.radius * sinPhi * cosTheta;

        this.camera.position.set(x, y, z);
        this.camera.lookAt(this.lookTarget);
    }

    // ========================================================
    // REUSABLE TRANSITION SYSTEM
    // ========================================================

    /**
     * Reusable cinematic camera transition functionality.
     * Smoothly interpolates position & target or spherical coordinates.
     */
    transitionTo({
        position = null,
        target = null,
        spherical = null,
        duration = 1.4,
        easing = "easeInOutCubic",
        onComplete = null
    } = {}) {
        this.isCinematic = false;
        this.isUserControlled = false;

        const easingFn = typeof easing === "function"
            ? easing
            : (EASING[easing] || EASING.easeInOutCubic);

        const targetVec = target instanceof THREE.Vector3
            ? target.clone()
            : (target ? new THREE.Vector3(target.x ?? target[0], target.y ?? target[1], target.z ?? target[2]) : this.target.clone());

        if (spherical) {
            // Spherical transition
            this.syncSphericalFromCurrentPosition();
            this.activeTransition = {
                isSpherical: true,
                elapsed: 0,
                duration: this.prefersReducedMotion ? 0.05 : duration,
                startRadius: this.radius,
                startTheta: this.theta,
                startPhi: this.phi,
                targetRadius: THREE.MathUtils.clamp(spherical.radius ?? this.radius, this.minRadius, this.maxRadius),
                targetTheta: spherical.theta ?? this.theta,
                targetPhi: THREE.MathUtils.clamp(spherical.phi ?? this.phi, this.minPhi, this.maxPhi),
                startTarget: this.lookTarget.clone(),
                endTarget: targetVec,
                easingFn,
                onComplete
            };
        } else if (position) {
            // Cartesian transition
            const posVec = position instanceof THREE.Vector3
                ? position.clone()
                : new THREE.Vector3(position.x ?? position[0], position.y ?? position[1], position.z ?? position[2]);

            this.activeTransition = {
                isSpherical: false,
                elapsed: 0,
                duration: this.prefersReducedMotion ? 0.05 : duration,
                startPos: this.camera.position.clone(),
                endPos: posVec,
                startTarget: this.lookTarget.clone(),
                endTarget: targetVec,
                easingFn,
                onComplete
            };
        }
    }

    // ========================================================
    // CONTROLLED CINEMATIC VEHICLE HERO COMPOSITIONS
    // ========================================================

    /**
     * A. ARRIVAL HERO
     * Wide environmental shot. The vehicle enters naturally.
     */
    transitionToArrival() {
        this.activeTransition = null;
        this.isCinematic = true;
        this.isInspection = false;
        this.isUserControlled = false;
        this.autoRotate = false;
        this.position.set(6.8, 3.0, 9.5);
        this.target.set(0, 0.75, -16.0);
    }

    /**
     * B. PARKED HERO
     * After parking: camera settles into a strong three-quarter automotive angle.
     * Vehicle occupies ~65% of the viewport.
     */
    transitionToParkedHero(targetX = 0, targetY = 0.75, targetZ = 3.2, onComplete = null) {
        this.isCinematic = false;
        this.isInspection = true;
        this.isUserControlled = false;
        this.autoRotate = false;

        this.transitionTo({
            spherical: {
                radius: 7.2,
                theta: 0.75, // ~43° front three-quarter
                phi: 1.30    // ~74° from top, eye level
            },
            target: new THREE.Vector3(targetX, targetY, targetZ),
            duration: 1.6,
            easing: "easeInOutCubic",
            onComplete
        });
    }

    /**
     * C. INSPECTION HERO
     * Camera transitions smoothly into user-controlled orbit.
     */
    transitionToInspection(targetX = 0, targetY = 0.75, targetZ = 3.2) {
        this.isCinematic = false;
        this.isInspection = true;
        this.isUserControlled = false;
        this.autoRotate = !this.prefersReducedMotion;

        this.transitionTo({
            spherical: {
                radius: 7.4,
                theta: 0.78,
                phi: 1.30
            },
            target: new THREE.Vector3(targetX, targetY, targetZ),
            duration: 1.2,
            easing: "easeOutCubic"
        });
    }

    /**
     * D. CONFIGURATION HERO
     * Camera settles into a slightly offset composition so configuration typography has clear space.
     */
    transitionToConfiguration(targetX = -0.32, targetY = 0.72, targetZ = 3.2) {
        this.isCinematic = false;
        this.isInspection = true;
        this.isUserControlled = false;
        this.autoRotate = false; // Hold steady composition during configuration

        this.transitionTo({
            spherical: {
                radius: 6.8,
                theta: 0.82, // Slightly wider angle framing car beside UI
                phi: 1.32
            },
            target: new THREE.Vector3(targetX, targetY, targetZ),
            duration: 1.2,
            easing: "easeInOutCubic"
        });
    }

    /**
     * E. VALUATION HERO
     * Camera moves into a deliberate premium composition focusing on vehicle stance.
     */
    transitionToValuation(targetX = 0, targetY = 0.70, targetZ = 3.2) {
        this.isCinematic = false;
        this.isInspection = true;
        this.isUserControlled = false;
        this.autoRotate = false;

        this.transitionTo({
            spherical: {
                radius: 6.0,
                theta: 0.72,
                phi: 1.36 // Slightly lower elevation
            },
            target: new THREE.Vector3(targetX, targetY, targetZ),
            duration: 1.4,
            easing: "easeInOutCubic"
        });
    }

    /**
     * F. FINAL VALUE HERO
     * The final price should be presented with the strongest composition in the entire experience.
     * Low three-quarter automotive beauty shot capturing grille, stance and headlights.
     */
    transitionToFinalValue(targetX = 0, targetY = 0.68, targetZ = 3.2) {
        this.isCinematic = false;
        this.isInspection = true;
        this.isUserControlled = false;
        this.autoRotate = false;

        this.transitionTo({
            spherical: {
                radius: 5.5,
                theta: 0.62, // Tight three-quarter front stance
                phi: 1.38    // Heroic low angle looking slightly up
            },
            target: new THREE.Vector3(targetX, targetY, targetZ),
            duration: 1.8,
            easing: "easeInOutCubic"
        });
    }

    // ========================================================
    // PARALLAX & DEPTH
    // ========================================================

    setPointerParallax(normX, normY) {
        if (!this.parallaxEnabled || this.prefersReducedMotion) {
            return;
        }

        // Clamp parallax within subtle, non-distracting bounds (max 0.07m horizontal, 0.04m vertical)
        const clampedX = THREE.MathUtils.clamp(normX, -1, 1) * 0.07;
        const clampedY = THREE.MathUtils.clamp(normY, -1, 1) * 0.04;

        this.parallaxTarget.set(clampedX, clampedY);
    }

    // ========================================================
    // CINEMATIC TRACKING API
    // ========================================================

    cinematicPosition(x, y, z, lookX = 0, lookY = 0.75, lookZ = 0) {
        if (this.activeTransition) {
            return;
        }
        this.isCinematic = true;
        this.isInspection = false;
        this.position.set(x, y, z);
        this.target.set(lookX, lookY, lookZ);
    }

    endCinematic() {
        this.transitionToInspection(this.target.x, this.target.y, this.target.z);
    }

    syncSphericalFromCurrentPosition() {
        const dx = this.camera.position.x - this.target.x;
        const dy = this.camera.position.y - this.target.y;
        const dz = this.camera.position.z - this.target.z;

        const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);
        this.radius = dist;
        this.theta = Math.atan2(dx, dz);
        this.phi = Math.acos(THREE.MathUtils.clamp(dy / Math.max(dist, 0.001), -1, 1));

        this.targetRadius = this.radius;
        this.targetTheta = this.theta;
        this.targetPhi = this.phi;
    }

    // ========================================================
    // 360° INSPECTION & SMART ZOOM
    // ========================================================

    orbit(deltaTheta, deltaPhi) {
        if (this.isCinematic || this.activeTransition) {
            return;
        }

        this.isUserControlled = true;
        this.targetTheta += deltaTheta;
        this.targetPhi = THREE.MathUtils.clamp(
            this.targetPhi + deltaPhi,
            this.minPhi,
            this.maxPhi
        );
    }

    rotate(amount) {
        this.orbit(amount, 0);
    }

    changeHeight(amount) {
        this.orbit(0, -amount * 0.10);
    }

    zoom(amount) {
        if (this.isCinematic || this.activeTransition) {
            return;
        }

        this.isUserControlled = true;
        this.targetRadius = THREE.MathUtils.clamp(
            this.targetRadius + amount,
            this.minRadius,
            this.maxRadius
        );
    }

    releaseControl() {
        this.isUserControlled = false;
    }

    enableAutoRotate(enabled = true) {
        this.autoRotate = enabled && !this.prefersReducedMotion;
    }

    setTarget(x, y, z) {
        this.target.set(x, y, z);
    }

    focusVehicle(distance = 7.0, height = 2.4) {
        this.isCinematic = false;
        this.isInspection = true;
        this.targetRadius = THREE.MathUtils.clamp(distance, this.minRadius, this.maxRadius);
        const clampedY = THREE.MathUtils.clamp(height, 0.6, 4.5);
        this.targetPhi = Math.acos(THREE.MathUtils.clamp((clampedY - this.target.y) / distance, -1, 1));
        this.releaseControl();
    }

    reset(immediate = false) {
        this.isCinematic = false;
        this.isInspection = true;
        this.isUserControlled = false;
        this.activeTransition = null;
        this.target.set(0, 0.75, 3.2);

        this.targetRadius = 7.2;
        this.targetTheta = 0.75;
        this.targetPhi = 1.30;

        if (immediate) {
            this.radius = this.targetRadius;
            this.theta = this.targetTheta;
            this.phi = this.targetPhi;
            this.lookTarget.copy(this.target);

            const sinPhi = Math.sin(this.phi);
            const cosPhi = Math.cos(this.phi);
            const x = this.target.x + this.radius * sinPhi * Math.sin(this.theta);
            const y = this.target.y + this.radius * cosPhi;
            const z = this.target.z + this.radius * sinPhi * Math.cos(this.theta);

            this.camera.position.set(x, y, z);
            this.camera.lookAt(this.target);
        }
    }

    // ========================================================
    // CAMERA PRESETS & AUTO-FRAMING API (PHASE 5)
    // ========================================================

    setPreset(presetName, onComplete = null) {
        const preset = CAMERA_PRESETS[presetName];
        if (!preset) {
            console.warn(`SmartCarCamera: Unknown preset "${presetName}".`);
            return;
        }

        this.currentPreset = presetName;

        if (presetName === "TURN_TABLE") {
            this.enableAutoRotate(true);
            const targetRadius = (this.baseFramedDistance || 7.2) * (preset.spherical.radiusMultiplier || 1.0);
            this.transitionTo({
                spherical: {
                    radius: THREE.MathUtils.clamp(targetRadius, this.minRadius, this.maxRadius),
                    phi: preset.spherical.phi ?? this.phi,
                    theta: this.theta // maintain current azimuth smoothly
                },
                target: this.target,
                duration: preset.duration || 1.2,
                easing: preset.easing || "easeInOutCubic",
                onComplete
            });
            return;
        }

        // Deactivate continuous turntable rotation for fixed stance presets
        this.enableAutoRotate(false);

        const targetRadius = (this.baseFramedDistance || 7.2) * (preset.spherical.radiusMultiplier || 1.0);
        this.transitionTo({
            spherical: {
                radius: THREE.MathUtils.clamp(targetRadius, this.minRadius, this.maxRadius),
                theta: preset.spherical.theta,
                phi: THREE.MathUtils.clamp(preset.spherical.phi, this.minPhi, this.maxPhi)
            },
            target: this.target,
            duration: preset.duration || 1.4,
            easing: preset.easing || "easeInOutCubic",
            onComplete
        });
    }

    getPreset() {
        return this.currentPreset;
    }

    getCurrentPreset() {
        return this.currentPreset;
    }

    getPresets() {
        return Object.keys(CAMERA_PRESETS);
    }

    autoFrameVehicle(objectOrBox, padding = 1.22) {
        if (!objectOrBox) return this.baseFramedDistance || 7.2;

        let box = null;
        if (objectOrBox.isBox3) {
            box = objectOrBox;
        } else if (objectOrBox.isObject3D) {
            box = new THREE.Box3().setFromObject(objectOrBox);
        }

        if (!box || box.isEmpty()) return this.baseFramedDistance || 7.2;

        const center = new THREE.Vector3();
        box.getCenter(center);
        const size = new THREE.Vector3();
        box.getSize(size);

        const sphere = new THREE.Sphere();
        box.getBoundingSphere(sphere);
        const radius = Math.max(sphere.radius, 1.2);

        // Perspective camera framing calculation:
        const fov = this.camera ? (this.camera.fov || 42) : 42;
        const aspect = this.camera ? (this.camera.aspect || 1.6) : 1.6;
        const vFovRad = THREE.MathUtils.degToRad(fov);
        const hFovRad = 2 * Math.atan(Math.tan(vFovRad / 2) * Math.max(aspect, 0.5));
        const minFovRad = Math.min(vFovRad, hFovRad);

        // Required distance so sphere fits inside FOV with padding
        const frameDistance = (radius / Math.sin(minFovRad / 2)) * padding;
        const optimalDistance = THREE.MathUtils.clamp(frameDistance, 4.8, 12.5);

        // Target center with grounded eye-level height
        const targetY = Math.max(center.y, 0.65);
        this.target.set(center.x, targetY, center.z);
        this.lookTarget.copy(this.target);

        this.baseFramedDistance = optimalDistance;
        this.targetRadius = optimalDistance;
        this.minRadius = Math.max(radius * 1.1, 4.0);
        this.maxRadius = optimalDistance * 2.2;

        console.log("SmartCarCamera: Auto-framed vehicle.", {
            center: [center.x, targetY, center.z],
            size: [size.x, size.y, size.z],
            radius,
            optimalDistance,
            minRadius: this.minRadius,
            maxRadius: this.maxRadius
        });

        return optimalDistance;
    }

    adaptToVehicle(metadata, boundingBox) {
        if (boundingBox) {
            this.autoFrameVehicle(boundingBox);
        }

        if (metadata) {
            if (metadata.cameraTargetHeight !== undefined && metadata.cameraTargetZ !== undefined) {
                this.target.set(0, metadata.cameraTargetHeight, metadata.cameraTargetZ);
                this.lookTarget.copy(this.target);
            }
            if (metadata.cameraDistance) {
                this.targetRadius = metadata.cameraDistance;
                this.baseFramedDistance = metadata.cameraDistance;
            }
            if (metadata.orbitBounds) {
                if (metadata.orbitBounds.minRadius) this.minRadius = metadata.orbitBounds.minRadius;
                if (metadata.orbitBounds.maxRadius) this.maxRadius = metadata.orbitBounds.maxRadius;
                if (metadata.orbitBounds.minPhi) this.minPhi = metadata.orbitBounds.minPhi;
                if (metadata.orbitBounds.maxPhi) this.maxPhi = metadata.orbitBounds.maxPhi;
            }
        }

        console.log("SmartCarCamera: Adapted framing to vehicle asset.", {
            target: this.target,
            targetRadius: this.targetRadius,
            minRadius: this.minRadius,
            maxRadius: this.maxRadius
        });
    }

    getInspectionState() {
        return {
            isInspection: this.isInspection,
            isCinematic: this.isCinematic,
            isUserControlled: this.isUserControlled,
            theta: this.theta,
            phi: this.phi,
            radius: this.radius,
            minRadius: this.minRadius,
            maxRadius: this.maxRadius,
            minPhi: this.minPhi,
            maxPhi: this.maxPhi
        };
    }
}