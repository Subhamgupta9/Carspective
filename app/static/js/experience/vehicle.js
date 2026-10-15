// ============================================================
// SMARTCAR AI — IMMERSIVE VEHICLE MODULE
// vehicle.js — Phase 12 Advanced Automotive Visualization
// ============================================================

import * as THREE from "three";
if (typeof window !== "undefined") {
    window.THREE = THREE;
}
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { findVehicleAsset, VEHICLE_ASSET_REGISTRY } from "./vehicleAssets.js";
import { setVehicleState, getVehicleState, vehicleIdentity, vehicleState } from "./vehicleIdentity.js";
import { VehicleLoader, disposeHierarchy } from "./vehicleLoader.js";

// Canonical Automotive Finish Options (Purely Visual)
export const VEHICLE_FINISHES = [
    { id: "bronze",   name: "Slate Bronze",    hex: "#3c3a29", color: 0x3c3a29 },
    { id: "black",    name: "Obsidian Black",  hex: "#121315", color: 0x121315 },
    { id: "white",    name: "Glacier White",   hex: "#eef0f3", color: 0xeef0f3 },
    { id: "silver",   name: "Sterling Silver", hex: "#858990", color: 0x858990 },
    { id: "red",      name: "Crimson Red",     hex: "#821319", color: 0x821319 },
    { id: "blue",     name: "Deep Sapphire",   hex: "#13233e", color: 0x13233e }
];

export class SmartCarVehicle {

    constructor(scene) {
        if (!scene) {
            throw new Error("SmartCarVehicle: Scene is required.");
        }

        this.scene = scene;
        this.loader = new GLTFLoader();
        this.vehicleLoader = new VehicleLoader(this.scene);

        this.object = null;
        this.model = null;

        this.ready = false;
        this.currentAssetEntry = null;
        this.isAssetAvailable = false;
        this.loadingAsset = false;
        this.onAssetReadyCallbacks = [];
        this.onAssetUnavailableCallbacks = [];

        this.wheelPivots = [];
        this.headlightLights = [];
        this.brakeLights = [];
        this.headlightMaterials = [];
        this.brakeLightMaterials = [];

        // Body paint material preservation & safe finish customization
        this.bodyMaterials = [];
        this.defaultBodyColor = new THREE.Color(0x3c3a29);
        this.currentBodyColor = new THREE.Color(0x3c3a29);
        this.targetBodyColor = new THREE.Color(0x3c3a29);
        this.activeFinishId = "bronze";

        // Contact grounding shadow
        this.contactShadow = null;

        // Geometric ground offset: the Y displacement needed so the
        // lowest tire geometry sits exactly at y = 0 (road surface).
        // Computed by normalizeScale() after applying uniform scale.
        this.groundOffset = 0;

        this.originalPosition = new THREE.Vector3();
        this.originalRotation = new THREE.Euler();
        this.originalScale = new THREE.Vector3(1, 1, 1);

        // In the raw GLB, the car's forward axis is +X.
        // In the Three.js scene, the road runs along the Z axis,
        // and the car drives forward towards the camera along +Z.
        // Therefore, the car's base heading (forward along +Z) is -Math.PI / 2.
        this.baseHeading = -Math.PI / 2;
        this.targetHeight = 1.55;
        this.currentIdentity = null;

        // Initial default vehicle load (Porsche 911 Carrera 4S via canonical API)
        this.loadVehicle({ brand: "Porsche", model: "911", year: 2021 });
    }

    unloadCurrentVehicle() {
        if (this.contactShadow) {
            this.contactShadow.visible = false;
        }

        // 1. Delegate full recursive GPU resource disposal to VehicleLoader
        if (this.vehicleLoader) {
            this.vehicleLoader.dispose();
        }

        // Clean up lights and targets
        this.headlightLights.forEach((light) => {
            if (light.target && light.target.parent) {
                light.target.parent.remove(light.target);
            }
            if (light.parent) {
                light.parent.remove(light);
            }
        });
        this.brakeLights.forEach((light) => {
            if (light.parent) {
                light.parent.remove(light);
            }
        });

        this.headlightLights = [];
        this.brakeLights = [];
        this.headlightMaterials = [];
        this.brakeLightMaterials = [];
        this.wheelPivots = [];
        this.bodyMaterials = [];

        // Complete secondary GPU resource disposal if object still exists
        if (this.object) {
            disposeHierarchy(this.object);
            if (this.scene && this.object.parent) {
                this.scene.remove(this.object);
            }
        }

        this.object = null;
        this.model = null;
        this.ready = false;
        this.currentAssetEntry = null;
    }

    /**
     * Backward-compatible adapter for legacy callers.
     */
    loadVehicleAsset(brand, model) {
        return this.loadVehicle({
            brand: brand,
            model: model,
            year: 2021
        });
    }

