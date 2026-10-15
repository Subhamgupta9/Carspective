// ============================================================
// SMARTCAR AI — CANONICAL VEHICLE IDENTITY & STATE LAYER
// vehicleIdentity.js — Level 2 Vehicle Identity & Architecture
// ============================================================

/**
 * Section 2: Canonical Vehicle Identity Object
 * Authoritative single source of truth for the currently selected vehicle identity.
 * 3D identity contains richer information than the ML prediction model.
 */
export const vehicleIdentity = {
    brand: "",
    model: "",
    manufacturing_year: null,
    variant: "",
    generation: "",
    fuel_type: "",
    transmission_type: "",
    bodytype: "",
    city: "",
    number_of_owners: null,

    // Backward-compatible alias accessors
    get year() {
        return this.manufacturing_year;
    },
    set year(val) {
        this.manufacturing_year = val;
    },
    get fuel() {
        return this.fuel_type;
    },
    set fuel(val) {
        this.fuel_type = val;
    },
    get transmission() {
        return this.transmission_type;
    },
    set transmission(val) {
        this.transmission_type = val;
    },
    get bodyType() {
        return this.bodytype;
    },
    set bodyType(val) {
        this.bodytype = val;
    },
    get owners() {
        return this.number_of_owners;
    },
    set owners(val) {
        this.number_of_owners = val;
    }
};

/**
 * Section 7: Canonical Frontend Vehicle State
 * ONE authoritative source of truth for the full 3D vehicle lifecycle.
 * Vehicle loading consumes this state.
 */
export const vehicleState = {
    identity: vehicleIdentity,
    generation: {},
    asset: {},
    loading: false,
    ready: false
};

// Registered change listeners
const identityListeners = [];
const stateListeners = [];

/**
 * Get a snapshot of canonical vehicle identity.
 * @returns {object} Current vehicle identity snapshot
 */
export function getVehicleIdentity() {
    return {
        brand: vehicleIdentity.brand,
        model: vehicleIdentity.model,
        manufacturing_year: vehicleIdentity.manufacturing_year,
        year: vehicleIdentity.manufacturing_year,
        variant: vehicleIdentity.variant,
        generation: vehicleIdentity.generation,
        fuel_type: vehicleIdentity.fuel_type,
        fuel: vehicleIdentity.fuel_type,
        transmission_type: vehicleIdentity.transmission_type,
        transmission: vehicleIdentity.transmission_type,
        bodytype: vehicleIdentity.bodytype,
        bodyType: vehicleIdentity.bodytype,
        city: vehicleIdentity.city,
        number_of_owners: vehicleIdentity.number_of_owners,
        owners: vehicleIdentity.number_of_owners
    };
}

/**
 * Get direct reference to canonical vehicle identity object.
 * @returns {object} Canonical vehicle identity reference
 */
export function getVehicleIdentityRef() {
    return vehicleIdentity;
}

/**
 * Section 7: Get full canonical vehicle state snapshot.
 * @returns {object} vehicleState snapshot
 */
export function getVehicleState() {
    return {
        identity: getVehicleIdentity(),
        generation: { ...vehicleState.generation },
        asset: { ...vehicleState.asset },
        loading: vehicleState.loading,
        ready: vehicleState.ready
    };
}

/**
 * Section 7: Update one or more fields in canonical vehicle state.
 * @param {object} updates - Partial state updates
 * @returns {object} Updated vehicleState snapshot
 */
export function setVehicleState(updates) {
    if (!updates || typeof updates !== "object") {
        return getVehicleState();
    }

    let hasChanged = false;

    if (updates.identity && typeof updates.identity === "object") {
        setVehicleIdentity(updates.identity);
        hasChanged = true;
    }

    if (updates.generation !== undefined) {
        vehicleState.generation = updates.generation && typeof updates.generation === "object"
            ? { ...updates.generation }
            : {};
        if (vehicleState.generation.slug && vehicleIdentity.generation !== vehicleState.generation.slug) {
            vehicleIdentity.generation = vehicleState.generation.slug;
        }
        hasChanged = true;
    }

    if (updates.asset !== undefined) {
        vehicleState.asset = updates.asset && typeof updates.asset === "object"
            ? { ...updates.asset }
            : {};
        hasChanged = true;
    }

    if (typeof updates.loading === "boolean" && vehicleState.loading !== updates.loading) {
        vehicleState.loading = updates.loading;
        hasChanged = true;
    }

    if (typeof updates.ready === "boolean" && vehicleState.ready !== updates.ready) {
        vehicleState.ready = updates.ready;
        hasChanged = true;
    }

    if (hasChanged) {
        notifyStateChange();
    }

    return getVehicleState();
}

/**
 * Update one or more fields in canonical vehicle identity.
 * Notifies all registered listeners if any value changes.
 * 
 * @param {object} updates - Key-value pairs to update
 * @returns {object} Updated vehicle identity snapshot
 */
