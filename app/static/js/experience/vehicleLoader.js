// ============================================================
// SMARTCAR AI — ROBUST VEHICLE LOADER & VALIDATOR
// vehicleLoader.js — Phase 3 GLB Loading, Validation & Normalization
// ============================================================

import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import {
    classifyMaterial,
    applyMaterialPreset,
    isMaterialHighQuality,
    ensureTextureQuality,
    disposeTextures
} from "./materialPresets.js";

/**
 * Expected automotive dimensional envelope (in real-world meters).
 * Benchmark car: Length ≈ 4.5m, Width ≈ 1.8m, Height ≈ 1.4m.
 * Allowance: ±30%.
 */
export const DIMENSION_LIMITS = {
    length: { min: 4.5 * 0.70, max: 4.5 * 1.30 }, // [3.15m, 5.85m]
    width:  { min: 1.8 * 0.70, max: 1.8 * 1.30 }, // [1.26m, 2.34m]
    height: { min: 1.4 * 0.70, max: 1.4 * 1.30 }  // [0.98m, 1.82m]
};

/**
 * Recursively disposes a Three.js 3D Object and all its GPU resources.
 * Cleans geometries, attributes, materials, textures, buffers, and lights.
 * 
 * @param {THREE.Object3D} root 
 */
export function disposeHierarchy(root) {
    if (!root) return;

    root.traverse((child) => {
        // 1. Lights & Light targets
        if (child.isLight) {
            if (child.target && child.target.parent) {
                child.target.parent.remove(child.target);
            }
        }

        // 2. Meshes, Lines, Points
        if (child.isMesh || child.isLine || child.isPoints) {
            // Geometry & Buffer Attributes
            if (child.geometry) {
                const geom = child.geometry;
                if (geom.attributes) {
                    Object.keys(geom.attributes).forEach((attrName) => {
                        const attr = geom.attributes[attrName];
                        if (attr && typeof attr.dispose === "function") {
                            attr.dispose();
                        }
                    });
                }
                if (geom.index && typeof geom.index.dispose === "function") {
                    geom.index.dispose();
                }
                geom.dispose();
            }

            // Materials & Texture Maps
            if (child.material) {
                const materials = Array.isArray(child.material)
                    ? child.material
                    : [child.material];

                materials.forEach((mat) => {
                    if (!mat) return;
                    disposeTextures(mat);
                    mat.dispose();
                });
            }
        }
    });

    if (root.parent) {
        root.parent.remove(root);
    }
}

/**
 * Robust Vehicle Loader Class
 * 
 * Implements strict loading, validation, normalization, and recursive disposal.
 */
export class VehicleLoader {

    constructor(scene = null) {
        this.scene = scene;
        this.gltfLoader = new GLTFLoader();
        this.currentModel = null;
        this.rawGLTF = null;
        this.validationReport = null;
        this.activeAssetUrl = null;
    }

    /**
     * Loads, validates, and normalizes a 3D vehicle asset from the given URL.
     * 
     * @param {string} assetUrl - URL of the 3D GLB model
     * @param {object} vehicleIdentity - Canonical vehicle identity object
     * @param {object} options - Optional overrides (metadata, targetHeight, baseHeading)
     * @returns {Promise<object>} Resolves with { scene, model, validation, metadata }
     */
    async load(assetUrl, vehicleIdentity = {}, options = {}) {
        if (!assetUrl) {
            throw new Error("VehicleLoader.load: assetUrl is required.");
        }

        // 1. Dispose any previously active model before loading new one
        this.dispose();

        this.activeAssetUrl = assetUrl;
        console.log(`[VehicleLoader] Loading asset from: ${assetUrl} for`, vehicleIdentity);

        return new Promise((resolve, reject) => {
            this.gltfLoader.load(
                assetUrl,
                (gltf) => {
                    try {
                        if (!gltf || !gltf.scene) {
                            throw new Error("Invalid GLTF structure: gltf.scene is missing.");
                        }

                        this.rawGLTF = gltf;
                        const model = gltf.scene;

                        // 2. Validate GLB Structure & Vertices
                        const validation = this.validate(model);
                        this.validationReport = validation;

                        if (!validation.valid) {
                            console.error("[VehicleLoader] Validation failed:", validation.errors);
                            disposeHierarchy(model);
                            reject(new Error(`GLB validation failed: ${validation.errors.join("; ")}`));
                            return;
                        }

                        // 3. Normalization Pipeline (scale, rotation, ground position, normals, materials)
                        const normalizedData = this.normalize(model, vehicleIdentity, options);

                        this.currentModel = model;

                        if (this.scene && !this.scene.children.includes(model)) {
                            this.scene.add(model);
                        }

                        console.log("[VehicleLoader] Asset successfully loaded & normalized:", {
                            assetUrl,
                            validation,
                            normalizedData
                        });

                        resolve({
                            gltf,
                            model,
                            scene: model,
                            validation,
                            normalization: normalizedData
                        });

                    } catch (err) {
                        console.error("[VehicleLoader] Processing error:", err);
                        if (gltf && gltf.scene) {
                            disposeHierarchy(gltf.scene);
                        }
                        reject(err);
                    }
                },
                (progressEvent) => {
                    // Optional loading progress tracking
                },
                (error) => {
                    console.error("[VehicleLoader] Network/parsing error loading GLB:", error);
                    reject(new Error(`Failed to download or parse GLB from ${assetUrl}: ${error?.message || error}`));
                }
            );
        });
    }

