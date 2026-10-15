// ============================================================
// SMARTCAR AI — MATERIAL PRESETS & CLASSIFICATION MODULE
// materialPresets.js — Phase 3 PBR Automotive Presets
// ============================================================

import * as THREE from "three";

/**
 * Standardized Automotive PBR Material Presets
 * Designed for high-fidelity physical realism under showroom lighting.
 */
export const MATERIAL_PRESETS = {
    paint: {
        name: "Automotive Clearcoat Paint",
        type: "MeshPhysicalMaterial",
        clearcoat: 1.0,
        clearcoatRoughness: 0.04,
        metalness: 0.82,
        roughness: 0.16,
        envMapIntensity: 1.8,
        reflectivity: 0.9
    },
    glass: {
        name: "Automotive Tinted Glass",
        type: "MeshPhysicalMaterial",
        transparent: true,
        opacity: 0.38,
        roughness: 0.02,
        metalness: 0.10,
        transmission: 0.90,
        ior: 1.52,
        depthWrite: true,
        envMapIntensity: 2.0
    },
    chrome: {
        name: "Polished Chrome & Alloy",
        type: "MeshStandardMaterial",
        metalness: 0.95,
        roughness: 0.08,
        envMapIntensity: 2.2
    },
    rubber: {
        name: "Vulcanized Tire Rubber",
        type: "MeshStandardMaterial",
        metalness: 0.0,
        roughness: 0.85,
        envMapIntensity: 0.4
    },
    leather: {
        name: "Perforated Interior Leather",
        type: "MeshStandardMaterial",
        metalness: 0.02,
        roughness: 0.70,
        envMapIntensity: 0.6
    },
    plastic: {
        name: "Textured Exterior Plastic",
        type: "MeshStandardMaterial",
        metalness: 0.08,
        roughness: 0.50,
        envMapIntensity: 0.8
    }
};

/**
 * Classifies a mesh/material into a semantic automotive material category
 * using mesh name, parent name, and material name heuristics.
 * 
 * @param {string} meshName 
 * @param {string} materialName 
 * @param {string} parentName 
 * @returns {string} One of 'paint', 'glass', 'chrome', 'rubber', 'leather', 'plastic', or 'default'
 */
export function classifyMaterial(meshName = "", materialName = "", parentName = "") {
    const combined = `${meshName} ${materialName} ${parentName}`.toLowerCase();

    // 1. Glass / Windows / Lights
    if (
        combined.includes("window") ||
        combined.includes("glass") ||
        combined.includes("windshield") ||
        combined.includes("windscreen") ||
        combined.includes("sunroof")
    ) {
        return "glass";
    }

    // 2. Rubber / Tires
    if (
        combined.includes("tire") ||
        combined.includes("tyre") ||
        combined.includes("rubber") ||
        combined.includes("wheel_tire") ||
        combined.includes("wheel_tyre")
    ) {
        return "rubber";
    }

    // 3. Chrome / Alloys / Mirrors / Exhaust
    if (
        combined.includes("chrome") ||
        combined.includes("rim") ||
        combined.includes("alloy") ||
        combined.includes("mirror_cover") ||
        combined.includes("exhaust") ||
        combined.includes("caliper") ||
        combined.includes("disc") ||
        combined.includes("metal_parts")
    ) {
        return "chrome";
    }

    // 4. Leather / Seats / Interior
    if (
        combined.includes("leather") ||
        combined.includes("seat") ||
        combined.includes("upholstery") ||
        combined.includes("steering") ||
        combined.includes("interior") ||
        combined.includes("carpet") ||
        combined.includes("dashboard")
    ) {
        return "leather";
    }

    // 5. Plastic / Trim / Grille
    if (
        combined.includes("plastic") ||
        combined.includes("trim") ||
        combined.includes("grille") ||
        combined.includes("grid") ||
        combined.includes("diffuser") ||
        combined.includes("service_black")
    ) {
        return "plastic";
    }

    // 6. Paint / Body Exterior
    if (
        combined.includes("body") ||
        combined.includes("paint") ||
        combined.includes("hood") ||
        combined.includes("bonnet") ||
        combined.includes("fender") ||
        combined.includes("door") ||
        combined.includes("trunk") ||
        combined.includes("boot") ||
        combined.includes("car_body") ||
        combined.includes("geometry_0") // Monolithic single-mesh CarImages model default
    ) {
        return "paint";
    }

    return "default";
}

/**
 * Checks whether an existing material is already high quality and physically valid.
 * High-quality materials (e.g. from the flagship Studio HD generic_car.glb) should
 * NOT be blindly overwritten.
 * 
 * @param {THREE.Material} material 
 * @returns {boolean}
 */
export function isMaterialHighQuality(material) {
    if (!material) return false;

    // Studio HD explicit marker
    if (material.userData && material.userData.isStudioHD) {
        return true;
    }

    // Already configured with full physical clearcoat PBR
    if (
        material.isMeshPhysicalMaterial &&
        material.clearcoat > 0.5 &&
        material.roughness < 0.3
    ) {
        return true;
    }

    // Multi-map PBR material with normal & roughness/metalness maps
    if (material.normalMap && (material.roughnessMap || material.metalnessMap)) {
        return true;
    }

    return false;
}