export function setVehicleIdentity(updates) {
    if (!updates || typeof updates !== "object") {
        return getVehicleIdentity();
    }

    let hasChanged = false;

    // Normalize field mappings (e.g. year -> manufacturing_year)
    const normalized = {};
    for (const [k, v] of Object.entries(updates)) {
        if (k === "year" || k === "manufacturing_year") {
            normalized.manufacturing_year = v;
        } else if (k === "fuel" || k === "fuel_type") {
            normalized.fuel_type = v;
        } else if (k === "transmission" || k === "transmission_type") {
            normalized.transmission_type = v;
        } else if (k === "bodyType" || k === "bodytype") {
            normalized.bodytype = v;
        } else if (k === "owners" || k === "number_of_owners") {
            normalized.number_of_owners = v;
        } else {
            normalized[k] = v;
        }
    }

    for (const [key, val] of Object.entries(normalized)) {
        if (key in vehicleIdentity) {
            let finalVal = val;
            if (key === "manufacturing_year" && val !== null && val !== undefined && val !== "") {
                const parsedYear = parseInt(val, 10);
                finalVal = isNaN(parsedYear) ? null : parsedYear;
            } else if (key === "number_of_owners" && val !== null && val !== undefined && val !== "") {
                const parsedOwners = parseInt(val, 10);
                finalVal = isNaN(parsedOwners) ? null : parsedOwners;
            } else if (typeof val === "string") {
                finalVal = val.trim();
            }

            if (vehicleIdentity[key] !== finalVal) {
                vehicleIdentity[key] = finalVal;
                hasChanged = true;
            }
        }
    }

    if (hasChanged) {
        notifyIdentityChange();
        notifyStateChange();
    }

    return getVehicleIdentity();
}

/**
 * Reset canonical vehicle identity to default blank state.
 */
export function resetVehicleIdentity() {
    vehicleIdentity.brand = "";
    vehicleIdentity.model = "";
    vehicleIdentity.manufacturing_year = null;
    vehicleIdentity.variant = "";
    vehicleIdentity.generation = "";
    vehicleIdentity.fuel_type = "";
    vehicleIdentity.transmission_type = "";
    vehicleIdentity.bodytype = "";
    vehicleIdentity.city = "";
    vehicleIdentity.number_of_owners = null;

    vehicleState.generation = {};
    vehicleState.asset = {};
    vehicleState.loading = false;
    vehicleState.ready = false;

    notifyIdentityChange();
    notifyStateChange();
}

/**
 * Determines if vehicle identity has sufficient attributes to resolve
 * a 3D model asset. Minimum requirements: Brand + Model + Manufacturing Year.
 * 
 * @returns {boolean} True if Brand, Model, and Year are populated
 */
export function isVehicleIdentityReadyForAsset() {
    const year = vehicleIdentity.manufacturing_year;
    return (
        !!vehicleIdentity.brand &&
        vehicleIdentity.brand.trim().length > 0 &&
        !!vehicleIdentity.model &&
        vehicleIdentity.model.trim().length > 0 &&
        typeof year === "number" &&
        year >= 1990 &&
        year <= 2026
    );
}

/**
 * Register a listener invoked whenever vehicle identity updates.
 * @param {Function} callback - Function receiving (identitySnapshot)
 * @returns {Function} Unsubscribe function
 */
export function onVehicleIdentityChange(callback) {
    if (typeof callback === "function" && !identityListeners.includes(callback)) {
        identityListeners.push(callback);
    }
    return () => {
        const idx = identityListeners.indexOf(callback);
        if (idx !== -1) {
            identityListeners.splice(idx, 1);
        }
    };
}

/**
 * Register a listener invoked whenever vehicle state updates.
 * @param {Function} callback - Function receiving (stateSnapshot)
 * @returns {Function} Unsubscribe function
 */
export function onVehicleStateChange(callback) {
    if (typeof callback === "function" && !stateListeners.includes(callback)) {
        stateListeners.push(callback);
    }
    return () => {
        const idx = stateListeners.indexOf(callback);
        if (idx !== -1) {
            stateListeners.splice(idx, 1);
        }
    };
}

/**
 * Notify all registered listeners with current vehicle identity snapshot.
 */
function notifyIdentityChange() {
    const snapshot = getVehicleIdentity();
    for (const listener of identityListeners) {
        try {
            listener(snapshot);
        } catch (err) {
            console.error("SmartCar AI: vehicleIdentity listener error:", err);
        }
    }
}

/**
 * Notify all registered listeners with current vehicle state snapshot.
 */
function notifyStateChange() {
    const snapshot = getVehicleState();
    for (const listener of stateListeners) {
        try {
            listener(snapshot);
        } catch (err) {
            console.error("SmartCar AI: vehicleState listener error:", err);
        }
    }
}

/**
 * Formatted title for current vehicle (e.g. "2021 BMW 3 Series").
 * @returns {string} Formatted label
 */
export function getVehicleIdentityTitle() {
    const parts = [];
    if (vehicleIdentity.manufacturing_year) parts.push(vehicleIdentity.manufacturing_year);
    if (vehicleIdentity.brand) parts.push(vehicleIdentity.brand);
    
    // Avoid repeating brand in model title
    if (vehicleIdentity.model) {
        let m = vehicleIdentity.model;
        if (vehicleIdentity.brand && m.toLowerCase().startsWith(vehicleIdentity.brand.toLowerCase() + " ")) {
            m = m.slice(vehicleIdentity.brand.length).trim();
        }
        parts.push(m);
    }

    if (vehicleIdentity.variant) {
        parts.push(vehicleIdentity.variant);
    }

    return parts.join(" ") || "UNSPECIFIED VEHICLE";
}