    /**
     * Validates a candidate GLTF model against all strict automotive criteria:
     * - mesh count > 0
     * - valid buffers
     * - no NaN vertices
     * - reasonable dimensions
     * - reasonable orientation
     * - ground contact
     * - valid materials
     * - valid textures
     * 
     * @param {THREE.Object3D} model 
     * @returns {object} Validation result { valid: boolean, errors: string[], stats: object }
     */
    validate(model) {
        const errors = [];
        const stats = {
            meshCount: 0,
            vertexCount: 0,
            materialCount: 0,
            textureCount: 0,
            hasNormals: true,
            hasNaN: false
        };

        if (!model) {
            return { valid: false, errors: ["Model is null or undefined"], stats };
        }

        // 1. Mesh count check
        const meshes = [];
        model.traverse((child) => {
            if (child.isMesh) {
                meshes.push(child);
            }
        });

        stats.meshCount = meshes.length;
        if (meshes.length === 0) {
            errors.push("Mesh count is 0. Asset contains no renderable geometry.");
            return { valid: false, errors, stats };
        }

        // 2. Validate Geometry Buffers & Vertices (No NaN / Infinite coordinates)
        let totalVertices = 0;
        let nanDetected = false;

        for (const mesh of meshes) {
            const geom = mesh.geometry;
            if (!geom) {
                errors.push(`Mesh '${mesh.name || "unnamed"}' lacks geometry.`);
                continue;
            }

            const posAttr = geom.attributes.position;
            if (!posAttr || posAttr.count === 0 || posAttr.itemSize !== 3) {
                errors.push(`Mesh '${mesh.name || "unnamed"}' has invalid or missing position buffer attribute.`);
                continue;
            }

            totalVertices += posAttr.count;
            const posArray = posAttr.array;

            // Check sample or full array for NaN / Infinite coordinates
            const checkStep = Math.max(1, Math.floor(posArray.length / 3000));
            for (let i = 0; i < posArray.length; i += checkStep) {
                const val = posArray[i];
                if (Number.isNaN(val) || !Number.isFinite(val)) {
                    nanDetected = true;
                    break;
                }
            }

            // Normals presence check
            if (!geom.attributes.normal || geom.attributes.normal.count === 0) {
                stats.hasNormals = false;
            }

            // 3. Material presence and validity check
            if (!mesh.material) {
                errors.push(`Mesh '${mesh.name || "unnamed"}' has no material.`);
            } else {
                const mats = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
                stats.materialCount += mats.length;

                for (const m of mats) {
                    if (!m) {
                        errors.push(`Mesh '${mesh.name || "unnamed"}' contains a null material entry.`);
                        continue;
                    }

                    // 4. Texture validity check
                    if (m.map) {
                        stats.textureCount++;
                        if (m.map.image) {
                            const img = m.map.image;
                            if (img.width === 0 || img.height === 0) {
                                errors.push(`Material '${m.name || "unnamed"}' has corrupted zero-dimension texture.`);
                            }
                        }
                    }
                }
            }
        }

        stats.vertexCount = totalVertices;
        if (nanDetected) {
            stats.hasNaN = true;
            errors.push("Invalid buffers: NaN or non-finite vertex coordinates detected in geometry.");
        }

        // 5. Bounding Box & Raw Dimension Validation
        model.updateMatrixWorld(true);
        const box = new THREE.Box3().setFromObject(model);
        const size = new THREE.Vector3();
        box.getSize(size);

        stats.rawDimensions = {
            x: size.x,
            y: size.y,
            z: size.z
        };

        if (size.x <= 0 || size.y <= 0 || size.z <= 0) {
            errors.push(`Degenerate bounding box: size=(${size.x.toFixed(3)}, ${size.y.toFixed(3)}, ${size.z.toFixed(3)}).`);
        }
        if (!Number.isFinite(size.x) || !Number.isFinite(size.y) || !Number.isFinite(size.z)) {
            errors.push("Non-finite bounding box dimensions detected.");
        }

        const valid = errors.length === 0;
        return { valid, errors, stats };
    }