    /**
     * Canonical Level 2 Vehicle Loader
     * Resolves matching 3D asset via /api/vehicle-asset.
     * If asset is unavailable, cleanly unloads active vehicle geometry.
     * 
     * @param {object} identity - Vehicle identity { brand, model, year, variant, fuel, transmission, bodyType }
     * @returns {Promise<boolean>}
     */
    async loadVehicle(identity) {
        if (!identity || !identity.brand) {
            console.warn("SmartCarVehicle.loadVehicle: Brand is required.", identity);
            return false;
        }

        const brand = identity.brand.trim();
        const model = (identity.model || "").trim();
        const year = identity.year ? parseInt(identity.year, 10) : 2021;
        const variant = (identity.variant || "").trim();
        const fuel = (identity.fuel || "").trim();
        const transmission = (identity.transmission || "").trim();
        const bodyType = (identity.bodyType || "").trim();

        // Check if same vehicle asset is already active
        if (this.currentIdentity &&
            this.currentIdentity.brand.toLowerCase() === brand.toLowerCase() &&
            this.currentIdentity.model.toLowerCase() === model.toLowerCase() &&
            this.currentIdentity.year === year &&
            this.ready &&
            this.object) {
            console.log(`SmartCarVehicle: Asset for "${brand} ${model}" (${year}) already active.`);
            return true;
        }

        console.log(`SmartCarVehicle: Resolving asset for "${brand}" "${model}" (${year})...`);
        this.loadingAsset = true;

        setVehicleState({
            loading: true,
            ready: false,
            identity: {
                brand,
                model,
                manufacturing_year: year,
                variant,
                fuel_type: fuel,
                transmission_type: transmission,
                bodytype: bodyType
            }
        });

        const statusEl = document.getElementById("experienceStatus");
        if (statusEl) {
            statusEl.textContent = "LOADING VEHICLE";
        }

        try {
            const response = await fetch("/api/vehicle-asset", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    brand,
                    model,
                    year,
                    variant,
                    fuel,
                    transmission,
                    bodyType
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error ${response.status}`);
            }

            const data = await response.json();
            console.log("SmartCarVehicle: Asset resolution response:", data);

            if (!data || !data.available || !data.asset_url) {
                console.log(`SmartCarVehicle: 3D asset unavailable for "${brand}" "${model}". Unloading active 3D model.`);
                this.unloadCurrentVehicle();
                this.isAssetAvailable = false;
                this.loadingAsset = false;
                this.currentIdentity = { brand, model, year };

                setVehicleState({
                    loading: false,
                    ready: false,
                    generation: {},
                    asset: {}
                });

                if (statusEl) {
                    statusEl.textContent = "3D MODEL PREVIEW UNAVAILABLE";
                }

                this.onAssetUnavailableCallbacks.forEach((cb) => {
                    try { cb(brand, model, data); } catch (e) { console.error("SmartCarVehicle: onAssetUnavailable error", e); }
                });

                return false;
            }

            // Asset is available! Unload previous car and load new GLB
            this.unloadCurrentVehicle();
            this.currentIdentity = { brand, model, year };

            const assetUrl = data.asset_url;
            const metadata = data.metadata || (data.asset && data.asset.metadata) || {};

            try {
                const loadResult = await this.vehicleLoader.load(
                    assetUrl,
                    { brand, model, year, variant, fuel, transmission, bodyType },
                    {
                        metadata,
                        targetHeight: metadata.targetHeight || this.targetHeight,
                        baseHeading: metadata.baseHeading !== undefined ? metadata.baseHeading : this.baseHeading
                    }
                );

                this.object = loadResult.model;
                this.model = loadResult.model;
                this.currentAssetEntry = data;
                this.isAssetAvailable = true;

                if (loadResult.normalization) {
                    this.groundOffset = loadResult.normalization.groundOffset;
                    this.targetHeight = loadResult.normalization.targetHeight;
                    this.baseHeading = loadResult.normalization.baseHeading;
                }

                // Extract body materials for paint swatch customization
                this.bodyMaterials = loadResult.model.userData?.bodyMaterials || [];
                if (this.bodyMaterials.length === 0) {
                    loadResult.model.traverse((child) => {
                        if (child.isMesh && child.material) {
                            const mats = Array.isArray(child.material) ? child.material : [child.material];
                            mats.forEach((m) => {
                                if (!this.bodyMaterials.includes(m)) this.bodyMaterials.push(m);
                            });
                        }
                    });
                }
                if (this.bodyMaterials.length > 0 && this.bodyMaterials[0].color) {
                    this.defaultBodyColor.copy(this.bodyMaterials[0].color);
                    this.currentBodyColor.copy(this.bodyMaterials[0].color);
                    this.targetBodyColor.copy(this.bodyMaterials[0].color);
                }

                this.fixDoorPresentation();

                if (!this.scene.children.includes(this.object)) {
                    this.scene.add(this.object);
                }

                this.originalPosition.copy(this.object.position);
                this.originalRotation.copy(this.object.rotation);
                this.originalScale.copy(this.object.scale);

                this.setupWheels();
                this.createLightSystem();

                this.setupContactShadow();
                if (this.contactShadow) {
                    this.contactShadow.visible = true;
                    this.contactShadow.position.z = this.object.position.z;
                    this.contactShadow.position.x = this.object.position.x;
                }

                this.ready = true;
                this.loadingAsset = false;
            } catch (loadErr) {
                console.error("SmartCarVehicle: VehicleLoader failed to load or validate asset:", loadErr);
                this.unloadCurrentVehicle();
                this.ready = false;
                this.loadingAsset = false;
                if (statusEl) statusEl.textContent = "3D MODEL PREVIEW UNAVAILABLE";
                return false;
            }

                        const assetObj = data.asset || {
                            source: "carimagesapi",
                            make_slug: (data.asset && data.asset.make_slug) || "",
                            model_slug: (data.asset && data.asset.model_slug) || "",
                            generation_slug: data.generation,
                            match_level: data.match_level,
                            fallback: data.fallback
                        };
                        const genObj = data.asset ? {
                            slug: data.asset.generation_slug,
                            name: data.asset.generation_name,
                            year_start: data.asset.year_start,
                            year_end: data.asset.year_end
                        } : { slug: data.generation };

                        setVehicleState({
                            loading: false,
                            ready: true,
                            generation: genObj,
                            asset: assetObj
                        });

                        const matchLevel = (data.asset && data.asset.match_level) || data.match_level;
                        let statusMsg = "3D MODEL PREVIEW — GENERATION MATCH";
                        if (matchLevel === "EXACT_VARIANT") {
                            statusMsg = "3D MODEL PREVIEW — EXACT VARIANT";
                        } else if (matchLevel === "GENERATION_MATCH") {
                            statusMsg = "3D MODEL PREVIEW — GENERATION MATCH";
                        } else if (matchLevel === "GENERATION_FALLBACK") {
                            statusMsg = "3D MODEL PREVIEW — GENERATION FALLBACK";
                        }

                        if (statusEl) {
                            statusEl.textContent = statusMsg;
                        }

                        const loaderEl = document.getElementById("experienceLoader");
                        if (loaderEl && !loaderEl.classList.contains("hidden")) {
                            loaderEl.classList.add("hidden");
                            setTimeout(() => {
                                loaderEl.style.display = "none";
                            }, 800);
                        }

                        const boundingBox = new THREE.Box3().setFromObject(this.object);
                        this.onAssetReadyCallbacks.forEach((cb) => {
                            try { cb(data, boundingBox, metadata); } catch (e) { console.error("SmartCarVehicle: onAssetReady error", e); }
                        });

                        console.log(`SmartCar AI: Vehicle "${brand} ${model}" (${data.generation}) loaded and ready. GroundOffset: ${this.groundOffset.toFixed(5)}`);
                        return true;

        } catch (error) {
            console.error("SmartCarVehicle: loadVehicle fetch error:", error);
            this.loadingAsset = false;
            this.unloadCurrentVehicle();
            setVehicleState({
                loading: false,
                ready: false,
                generation: {},
                asset: {}
            });
            if (statusEl) {
                statusEl.textContent = "3D MODEL PREVIEW UNAVAILABLE";
            }
            this.onAssetUnavailableCallbacks.forEach((cb) => {
                try { cb(brand, model); } catch (e) {}
            });
            return false;
        }
    }

    onAssetReady(callback) {
        if (typeof callback === "function") {
            this.onAssetReadyCallbacks.push(callback);
            if (this.ready && this.object && this.currentAssetEntry) {
                try {
                    callback(this.currentAssetEntry, new THREE.Box3().setFromObject(this.object), this.currentAssetEntry.metadata);
                } catch (e) {
                    console.error("SmartCarVehicle: onAssetReady callback error", e);
                }
            }
        }
    }

    onAssetUnavailable(callback) {
        if (typeof callback === "function") {
            this.onAssetUnavailableCallbacks.push(callback);
        }
    }

    getCurrentAsset() {
        return this.currentAssetEntry;
    }

    hasAsset() {
        return this.isAssetAvailable && !!this.object;
    }

    // ========================================================
    // SELECTIVE SHADOW CASTING
    // ========================================================

    /**
     * Determines whether a mesh should cast shadows onto the road.
     * Only exterior surfaces (body panels, windows, doors, tires,
     * exterior plastic) should cast shadows. Interior details,
     * small hardware, brakes, reflectors, and invisible/service
     * geometry are excluded to prevent detached shadow artifacts.
     */
    _shouldCastShadow(mesh) {
        const name = (mesh.name || "").toLowerCase();
        const parentName = (mesh.parent && mesh.parent.name || "").toLowerCase();

        // Never cast shadows from invisible meshes
        if (!mesh.visible) {
            return false;
        }

        // Explicit exclusion list: interior and small-detail meshes
        // that produce detached black circular shadow spots on the road
        const excludePatterns = [
            // Interior
            "leather_all",   "leather_int",  "leather_seam", "leather_perforated",
            "plastic_all",   "bl_pl_m_int",  "interior_grid",
            "upholstery",    "rug_interior",  "rugs_all",
            "chrome_int",    "chrom_int",
            "carbon_int",    "carbon_all",
            "steering",      "monitor",       "monitors",
            "belts",         "plast_leather",
            "glossy_plastic",
            "reisin",
            // Small hardware
            "brakes",        "brake",
            "pipes",         "pipe",
            "reflector",
            "screw",         "black_metal",
            "logo",
            "number_plate",
            // Invisible / service geometry
            "invisible",     "service_black",
            "body_circles",
            // Interior door details (leather, plastic, chrome INSIDE doors)
            "chrome_door",   "chrome__door",
            "leathplast_door", "leath_plast_door",
            "plastic_door",
            "carbon__door",
            "dynamic_door",  "dynamics_door",
            "reisin__door",
            // Headlight internals (small grids/rings produce spots)
            "hedlights_grid", "headlights_grid",
            "headlights_plastic_ring",
            // Metal interior parts
            "metal_parts",
            // Mirror internals
            "mirror_middle", "mirror_door", "mirror_cover"
        ];

        for (const pattern of excludePatterns) {
            if (name.includes(pattern) || parentName.includes(pattern)) {
                return false;
            }
        }

        // Everything else (body panels, windows, exterior plastic,
        // tires, wheel rims, discs, doors body, lights housing) may cast
        return true;
    }

    // ========================================================
    // ASSET NORMALIZATION & GROUNDING PIPELINE (PHASE E)
    // ========================================================

    normalizeVehicle(metadata = null) {
        if (!this.object) {
            return;
        }

        // 1. Compute raw bounding box & dimensions
        const rawBox = new THREE.Box3().setFromObject(this.object);
        const rawSize = new THREE.Vector3();
        rawBox.getSize(rawSize);

        console.log(
            `SmartCar AI: Raw asset bounds: min=(${rawBox.min.x.toFixed(3)}, ${rawBox.min.y.toFixed(3)}, ${rawBox.min.z.toFixed(3)}), ` +
            `max=(${rawBox.max.x.toFixed(3)}, ${rawBox.max.y.toFixed(3)}, ${rawBox.max.z.toFixed(3)}), ` +
            `size=(L:${rawSize.z.toFixed(3)}, W:${rawSize.x.toFixed(3)}, H:${rawSize.y.toFixed(3)})`
        );

        if (rawSize.y <= 0) {
            return;
        }

        // 2. Uniform scale normalization
        const targetHeight = (metadata && metadata.targetHeight) ? metadata.targetHeight : (this.targetHeight || 1.45);
        this.targetHeight = targetHeight;
        const scale = targetHeight / rawSize.y;
        this.object.scale.setScalar(scale);
        this.object.updateMatrixWorld(true);

        // 4. Orientation
        const baseHeading = (metadata && metadata.baseHeading !== undefined) ? metadata.baseHeading : this.baseHeading;
        this.baseHeading = baseHeading;
        this.object.rotation.order = "YXZ";
        this.object.rotation.set(0, this.baseHeading, 0);
        this.object.updateMatrixWorld(true);

        // 3. Grounding
        // After scaling, compute world-space lowest point (box.min.y).
        // groundOffset = -scaledBox.min.y ensures lowest tyre contact patch is at y = 0.000.
        const scaledBox = new THREE.Box3().setFromObject(this.object);
        if (scaledBox.min.y < 0) {
            this.groundOffset = -scaledBox.min.y;
        } else {
            this.groundOffset = 0;
        }

        const exp = window.smartCarExperience;
        const anim = exp ? exp.getAnimation() : null;
        const isAlreadyParked = anim && (anim.sequenceInitialized || anim.state !== "DRIVE");

        if (isAlreadyParked) {
            this.object.position.set(0, this.groundOffset, 3.2);
        } else {
            this.object.position.set(0, this.groundOffset, -16.0);
        }
        this.object.updateMatrixWorld(true);

        if (this.contactShadow) {
            this.contactShadow.visible = true;
            this.contactShadow.position.set(0, 0.003, this.object.position.z);
        }

        console.log(
            `SmartCar AI: Vehicle normalized & grounded. Scale: ${scale.toFixed(6)}, ` +
            `GroundOffset: ${this.groundOffset.toFixed(6)}, TargetHeight: ${targetHeight.toFixed(3)}`
        );
    }

    normalizeScale() {
        this.normalizeVehicle();
    }

    // ========================================================
    // DOOR PRESENTATION FIX
    // ========================================================

    fixDoorPresentation() {
        if (!this.model) {
            return;
        }

        const door1 = this.model.getObjectByName("door_1");
        const door2 = this.model.getObjectByName("door_2");

        if (door2 && door1) {
            door2.position.set(0, 0, 0);
            door2.quaternion.copy(door1.quaternion);
            door2.scale.set(1, 1, 1);
            door2.updateMatrix();
        }
    }

    getBaseYaw() {
        return this.baseHeading;
    }

    // ========================================================
    // ENVIRONMENTAL GROUNDING (CONTACT SHADOW)
    // ========================================================

    setupContactShadow() {
        if (this.contactShadow) {
            this.contactShadow.visible = true;
            if (this.object) {
                this.contactShadow.position.z = this.object.position.z;
                this.contactShadow.position.x = this.object.position.x;
            }
            return;
        }

        // Procedural high-resolution ambient occlusion contact shadow texture
        const canvas = document.createElement("canvas");
        canvas.width = 512;
        canvas.height = 512;
        const ctx = canvas.getContext("2d");
        if (!ctx) return;

        ctx.clearRect(0, 0, 512, 512);

        // Undercarriage soft core shadow
        const coreGrad = ctx.createRadialGradient(256, 256, 30, 256, 256, 210);
        coreGrad.addColorStop(0, "rgba(0, 0, 0, 0.88)");
        coreGrad.addColorStop(0.5, "rgba(0, 0, 0, 0.45)");
        coreGrad.addColorStop(1, "rgba(0, 0, 0, 0)");
        ctx.fillStyle = coreGrad;
        ctx.fillRect(0, 0, 512, 512);

        // 4 tire contact patch spots directly beneath the wheel hubs
        const drawTirePatch = (cx, cy) => {
            const tireGrad = ctx.createRadialGradient(cx, cy, 8, cx, cy, 48);
            tireGrad.addColorStop(0, "rgba(0, 0, 0, 0.95)");
            tireGrad.addColorStop(0.6, "rgba(0, 0, 0, 0.50)");
            tireGrad.addColorStop(1, "rgba(0, 0, 0, 0)");
            ctx.fillStyle = tireGrad;
            ctx.beginPath();
            ctx.ellipse(cx, cy, 38, 24, 0, 0, Math.PI * 2);
            ctx.fill();
        };

        drawTirePatch(155, 140); // Front Left
        drawTirePatch(357, 140); // Front Right
        drawTirePatch(155, 372); // Rear Left
        drawTirePatch(357, 372); // Rear Right

        const shadowTex = new THREE.CanvasTexture(canvas);
        shadowTex.colorSpace = THREE.SRGBColorSpace;

        const shadowGeo = new THREE.PlaneGeometry(2.35, 4.65);
        const shadowMat = new THREE.MeshBasicMaterial({
            map: shadowTex,
            transparent: true,
            opacity: 0.65,
            depthWrite: false
        });

        this.contactShadow = new THREE.Mesh(shadowGeo, shadowMat);
        this.contactShadow.rotation.x = -Math.PI / 2;
        this.contactShadow.position.set(0, 0.003, this.object ? this.object.position.z : 0);
        this.contactShadow.name = "smartCarContactShadow";

        this.scene.add(this.contactShadow);
    }

    // ========================================================
    // WHEEL ASSEMBLY & ROTATION
    // ========================================================

    setupWheels() {
        if (!this.model) {
            return;
        }

        this.wheelPivots = [];

        const wheelSpecs = [
            { name: "frontLeft",  center: new THREE.Vector3(-103.82, 77.85, 18.89),  radius: 33.62 },
            { name: "frontRight", center: new THREE.Vector3(-103.82, -77.85, 18.89), radius: 33.62 },
            { name: "rearLeft",   center: new THREE.Vector3(-348.95, 78.48, 19.36),  radius: 35.35 },
            { name: "rearRight",  center: new THREE.Vector3(-348.95, -78.48, 19.36), radius: 35.35 }
        ];

        const wheelMeshNames = [
            "AO_tire_main_tires_0",
            "wheel_rim_rim_chrome_0",
            "wheel_rim_rim_black_0",
            "discs_Discs_0"
        ];

        const wheelMeshes = wheelMeshNames
            .map((name) => this.model.getObjectByName(name))
            .filter(Boolean);

        if (!wheelMeshes.length) {
            console.warn("SmartCarVehicle: Wheel meshes not found; wheel rotation disabled.");
            return;
        }

        const anchorNode = wheelMeshes[0].parent;
        if (!anchorNode) {
            console.warn("SmartCarVehicle: Wheel anchor node not found.");
            return;
        }

        const scaleFactor = this.object.scale.x;
        const pivots = [];

        wheelSpecs.forEach((spec) => {
            const pivot = new THREE.Group();
            pivot.name = `${spec.name}Pivot`;
            pivot.position.copy(spec.center);
            anchorNode.add(pivot);

            const worldRadius = (spec.radius / 100) * scaleFactor;
            const pivotEntry = {
                name: spec.name,
                pivot: pivot,
                radius: (worldRadius > 0.05 && worldRadius < 1.0) ? worldRadius : 0.39
            };

            pivots.push(pivotEntry);
            this.wheelPivots.push(pivotEntry);
        });

        wheelMeshes.forEach((mesh) => {
            const geom = mesh.geometry;
            if (!geom || !geom.index || !geom.attributes.position) {
                return;
            }

            const posAttr = geom.attributes.position;
            const indexArray = geom.index.array;
            const wheelIndices = [[], [], [], []];

            for (let i = 0; i < indexArray.length; i += 3) {
                const i0 = indexArray[i];
                const x = posAttr.getX(i0);
                const y = posAttr.getY(i0);

                const isFront = x > -220;
                const isLeft = y > 0;
                const wIdx = isFront ? (isLeft ? 0 : 1) : (isLeft ? 2 : 3);

                wheelIndices[wIdx].push(indexArray[i], indexArray[i + 1], indexArray[i + 2]);
            }

            for (let w = 0; w < 4; w++) {
                if (wheelIndices[w].length === 0) {
                    continue;
                }

                const subGeom = geom.clone();
                const IndexCtor = subGeom.index.array.constructor;
                const newIndex = new IndexCtor(wheelIndices[w].length);
                newIndex.set(wheelIndices[w]);
                subGeom.setIndex(new THREE.BufferAttribute(newIndex, 1));

                const center = wheelSpecs[w].center;
                subGeom.translate(-center.x, -center.y, -center.z);

                const subMesh = new THREE.Mesh(subGeom, mesh.material);
                subMesh.name = `${mesh.name}_${wheelSpecs[w].name}`;
                subMesh.castShadow = true;
                subMesh.receiveShadow = true;

                pivots[w].pivot.add(subMesh);
            }

            mesh.visible = false;
        });

        console.log("SmartCarVehicle: 4 independent wheel assemblies ready.");
    }

    rotateWheels(distance) {
        if (!this.wheelPivots.length) {
            return;
        }

        this.wheelPivots.forEach((wheel) => {
            const rotationAmount = distance / wheel.radius;
            wheel.pivot.rotation.z -= rotationAmount;
        });
    }

    resetWheels() {
        this.steeringAngle = 0;
        this.wheelPivots.forEach((wheel) => {
            wheel.pivot.rotation.set(0, 0, 0);
        });
    }

    setSteeringAngle(angle) {
        this.steeringAngle = angle;
        if (!this.wheelPivots || !this.wheelPivots.length) {
            return;
        }
        this.wheelPivots.forEach((wheel) => {
            if (wheel.name && (wheel.name.startsWith("front") || wheel.name.includes("Front"))) {
                wheel.pivot.rotation.y = angle;
            }
        });
    }

    getSteeringAngle() {
        return this.steeringAngle || 0;
    }

    // ========================================================
    // PHYSICALLY-ALIGNED LIGHTING SYSTEM
    // ========================================================

    createLightSystem() {
        if (!this.model) {
            return;
        }

        this.headlightLights = [];
        this.brakeLights = [];
        this.headlightMaterials = [];
        this.brakeLightMaterials = [];

        // 1. FRONT HEADLIGHTS
        const headlightNode = this.model.getObjectByName("headlights_flash_lights_0")
            || this.model.getObjectByName("headlights_flash");

        if (headlightNode && headlightNode.isMesh && headlightNode.geometry && headlightNode.geometry.attributes.position) {
            const posAttr = headlightNode.geometry.attributes.position;

            const leftSum = new THREE.Vector3();
            let leftCount = 0;
            const rightSum = new THREE.Vector3();
            let rightCount = 0;

            for (let i = 0; i < posAttr.count; i++) {
                const y = posAttr.getY(i);
                const v = new THREE.Vector3(posAttr.getX(i), y, posAttr.getZ(i));
                if (y > 0) {
                    leftSum.add(v);
                    leftCount++;
                } else {
                    rightSum.add(v);
                    rightCount++;
                }
            }

            const leftLampPos = leftCount > 0
                ? leftSum.divideScalar(leftCount)
                : new THREE.Vector3(-60.29, 69.86, 56.90);

            const rightLampPos = rightCount > 0
                ? rightSum.divideScalar(rightCount)
                : new THREE.Vector3(-60.29, -69.86, 56.90);

            const forwardOffset = 400;
            const downOffset = -30;

            // Left SpotLight
            const leftSpot = new THREE.SpotLight(0xffffff, 45, 30, Math.PI / 7, 0.45, 1.5);
            leftSpot.position.copy(leftLampPos);

            const leftTarget = new THREE.Object3D();
            leftTarget.position.set(leftLampPos.x + forwardOffset, leftLampPos.y, leftLampPos.z + downOffset);

            headlightNode.add(leftSpot);
            headlightNode.add(leftTarget);
            leftSpot.target = leftTarget;
            this.headlightLights.push(leftSpot);

            // Right SpotLight
            const rightSpot = new THREE.SpotLight(0xffffff, 45, 30, Math.PI / 7, 0.45, 1.5);
            rightSpot.position.copy(rightLampPos);

            const rightTarget = new THREE.Object3D();
            rightTarget.position.set(rightLampPos.x + forwardOffset, rightLampPos.y, rightLampPos.z + downOffset);

            headlightNode.add(rightSpot);
            headlightNode.add(rightTarget);
            rightSpot.target = rightTarget;
            this.headlightLights.push(rightSpot);
        } else if (this.object) {
            // Dynamic bounds-based headlight anchoring (Phase G)
            const box = new THREE.Box3().setFromObject(this.object);
            const size = new THREE.Vector3();
            box.getSize(size);

            const frontZ = box.max.z - 0.05;
            const lampY = box.min.y + size.y * 0.60;
            const halfWidth = (size.x * 0.70) / 2;

            const leftSpot = new THREE.SpotLight(0xffffff, 45, 30, Math.PI / 7, 0.45, 1.5);
            leftSpot.position.set(-halfWidth, lampY, frontZ);
            const leftTarget = new THREE.Object3D();
            leftTarget.position.set(-halfWidth, lampY - 0.2, frontZ + 20);
            this.scene.add(leftSpot);
            this.scene.add(leftTarget);
            leftSpot.target = leftTarget;
            this.headlightLights.push(leftSpot);

            const rightSpot = new THREE.SpotLight(0xffffff, 45, 30, Math.PI / 7, 0.45, 1.5);
            rightSpot.position.set(halfWidth, lampY, frontZ);
            const rightTarget = new THREE.Object3D();
            rightTarget.position.set(halfWidth, lampY - 0.2, frontZ + 20);
            this.scene.add(rightSpot);
            this.scene.add(rightTarget);
            rightSpot.target = rightTarget;
            this.headlightLights.push(rightSpot);
        }

        // 2. REAR BRAKE LIGHTS
        const rearNode = this.model.getObjectByName("red_light_back_red_light_main_0")
            || this.model.getObjectByName("red_light_back");

        if (rearNode && rearNode.isMesh && rearNode.geometry && rearNode.geometry.attributes.position) {
            const posAttr = rearNode.geometry.attributes.position;

            const leftRearSum = new THREE.Vector3();
            let leftRearCount = 0;
            const rightRearSum = new THREE.Vector3();
            let rightRearCount = 0;

            for (let i = 0; i < posAttr.count; i++) {
                const y = posAttr.getY(i);
                const v = new THREE.Vector3(posAttr.getX(i), y, posAttr.getZ(i));
                if (y > 0) {
                    leftRearSum.add(v);
                    leftRearCount++;
                } else {
                    rightRearSum.add(v);
                    rightRearCount++;
                }
            }

            const leftRearPos = leftRearCount > 0
                ? leftRearSum.divideScalar(leftRearCount)
                : new THREE.Vector3(-426.37, 40.00, 61.84);

            const rightRearPos = rightRearCount > 0
                ? rightRearSum.divideScalar(rightRearCount)
                : new THREE.Vector3(-426.44, -36.53, 61.84);

            const leftBrake = new THREE.PointLight(0xff1600, 6, 6);
            leftBrake.position.copy(leftRearPos);
            rearNode.add(leftBrake);
            this.brakeLights.push(leftBrake);

            const rightBrake = new THREE.PointLight(0xff1600, 6, 6);
            rightBrake.position.copy(rightRearPos);
            rearNode.add(rightBrake);
            this.brakeLights.push(rightBrake);
        } else if (this.object) {
            // Dynamic bounds-based taillight anchoring (Phase G)
            const box = new THREE.Box3().setFromObject(this.object);
            const size = new THREE.Vector3();
            box.getSize(size);

            const rearZ = box.min.z + 0.05;
            const rearY = box.min.y + size.y * 0.65;
            const halfWidth = (size.x * 0.70) / 2;

            const leftBrake = new THREE.PointLight(0xff1600, 6, 6);
            leftBrake.position.set(-halfWidth, rearY, rearZ);
            this.scene.add(leftBrake);
            this.brakeLights.push(leftBrake);

            const rightBrake = new THREE.PointLight(0xff1600, 6, 6);
            rightBrake.position.set(halfWidth, rearY, rearZ);
            this.scene.add(rightBrake);
            this.brakeLights.push(rightBrake);
        }

        // 3. EMISSIVE PBR MATERIALS ENHANCEMENT
        this.model.traverse((child) => {
            if (!child.isMesh || !child.material) {
                return;
            }

            const materials = Array.isArray(child.material)
                ? child.material
                : [child.material];

            materials.forEach((material) => {
                if (!material || !material.name) {
                    return;
                }

                const name = material.name.toLowerCase();
                if (name.includes("headlight") || name.includes("lights_pattern") || name.includes("flash") || name === "lights") {
                    this.headlightMaterials.push(material);
                }

                if (name.includes("red_light") || name.includes("brake")) {
                    this.brakeLightMaterials.push(material);
                }
            });
        });

        this.setHeadlights(true);
        this.setBrakeLights(false);
    }

    get headlightsActive() {
        return this.headlightLights.some((light) => light.intensity > 0);
    }

    setHeadlights(enabled) {
        this.headlightLights.forEach((light) => {
            light.intensity = enabled ? 45 : 0;
        });

        this.headlightMaterials.forEach((material) => {
            if (material.emissive) {
                material.emissive.setHex(0xd8e8ff);
                material.emissiveIntensity = enabled ? 3.0 : 0.35;
            }
        });
    }

    flashHeadlights() {
        this.setHeadlights(true);
        setTimeout(() => {
            this.setHeadlights(false);
        }, 180);
    }

    setBrakeLights(enabled) {
        this.brakeLights.forEach((light) => {
            light.intensity = enabled ? 12 : 0.5;
        });

        this.brakeLightMaterials.forEach((material) => {
            if (material.emissive) {
                material.emissive.setHex(0xff1100);
                material.emissiveIntensity = enabled ? 3.8 : 0.4;
            }
        });
    }

    // ========================================================
    // VEHICLE FINISH (BODY COLOR INTERACTION)
    // ========================================================

    setBodyColor(colorInput, immediate = false) {
        if (!this.bodyMaterials.length) {
            return;
        }

        let targetColor = null;
        if (typeof colorInput === "string") {
            const found = VEHICLE_FINISHES.find(f => f.id === colorInput || f.hex.toLowerCase() === colorInput.toLowerCase());
            if (found) {
                this.activeFinishId = found.id;
                targetColor = new THREE.Color(found.color);
            } else {
                targetColor = new THREE.Color(colorInput);
            }
        } else if (typeof colorInput === "number") {
            targetColor = new THREE.Color(colorInput);
        } else if (colorInput instanceof THREE.Color) {
            targetColor = colorInput.clone();
        }

        if (!targetColor) {
            return;
        }

        this.targetBodyColor.copy(targetColor);

        if (immediate) {
            this.currentBodyColor.copy(targetColor);
            this.bodyMaterials.forEach((mat) => {
                mat.color.copy(this.currentBodyColor);
            });
        }
    }

    getBodyColor() {
        return `#${this.currentBodyColor.getHexString()}`;
    }

    getActiveFinishId() {
        return this.activeFinishId;
    }

    getBodyColorOptions() {
        return VEHICLE_FINISHES;
    }

    // ========================================================
    // PUBLIC API & UPDATES
    // ========================================================

    getObject() {
        return this.object;
    }

    getModel() {
        return this.model;
    }

    isReady() {
        return this.ready && !!this.object;
    }

    getGroundOffset() {
        return this.groundOffset;
    }

    setPosition(x, y, z) {
        if (!this.object) {
            return;
        }
        this.object.position.set(x, y, z);
    }

    setRotation(x, y, z) {
        if (!this.object) {
            return;
        }
        this.object.rotation.set(x, y, z);
    }

    setScale(scale, y = scale, z = scale) {
        if (!this.object) {
            return;
        }
        if (arguments.length === 1) {
            this.object.scale.setScalar(scale);
            return;
        }
        this.object.scale.set(scale, y, z);
    }

    rotate(x, y = 0, z = 0) {
        if (!this.object) {
            return;
        }
        if (arguments.length === 1) {
            this.object.rotation.y += x;
            return;
        }
        this.object.rotation.x += x;
        this.object.rotation.y += y;
        this.object.rotation.z += z;
    }

    reset() {
        if (!this.object) {
            return;
        }

        this.object.position.copy(this.originalPosition);
        this.object.rotation.copy(this.originalRotation);
        this.object.scale.copy(this.originalScale);
        this.resetWheels();
        this.setBrakeLights(false);
    }

    update(delta) {
        if (!this.object) {
            return;
        }

        // 1. Smooth Paint Color Interpolation
        if (this.bodyMaterials.length > 0 && this.targetBodyColor) {
            const diff = Math.hypot(
                this.currentBodyColor.r - this.targetBodyColor.r,
                this.currentBodyColor.g - this.targetBodyColor.g,
                this.currentBodyColor.b - this.targetBodyColor.b
            );
            if (diff > 0.001) {
                this.currentBodyColor.lerp(this.targetBodyColor, THREE.MathUtils.clamp(delta * 4.5, 0.02, 0.30));
                this.bodyMaterials.forEach((mat) => {
                    mat.color.copy(this.currentBodyColor);
                });
            }
        }

        // 2. Synchronize Physical Contact Grounding Shadow Position
        if (this.contactShadow) {
            this.contactShadow.position.z = this.object.position.z;
            this.contactShadow.position.x = this.object.position.x;
        }
    }

    dispose() {
        this.unloadCurrentVehicle();

        if (this.contactShadow && this.contactShadow.parent) {
            this.contactShadow.parent.remove(this.contactShadow);
            if (this.contactShadow.geometry) this.contactShadow.geometry.dispose();
            if (this.contactShadow.material) this.contactShadow.material.dispose();
            this.contactShadow = null;
        }

        this.onAssetReadyCallbacks = [];
        this.onAssetUnavailableCallbacks = [];
    }

    getMemoryStats() {
        if (this.vehicleLoader && typeof this.vehicleLoader.getMemoryStats === "function") {
            return this.vehicleLoader.getMemoryStats();
        }
        return {
            geometries: 0,
            materials: 0,
            textures: 0,
            hasActiveModel: !!this.object
        };
    }
}
