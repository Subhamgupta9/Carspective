// ============================================================
// SMARTCAR AI — ORBITAL NIGHT ENVIRONMENT MODULE
// environment.js
// ============================================================

import * as THREE from "three";

export class SmartCarEnvironment {

    constructor(parentGroup, camera = null) {
        if (!parentGroup) {
            throw new Error("SmartCarEnvironment: parentGroup is required.");
        }

        this.parentGroup = parentGroup;
        this.camera = camera;

        // Dedicated root group for all orbital environmental elements
        this.environmentGroup = new THREE.Group();
        this.environmentGroup.name = "smartCarOrbitalEnvironment";
        this.parentGroup.add(this.environmentGroup);

        // Subgroups for clean organization
        this.starsGroup = new THREE.Group();
        this.starsGroup.name = "orbitalStars";

        this.celestialGroup = new THREE.Group();
        this.celestialGroup.name = "orbitalCelestial";

        this.skylineGroup = new THREE.Group();
        this.skylineGroup.name = "orbitalSkyline";

        this.environmentGroup.add(this.starsGroup);
        this.environmentGroup.add(this.celestialGroup);
        this.environmentGroup.add(this.skylineGroup);

        // Track disposable resources
        this.disposables = [];

        // Detect mobile viewport for density optimization
        const isMobile = typeof window !== "undefined" && window.innerWidth < 768;

        // Build environment layers
        this.createStarField(isMobile);
        this.createCelestialBodies();
        this.createDistantSkyline(isMobile);
    }

    // ========================================================
    // 1. SUBTLE BACKGROUND STAR FIELD
    // ========================================================