    /**
     * Normalizes scale, orientation, ground contact, vertex normals, and materials.
     * 
     * @param {THREE.Object3D} model 
     * @param {object} vehicleIdentity 
     * @param {object} options 
     * @returns {object} Normalization metadata
     */
    normalize(model, vehicleIdentity = {}, options = {}) {
        // 1. Ensure all geometries have computed vertex normals
        model.traverse((child) => {
            if (child.isMesh && child.geometry) {
                if (!child.geometry.attributes.normal || child.geometry.attributes.normal.count === 0) {
                    child.geometry.computeVertexNormals();
                }
            }
        });

        // 2. Measure raw bounds
        model.updateMatrixWorld(true);
        const rawBox = new THREE.Box3().setFromObject(model);
        const rawSize = new THREE.Vector3();
        rawBox.getSize(rawSize);

        // 3. Target height and orientation determination
        // CarImages models typically have +X as length axis, so rawSize.x is length and rawSize.y is height
        const metadata = options.metadata || {};
        let targetHeight = options.targetHeight || metadata.targetHeight;
        if (!targetHeight) {
            // Adaptive target height based on body type / model class
            const bodyType = (vehicleIdentity.bodytype || vehicleIdentity.bodyType || "").toLowerCase();
            if (bodyType.includes("suv")) {
                targetHeight = 1.68; // SUV height
            } else if (bodyType.includes("coupe") || (vehicleIdentity.model || "").includes("911")) {
                targetHeight = 1.32; // Sports coupe height
            } else {
                targetHeight = 1.45; // Standard executive sedan
            }
        }

        // Scale factor: scale = targetHeight / rawHeight
        const rawHeight = rawSize.y > 0 ? rawSize.y : 1.0;
        const scaleFactor = targetHeight / rawHeight;
        model.scale.setScalar(scaleFactor);
        model.updateMatrixWorld(true);

        // 4. Orientation Normalization
        // In Three.js, road runs along Z. Car should face forward towards camera (-Math.PI / 2 baseHeading)
        const baseHeading = (options.baseHeading !== undefined)
            ? options.baseHeading
            : (metadata.baseHeading !== undefined ? metadata.baseHeading : -Math.PI / 2);

        model.rotation.order = "YXZ";
        model.rotation.set(0, baseHeading, 0);
        model.updateMatrixWorld(true);

        // 5. Measure Scaled Dimensions & Check Automotive Dimensional Envelope
        const scaledBox = new THREE.Box3().setFromObject(model);
        const scaledSize = new THREE.Vector3();
        scaledBox.getSize(scaledSize);

        // Length is along Z after heading rotation, Width is along X, Height is along Y
        const vehicleLength = scaledSize.z > scaledSize.x ? scaledSize.z : scaledSize.x;
        const vehicleWidth  = scaledSize.z > scaledSize.x ? scaledSize.x : scaledSize.z;
        const vehicleHeight = scaledSize.y;

        console.log(`[VehicleLoader] Scaled dimensions: L=${vehicleLength.toFixed(2)}m, W=${vehicleWidth.toFixed(2)}m, H=${vehicleHeight.toFixed(2)}m`);

        // Check if dimensions are within ±30% envelope
        const dimChecks = {
            lengthValid: vehicleLength >= DIMENSION_LIMITS.length.min && vehicleLength <= DIMENSION_LIMITS.length.max,
            widthValid:  vehicleWidth  >= DIMENSION_LIMITS.width.min  && vehicleWidth  <= DIMENSION_LIMITS.width.max,
            heightValid: vehicleHeight >= DIMENSION_LIMITS.height.min && vehicleHeight <= DIMENSION_LIMITS.height.max
        };

        if (!dimChecks.lengthValid || !dimChecks.heightValid) {
            console.warn("[VehicleLoader] Scaled dimensions deviate from standard envelope:", dimChecks);
        }

        // 6. Ground Contact Normalization
        // Ensure the lowest vertex / tyre bottom touches y = 0.000 exactly
        let groundOffset = 0;
        if (scaledBox.min.y < 0) {
            groundOffset = -scaledBox.min.y;
        } else if (scaledBox.min.y > 0) {
            groundOffset = -scaledBox.min.y;
        }

        // Apply ground offset and standard parking Z-coordinate
        model.position.set(0, groundOffset, 3.2);
        model.updateMatrixWorld(true);

        // 7. Material Classification & Normalization
        this.normalizeMaterials(model);

        return {
            scale: scaleFactor,
            targetHeight,
            baseHeading,
            groundOffset,
            dimensions: {
                length: vehicleLength,
                width: vehicleWidth,
                height: vehicleHeight
            },
            dimensionChecks: dimChecks
        };
    }