/**
 * Applies a PBR preset to a material, preserving existing textures and colors
 * unless explicitly instructed to overwrite.
 * 
 * @param {THREE.Material} material - Material to enhance
 * @param {string} category - Category preset name ('paint', 'glass', etc.)
 * @param {boolean} preserveExistingQuality - If true, skips materials that are already high-fidelity
 * @returns {THREE.Material} The configured material (or a converted physical material)
 */
export function applyMaterialPreset(material, category, preserveExistingQuality = true) {
    if (!material) return null;

    if (preserveExistingQuality && isMaterialHighQuality(material)) {
        // Only ensure anisotropic filtering on textures
        ensureTextureQuality(material);
        return material;
    }

    const preset = MATERIAL_PRESETS[category] || MATERIAL_PRESETS.paint;

    // Convert MeshStandardMaterial to MeshPhysicalMaterial if clearcoat is needed
    let targetMat = material;
    if (preset.type === "MeshPhysicalMaterial" && !material.isMeshPhysicalMaterial) {
        // Upgrade to MeshPhysicalMaterial preserving parameters
        targetMat = new THREE.MeshPhysicalMaterial({
            color: material.color ? material.color.clone() : new THREE.Color(0xffffff),
            map: material.map || null,
            normalMap: material.normalMap || null,
            roughnessMap: material.roughnessMap || null,
            metalnessMap: material.metalnessMap || null,
            aoMap: material.aoMap || null,
            emissive: material.emissive ? material.emissive.clone() : new THREE.Color(0x000000),
            emissiveMap: material.emissiveMap || null,
            name: material.name || `converted_${category}`
        });
    }

    // Apply preset properties
    if (preset.clearcoat !== undefined && targetMat.clearcoat !== undefined) {
        targetMat.clearcoat = preset.clearcoat;
    }
    if (preset.clearcoatRoughness !== undefined && targetMat.clearcoatRoughness !== undefined) {
        targetMat.clearcoatRoughness = preset.clearcoatRoughness;
    }
    if (preset.metalness !== undefined) {
        targetMat.metalness = preset.metalness;
    }
    if (preset.roughness !== undefined) {
        targetMat.roughness = preset.roughness;
    }
    if (preset.envMapIntensity !== undefined) {
        targetMat.envMapIntensity = preset.envMapIntensity;
    }
    if (preset.transparent !== undefined) {
        targetMat.transparent = preset.transparent;
        targetMat.opacity = preset.opacity !== undefined ? preset.opacity : targetMat.opacity;
    }
    if (preset.transmission !== undefined && targetMat.transmission !== undefined) {
        targetMat.transmission = preset.transmission;
    }
    if (preset.ior !== undefined && targetMat.ior !== undefined) {
        targetMat.ior = preset.ior;
    }
    if (preset.depthWrite !== undefined) {
        targetMat.depthWrite = preset.depthWrite;
    }

    ensureTextureQuality(targetMat);
    targetMat.needsUpdate = true;

    return targetMat;
}

/**
 * Ensures optimal anisotropic filtering and mipmapping on all textures of a material.
 * Desktop: up to 16x anisotropic filtering.
 * Mobile: clamped to 4x for high-throughput GPU memory bandwidth preservation.
 * @param {THREE.Material} material 
 * @param {boolean} [forceMobile]
 */
export function ensureTextureQuality(material, forceMobile = null) {
    if (!material) return;

    const isMobile = forceMobile !== null ? forceMobile : (
        (typeof window !== "undefined") && (
            window.innerWidth < 768 ||
            /Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent || "")
        )
    );

    const maxAnisotropy = isMobile ? 4 : 16;

    const maps = [
        material.map, material.normalMap, material.roughnessMap,
        material.metalnessMap, material.aoMap, material.emissiveMap,
        material.clearcoatMap, material.clearcoatNormalMap, material.clearcoatRoughnessMap
    ];

    maps.forEach((m) => {
        if (m && typeof m === "object") {
            m.anisotropy = maxAnisotropy;
            m.generateMipmaps = true;
            m.minFilter = THREE.LinearMipmapLinearFilter;
            m.magFilter = THREE.LinearFilter;
            m.needsUpdate = true;
        }
    });
}

/**
 * Cleanly disposes all texture maps attached to a material to release WebGL GPU memory.
 * @param {THREE.Material} material
 */
export function disposeTextures(material) {
    if (!material) return;
    const textureProps = [
        "map", "alphaMap", "aoMap", "bumpMap", "displacementMap",
        "emissiveMap", "envMap", "lightMap", "metalnessMap",
        "normalMap", "roughnessMap", "clearcoatMap",
        "clearcoatNormalMap", "clearcoatRoughnessMap",
        "sheenColorMap", "sheenRoughnessMap", "specularColorMap",
        "specularIntensityMap", "transmissionMap", "thicknessMap"
    ];
    textureProps.forEach((prop) => {
        const tex = material[prop];
        if (tex && typeof tex.dispose === "function") {
            tex.dispose();
        }
    });
}