    createStarField(isMobile = false) {
        const starCount = isMobile ? 750 : 1500;
        const positions = new Float32Array(starCount * 3);
        const colors = new Float32Array(starCount * 3);

        const tempColor = new THREE.Color();

        // Palette: mostly soft crisp white with subtle cool/icy tints
        const starTints = [
            0xf0f4fc, // Crisp cool white
            0xe8eef8, // Soft silver white
            0xd2e0f4, // Very faint icy blue
            0xbfd3ee  // Subtle cool blue
        ];

        let index = 0;
        for (let i = 0; i < starCount; i++) {
            // Distribute stars on an upper celestial dome
            // Radius 135m - 165m (distant background, within cameraFar: 200)
            const radius = 135 + Math.random() * 30;

            // Azimuthal angle: full 360° around the scene
            const theta = Math.random() * Math.PI * 2;

            // Elevation angle: mostly upper hemisphere (from 6° above horizon to zenith)
            // phi = 0 is directly above (zenith), phi = PI/2 is horizon
            const phi = Math.acos(Math.random() * 0.90 + 0.08);

            const x = radius * Math.sin(phi) * Math.cos(theta);
            const y = radius * Math.cos(phi); // Always positive (upper sky)
            const z = radius * Math.sin(phi) * Math.sin(theta);

            positions[index * 3]     = x;
            positions[index * 3 + 1] = y;
            positions[index * 3 + 2] = z;

            // Subtle color and brightness variation
            const tintHex = starTints[Math.floor(Math.random() * starTints.length)];
            tempColor.setHex(tintHex);

            // Slight brightness modulation (0.65 to 1.0) so stars have natural depth
            const brightness = 0.65 + Math.random() * 0.35;
            colors[index * 3]     = tempColor.r * brightness;
            colors[index * 3 + 1] = tempColor.g * brightness;
            colors[index * 3 + 2] = tempColor.b * brightness;

            index++;
        }

        const starGeometry = new THREE.BufferGeometry();
        starGeometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
        starGeometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));

        const starMaterial = new THREE.PointsMaterial({
            size: isMobile ? 1.0 : 1.25,
            sizeAttenuation: false, // Clean sub-pixel rendering across distances
            vertexColors: true,
            transparent: true,
            opacity: 0.85,
            fog: false,             // Stars stay crisp and do not wash out in ground fog
            depthWrite: false
        });

        this.starPoints = new THREE.Points(starGeometry, starMaterial);
        this.starPoints.name = "starFieldPoints";
        this.starsGroup.add(this.starPoints);

        this.disposables.push(starGeometry, starMaterial);
    }

    // ========================================================
    // 2. DISTANT CELESTIAL BODIES (PLANET & COMPANION MOON)
    // ========================================================

    createCelestialBodies() {
        // --- PRIMARY CELESTIAL BODY: Distant Dark Blue/Charcoal Planet ---
        // Positioned in distant background (dist > 120m, z < -100m) beautifully framing vehicle
        const planetRadius = 9.2;
        const planetGeo = new THREE.SphereGeometry(planetRadius, 48, 36);

        const planetMat = new THREE.MeshStandardMaterial({
            color: 0x0a121e,       // Deep obsidian navy
            roughness: 0.90,
            metalness: 0.15,
            fog: false,
            depthWrite: true
        });

        const planetMesh = new THREE.Mesh(planetGeo, planetMat);
        // Distant background: x=-65, y=17, z=-105 (dist ≈ 125m)
        planetMesh.position.set(-65, 17, -105);
        planetMesh.name = "primaryPlanetBody";
        this.celestialGroup.add(planetMesh);

        // Delicate atmospheric limb/rim glow for the primary planet
        const atmosphericRimGeo = new THREE.SphereGeometry(planetRadius * 1.035, 36, 24);
        const atmosphericRimMat = new THREE.ShaderMaterial({
            vertexShader: `
                varying vec3 vNormal;
                varying vec3 vViewPosition;
                void main() {
                    vNormal = normalize(normalMatrix * normal);
                    vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
                    vViewPosition = -mvPosition.xyz;
                    gl_Position = projectionMatrix * mvPosition;
                }
            `,
            fragmentShader: `
                varying vec3 vNormal;
                varying vec3 vViewPosition;
                void main() {
                    vec3 normal = normalize(vNormal);
                    vec3 viewDir = normalize(vViewPosition);

                    // Delicate atmospheric Fresnel rim
                    float rim = 1.0 - max(dot(viewDir, normal), 0.0);
                    rim = pow(rim, 3.6);

                    // Atmospheric limb color: subtle cool cyan-slate
                    vec3 atmosphereColor = vec3(0.42, 0.58, 0.82);
                    gl_FragColor = vec4(atmosphereColor, rim * 0.45);
                }
            `,
            blending: THREE.AdditiveBlending,
            transparent: true,
            depthWrite: false,
            fog: false
        });

        const atmosphericRimMesh = new THREE.Mesh(atmosphericRimGeo, atmosphericRimMat);
        atmosphericRimMesh.position.copy(planetMesh.position);
        atmosphericRimMesh.name = "primaryPlanetAtmosphere";
        this.celestialGroup.add(atmosphericRimMesh);

        this.disposables.push(
            planetGeo, planetMat,
            atmosphericRimGeo, atmosphericRimMat
        );

        // --- SECONDARY CELESTIAL BODY: Small, Faint Companion Moon ---
        // Subtle balance in the distant background sky
        const moonRadius = 2.2;
        const moonGeo = new THREE.SphereGeometry(moonRadius, 24, 18);
        const moonMat = new THREE.MeshStandardMaterial({
            color: 0x141b26,       // Deep muted slate
            roughness: 0.95,
            metalness: 0.1,
            transparent: true,
            opacity: 0.60,
            fog: false,
            depthWrite: false
        });

        const moonMesh = new THREE.Mesh(moonGeo, moonMat);
        moonMesh.position.set(-92, 20, -102);
        moonMesh.name = "companionMoon";
        this.celestialGroup.add(moonMesh);

        this.disposables.push(moonGeo, moonMat);
    }

    // ========================================================
    // 3. MINIMAL FUTURISTIC SILHOUETTE SKYLINE
    // ========================================================

    createDistantSkyline(isMobile = false) {
        // High-performance InstancedMesh for skyline silhouettes
        const buildingCount = isMobile ? 36 : 64;

        // Base 1x1x1 unit box for instancing
        const boxGeo = new THREE.BoxGeometry(1, 1, 1);

        // Dark charcoal / near-black silhouette material
        // fog: true allows buildings to naturally fade into horizon atmospheric depth
        const buildingMat = new THREE.MeshStandardMaterial({
            color: 0x07090c,       // Deep obsidian charcoal
            roughness: 0.96,
            metalness: 0.12,
            fog: true
        });

        const instancedBuildings = new THREE.InstancedMesh(boxGeo, buildingMat, buildingCount);
        instancedBuildings.name = "skylineInstancedMesh";
        instancedBuildings.castShadow = false;
        instancedBuildings.receiveShadow = false;

        const dummy = new THREE.Object3D();

        // Deterministic pseudo-random seed generator for stable layout
        let seed = 42;
        const pseudoRandom = () => {
            seed = (seed * 9301 + 49297) % 233280;
            return seed / 233280;
        };

        // Distribute buildings across the distant horizon:
        // x spans -85m to +85m, z spans -55m to -82m (well behind the vehicle at z=3.2)
        const xSpan = 170;
        const xStep = xSpan / buildingCount;

        for (let i = 0; i < buildingCount; i++) {
            // Position along horizon with slight grouping/jitter
            const posX = -85 + i * xStep + (pseudoRandom() - 0.5) * (xStep * 0.7);
            const posZ = -55 - pseudoRandom() * 26; // Between -55 and -81

            // Proportions: varied heights (7m to 26m) and widths (2.8m to 7.5m)
            // Downtown cluster effect: center buildings slightly taller
            const centerDist = Math.abs(posX) / 85;
            const heightBias = 1.0 - Math.pow(centerDist, 1.4) * 0.5;

            const width  = 2.8 + pseudoRandom() * 4.6;
            const depth  = 3.2 + pseudoRandom() * 5.0;
            const height = (7.5 + pseudoRandom() * 18.0) * heightBias;

            // Ground base at y = 0
            const posY = height / 2 - 0.2;

            dummy.position.set(posX, posY, posZ);
            dummy.scale.set(width, height, depth);
            dummy.rotation.set(0, (pseudoRandom() - 0.5) * 0.15, 0);
            dummy.updateMatrix();

            instancedBuildings.setMatrixAt(i, dummy.matrix);
        }

        instancedBuildings.instanceMatrix.needsUpdate = true;
        this.skylineGroup.add(instancedBuildings);

        // --- SUBTLE WINDOW ACCENTS: Very sparse, dim micro-strips ---
        // Sparse micro-accent slivers on only ~35% of buildings
        const accentCount = Math.floor(buildingCount * 0.35);
        const accentGeo = new THREE.BoxGeometry(1, 1, 1);
        const accentMat = new THREE.MeshBasicMaterial({
            color: 0x4a6585,       // Dim cool slate-blue (NOT bright neon)
            transparent: true,
            opacity: 0.35,
            fog: true
        });

        const instancedAccents = new THREE.InstancedMesh(accentGeo, accentMat, accentCount);
        instancedAccents.name = "skylineWindowAccents";
        instancedAccents.castShadow = false;
        instancedAccents.receiveShadow = false;

        let accentIdx = 0;
        seed = 137; // New seed for accent distribution

        for (let i = 0; i < buildingCount && accentIdx < accentCount; i++) {
            if (pseudoRandom() > 0.45) {
                // Read corresponding building transform
                instancedBuildings.getMatrixAt(i, dummy.matrix);
                dummy.matrix.decompose(dummy.position, dummy.quaternion, dummy.scale);

                // Place a thin horizontal micro-strip near upper third of tower
                const stripY = dummy.position.y + dummy.scale.y * (0.15 + pseudoRandom() * 0.25);
                const stripW = dummy.scale.x * (0.45 + pseudoRandom() * 0.35);
                const stripH = 0.22 + pseudoRandom() * 0.25;
                const stripD = dummy.scale.z + 0.15; // Slightly protruding

                const accentDummy = new THREE.Object3D();
                accentDummy.position.set(dummy.position.x, stripY, dummy.position.z);
                accentDummy.scale.set(stripW, stripH, stripD);
                accentDummy.rotation.copy(dummy.rotation);
                accentDummy.updateMatrix();

                instancedAccents.setMatrixAt(accentIdx, accentDummy.matrix);
                accentIdx++;
            }
        }

        instancedAccents.instanceMatrix.needsUpdate = true;
        this.skylineGroup.add(instancedAccents);

        this.disposables.push(boxGeo, buildingMat, accentGeo, accentMat);
    }

    // ========================================================
    // UPDATE & SUBTLE PARALLAX
    // ========================================================

    update(delta) {
        // Extremely subtle, imperceptible celestial drift (0.00015 rad/s)
        // Adds faint cinematic life without drawing the eye away from the vehicle
        if (this.starPoints) {
            this.starPoints.rotation.y += delta * 0.00015;
        }

        // Extremely slow planetary orbit drift
        if (this.celestialGroup) {
            this.celestialGroup.rotation.y += delta * 0.00008;
        }
    }

    // ========================================================
    // CLEANUP
    // ========================================================

    dispose() {
        if (this.environmentGroup && this.environmentGroup.parent) {
            this.environmentGroup.parent.remove(this.environmentGroup);
        }

        this.disposables.forEach((resource) => {
            if (resource && typeof resource.dispose === "function") {
                resource.dispose();
            }
        });

        this.disposables = [];
    }
}