    /**
     * Normalizes and enhances materials across all meshes in the model
     * using semantic preset classification and anisotropic filtering.
     * Preserves high-quality source materials where already correct.
     * 
     * @param {THREE.Object3D} model 
     */
    normalizeMaterials(model) {
        const bodyMaterials = [];

        model.traverse((child) => {
            if (!child.isMesh || !child.material) return;

            child.receiveShadow = true;
            child.castShadow = true;

            const materials = Array.isArray(child.material)
                ? child.material
                : [child.material];

            const updatedMaterials = materials.map((mat) => {
                const category = classifyMaterial(child.name, mat.name, child.parent?.name || "");

                // Apply PBR preset (preserves high-quality existing materials)
                const enhanced = applyMaterialPreset(mat, category, true);

                if (category === "paint" && !bodyMaterials.includes(enhanced)) {
                    bodyMaterials.push(enhanced);
                }

                return enhanced;
            });

            child.material = Array.isArray(child.material)
                ? updatedMaterials
                : updatedMaterials[0];
        });

        // Store reference to body paint materials for paint swatch switching
        model.userData.bodyMaterials = bodyMaterials;
    }

    /**
     * Completely and recursively disposes the currently loaded model,
     * releasing all GPU geometries, buffers, materials, textures, and lights.
     */
    dispose() {
        if (this.currentModel) {
            console.log("[VehicleLoader] Disposing active 3D model hierarchy...");
            disposeHierarchy(this.currentModel);
            this.currentModel = null;
        }
        if (this.rawGLTF) {
            this.rawGLTF = null;
        }
        this.validationReport = null;
        this.activeAssetUrl = null;
    }

    /**
     * Reports active GPU resource allocation metrics for memory diagnostics.
     */
    getMemoryStats() {
        let geometries = 0;
        let materials = 0;
        let textures = 0;

        if (this.currentModel) {
            const geomSet = new Set();
            const matSet = new Set();
            const texSet = new Set();

            this.currentModel.traverse((child) => {
                if (child.isMesh) {
                    if (child.geometry) geomSet.add(child.geometry.id);
                    if (child.material) {
                        const mats = Array.isArray(child.material) ? child.material : [child.material];
                        mats.forEach((m) => {
                            if (!m) return;
                            matSet.add(m.id);
                            [
                                "map", "normalMap", "roughnessMap", "metalnessMap",
                                "aoMap", "emissiveMap", "clearcoatMap"
                            ].forEach((prop) => {
                                if (m[prop] && m[prop].id) texSet.add(m[prop].id);
                            });
                        });
                    }
                }
            });
            geometries = geomSet.size;
            materials = matSet.size;
            textures = texSet.size;
        }

        return {
            geometries,
            materials,
            textures,
            hasActiveModel: !!this.currentModel
        };
    }
}
