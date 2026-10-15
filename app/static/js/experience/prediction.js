// ============================================================
// SMARTCAR AI — REAL MACHINE LEARNING PREDICTION SERVICE
// prediction.js
// ============================================================

export class SmartCarPrediction {

    constructor() {
        this.isPredicting = false;
        this.lastPrediction = null;
        this.apiEndpoint = "/api/predict";
    }

    /**
     * Validate that the configuration contains all 9 required parameters.
     */
    validateConfig(config) {
        if (!config || typeof config !== "object") {
            throw new Error("Invalid configuration object.");
        }

        const required = [
            { key: "brand", label: "Brand" },
            { key: "model", label: "Model" },
            { key: "manufacturing_year", label: "Manufacturing Year" },
            { key: "km_driven", label: "Kilometers Driven" },
            { key: "fuel_type", label: "Fuel Type" },
            { key: "transmission_type", label: "Transmission" },
            { key: "city", label: "City" },
            { key: "bodytype", label: "Body Type" },
            { key: "number_of_owners", label: "Number of Owners" }
        ];

        for (const item of required) {
            const val = config[item.key];
            if (val === undefined || val === null || val === "") {
                throw new Error(`Missing required specification: ${item.label}`);
            }
        }

        const year = Number(config.manufacturing_year);
        if (!Number.isInteger(year) || year < 1990 || year > 2026) {
            throw new Error("Manufacturing year must be between 1990 and 2026.");
        }

        const km = Number(config.km_driven);
        if (isNaN(km) || km < 0) {
            throw new Error("Kilometers driven cannot be negative.");
        }

        const owners = Number(config.number_of_owners);
        if (!Number.isInteger(owners) || owners < 1) {
            throw new Error("Number of owners must be at least 1.");
        }

        return true;
    }

    /**
     * Send real prediction request to Flask /api/predict.
     * @param {Object} config - The 9-field vehicle configuration
     * @returns {Promise<Object>} The ML prediction result payload
     */
    async predict(config) {
        if (this.isPredicting) {
            throw new Error("Valuation already in progress. Please wait.");
        }

        this.validateConfig(config);

        this.isPredicting = true;

        try {
            console.log("SmartCar Prediction: Dispatching real ML inference request to /api/predict...", config);

            const payload = {
                brand: config.brand.trim(),
                model: config.model.trim(),
                manufacturing_year: Number(config.manufacturing_year),
                km_driven: Number(config.km_driven),
                fuel_type: config.fuel_type.trim(),
                transmission_type: config.transmission_type.trim(),
                city: config.city.trim(),
                bodytype: config.bodytype.trim(),
                number_of_owners: Number(config.number_of_owners)
            };

            const response = await fetch(this.apiEndpoint, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                body: JSON.stringify(payload)
            });

            let data;
            try {
                data = await response.json();
            } catch (jsonErr) {
                throw new Error("Invalid response format received from valuation server.");
            }

            if (!response.ok || !data.success) {
                const message = data.error || `Server responded with status ${response.status}`;
                throw new Error(message);
            }

            this.lastPrediction = data;
            console.log("SmartCar Prediction: Real ML Valuation successfully received:", data);
            return data;

        } catch (error) {
            console.error("SmartCar Prediction Error:", error);
            throw error;
        } finally {
            this.isPredicting = false;
        }
    }

    getLastPrediction() {
        return this.lastPrediction;
    }

    getIsPredicting() {
        return this.isPredicting;
    }
}
