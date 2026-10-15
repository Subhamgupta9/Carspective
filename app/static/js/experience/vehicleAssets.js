// ============================================================
// SMARTCAR AI — VEHICLE ASSET REGISTRY
// vehicleAssets.js
// ============================================================

import * as THREE from "three";

/**
 * Canonical Vehicle 3D Asset Registry
 * Maps supported Brand + Model combinations to verified 3D assets and
 * asset-specific calibration metadata.
 */
export const VEHICLE_ASSET_REGISTRY = [
    {
        id: "porsche_911",
        brand: "Porsche",
        // Variations matching dataset representations and canonical designations
        modelMatches: [
            "911",
            "Porsche 911",
            "911 Carrera 4S",
            "911 Carrera",
            "911 Turbo",
            "911 GT3"
        ],
        assetPath: "/static/models/generic_car.glb",
        displayName: "Porsche 911 Carrera 4S",
        category: "Sports Coupe",
        metadata: {
            targetHeight: 1.55,
            baseHeading: -Math.PI / 2, // Forward along +Z in road coordinates
            groundOffset: 0.18915,      // Calibrated lowest tire contact point at y=0
            cameraDistance: 7.2,
            cameraTargetHeight: 0.75,
            cameraTargetZ: 3.2,
            orbitBounds: {
                minRadius: 4.8,
                maxRadius: 11.0,
                minPhi: 0.66,
                maxPhi: 1.45
            },
            shadowDimensions: {
                width: 2.35,
                length: 4.65
            },
            features: {
                hasIndependentWheels: true,
                hasHeadlights: true,
                hasBrakeLights: true
            }
        }
    }
];

/**
 * Normalize brand and model strings for robust registry lookup.
 * Strips duplicate brand prefixes (e.g. "Porsche 911" with brand "Porsche" -> "911").
 */
export function normalizeVehicleLookup(brand, model) {
    const b = (brand || "").trim().toLowerCase();
    let m = (model || "").trim().toLowerCase();

    if (b && m.startsWith(b + " ")) {
        m = m.slice(b.length).trim();
    }

    return { brandNorm: b, modelNorm: m };
}

/**
 * Match a brand and model to a registered 3D asset entry.
 * Returns the matching registry entry, or null if no 3D asset exists.
 *
 * @param {string} brand - Vehicle brand (e.g. "Porsche", "BMW")
 * @param {string} model - Vehicle model (e.g. "911", "3 Series")
 * @returns {object|null} Matching asset registry entry, or null
 */
export function findVehicleAsset(brand, model) {
    if (!brand || !model) {
        return null;
    }

    const { brandNorm, modelNorm } = normalizeVehicleLookup(brand, model);

    for (const entry of VEHICLE_ASSET_REGISTRY) {
        if (entry.brand.toLowerCase() !== brandNorm) {
            continue;
        }

        for (const matchStr of entry.modelMatches) {
            const cleanMatch = matchStr.toLowerCase();

            // Check exact equality, prefix, or substring match
            if (
                cleanMatch === modelNorm ||
                modelNorm.startsWith(cleanMatch) ||
                cleanMatch.startsWith(modelNorm)
            ) {
                return entry;
            }
        }
    }

    return null;
}

/**
 * Get the list of all currently supported 3D vehicles in the registry.
 *
 * @returns {Array<object>} Array of supported vehicle summaries
 */
export function getSupportedVehicles() {
    return VEHICLE_ASSET_REGISTRY.map((entry) => ({
        id: entry.id,
        brand: entry.brand,
        displayName: entry.displayName,
        category: entry.category,
        assetPath: entry.assetPath
    }));
}
