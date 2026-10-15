// ============================================================
// SMARTCAR AI — IMMERSIVE 3D SCENE
// scene.js
// ============================================================

import * as THREE from "three";
import { SmartCarEnvironment } from "./environment.js";


// ============================================================
// SCENE CONFIGURATION
// ============================================================

const SCENE_CONFIG = {

    background: 0x050607,

    fogColor: 0x050607,

    fogNear: 18,

    fogFar: 90,

    cameraFov: 42,

    cameraNear: 0.1,

    cameraFar: 200,

    exposure: 1.15

};


// ============================================================
// SMARTCAR SCENE CLASS
// ============================================================

export class SmartCarScene {

    constructor(canvas) {

        if (!canvas) {

            throw new Error(
                "SmartCarScene: Canvas element not found."
            );

        }


        this.canvas = canvas;


        // ----------------------------------------------------
        // THREE.JS SCENE
        // ----------------------------------------------------

        this.scene = new THREE.Scene();

        this.scene.background =
            new THREE.Color(
                SCENE_CONFIG.background
            );


        this.scene.fog =
            new THREE.Fog(
                SCENE_CONFIG.fogColor,
                SCENE_CONFIG.fogNear,
                SCENE_CONFIG.fogFar
            );


        // ----------------------------------------------------
        // CAMERA
        // ----------------------------------------------------

        this.camera =
            new THREE.PerspectiveCamera(
                SCENE_CONFIG.cameraFov,
                1,
                SCENE_CONFIG.cameraNear,
                SCENE_CONFIG.cameraFar
            );


        this.camera.position.set(
            7,
            3.2,
            8
        );


        this.camera.lookAt(
            0,
            1,
            0
        );


        // ----------------------------------------------------
        // RENDERER
        // ----------------------------------------------------

        this.renderer =
            new THREE.WebGLRenderer({

                canvas: this.canvas,

                antialias: true,

                alpha: false,

                powerPreference: "high-performance"

            });


        this.renderer.setPixelRatio(
            this.getSafePixelRatio()
        );


        this.renderer.setSize(
            this.canvas.clientWidth ||
            window.innerWidth,

            this.canvas.clientHeight ||
            window.innerHeight,

            false
        );


        this.renderer.outputColorSpace =
            THREE.SRGBColorSpace;


        this.renderer.toneMapping =
            THREE.ACESFilmicToneMapping;


        this.renderer.toneMappingExposure =
            SCENE_CONFIG.exposure;


        this.renderer.shadowMap.enabled =
            true;


        this.renderer.shadowMap.type =
            THREE.PCFSoftShadowMap;


        // ----------------------------------------------------
        // WORLD GROUP
        // ----------------------------------------------------

        this.world =
            new THREE.Group();


        this.scene.add(
            this.world
        );


        // ----------------------------------------------------
        // OBJECT GROUPS
        // ----------------------------------------------------

        this.environment =
            new THREE.Group();


        this.road =
            new THREE.Group();


        this.lights =
            new THREE.Group();


        this.world.add(
            this.environment
        );


        this.world.add(
            this.road
        );


        this.world.add(
            this.lights
        );


        // ----------------------------------------------------
        // BUILD ENVIRONMENT & STUDIO LIGHTING
        // ----------------------------------------------------

        this.createLighting();

        this.createHDREnvironment();

        this.createContactShadow();

        this.createRoad();

        this.createRoadDetails();

        this.createEnvironment();

        this.createAtmosphere();


        // ----------------------------------------------------
        // RESIZE
        // ----------------------------------------------------

        this.handleResize =
            this.handleResize.bind(this);


        window.addEventListener(
            "resize",
            this.handleResize
        );


        this.handleResize();


        // ----------------------------------------------------
        // CLOCK
        // ----------------------------------------------------

        this.clock =
            new THREE.Clock();


        this.elapsedTime = 0;


        // ----------------------------------------------------
        // START RENDER LOOP
        // ----------------------------------------------------

        this.isRunning = true;

        this.animate();

    }



    // ========================================================
    // LIGHTING
    // ========================================================

    createLighting() {

        // ----------------------------------------------------
        // LIGHTING PROFILES: ARRIVAL, INSPECTION, VALUATION
        // ----------------------------------------------------

        this.lightingProfiles = {
            ARRIVAL: {
                name: "ARRIVAL",
                ambientColor: 0x222d3d,
                groundColor: 0x05070a,
                ambientIntensity: 0.85,
                directionalColor: 0xc4dafc,
                directionalIntensity: 2.2,
                directionalPos: [-14, 18, 9],
                rimColor: 0x4876ff,
                rimIntensity: 2.4,
                rimPos: [11, 7, -15],
                frontColor: 0xe0eaff,
                frontIntensity: 8.0,
                exposure: 1.05,
                fogColor: 0x05070b
            },
            INSPECTION: {
                name: "INSPECTION",
                ambientColor: 0xe8f0f8,
                groundColor: 0x181c24,
                ambientIntensity: 1.45,
                directionalColor: 0xffffff,
                directionalIntensity: 3.4,
                directionalPos: [-8, 16, 6],
                rimColor: 0x9bc0f0,
                rimIntensity: 1.6,
                rimPos: [10, 8, -12],
                frontColor: 0xffffff,
                frontIntensity: 18.0,
                exposure: 1.15,
                fogColor: 0x080a0e
            },
            VALUATION: {
                name: "VALUATION",
                ambientColor: 0xebd9c2,
                groundColor: 0x12100d,
                ambientIntensity: 1.15,
                directionalColor: 0xfff0d8,
                directionalIntensity: 4.0,
                directionalPos: [-10, 14, 8],
                rimColor: 0xffcf94,
                rimIntensity: 2.8,
                rimPos: [13, 7, -13],
                frontColor: 0xffebd2,
                frontIntensity: 24.0,
                exposure: 1.25,
                fogColor: 0x0b0907
            }
        };

        // Aliases for compatibility
        this.lightingProfiles.RESULT = { ...this.lightingProfiles.VALUATION };

        this.currentLightingProfile = "INSPECTION";
        this.targetLighting = { ...this.lightingProfiles.INSPECTION };

        // ----------------------------------------------------
        // WORLD AMBIENT / HEMISPHERE LIGHT
        // ----------------------------------------------------

        const ambient = new THREE.HemisphereLight(
            this.targetLighting.ambientColor,
            this.targetLighting.groundColor,
            this.targetLighting.ambientIntensity
        );

        this.ambientLight = ambient;
        this.lights.add(ambient);

        // ----------------------------------------------------
        // MAIN KEY / SKY LIGHT (SOFTBOX KEY)
        // ----------------------------------------------------

        const directional = new THREE.DirectionalLight(
            this.targetLighting.directionalColor,
            this.targetLighting.directionalIntensity
        );

        const isMobile = (typeof window !== "undefined") && (
            window.innerWidth < 768 ||
            /Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent || "")
        );

        directional.position.set(...this.targetLighting.directionalPos);
        directional.castShadow = true;
        directional.shadow.mapSize.width = isMobile ? 1024 : 2048;
        directional.shadow.mapSize.height = isMobile ? 1024 : 2048;
        directional.shadow.camera.near = 0.5;
        directional.shadow.camera.far = 40;
        directional.shadow.camera.left = -10;
        directional.shadow.camera.right = 10;
        directional.shadow.camera.top = 10;
        directional.shadow.camera.bottom = -10;
        directional.shadow.bias = -0.0002;
        directional.shadow.normalBias = 0.035;

        this.directionalLight = directional;
        this.lights.add(directional);

        // ----------------------------------------------------
        // RIM LIGHT
        // ----------------------------------------------------

        const rim = new THREE.DirectionalLight(
            this.targetLighting.rimColor,
            this.targetLighting.rimIntensity
        );

        rim.position.set(...this.targetLighting.rimPos);
        this.rimLight = rim;
        this.lights.add(rim);

        // ----------------------------------------------------
        // SOFT FRONT / FILL LIGHT
        // ----------------------------------------------------

        const front = new THREE.PointLight(
            this.targetLighting.frontColor,
            this.targetLighting.frontIntensity,
            30
        );

        front.position.set(0, 4, 10);
        this.frontLight = front;
        this.lights.add(front);
    }

    setLightingProfile(profileName, immediate = false) {
        const profile = this.lightingProfiles[profileName];
        if (!profile) return;

        this.currentLightingProfile = profileName;
        this.targetLighting = { ...profile };

        if (immediate) {
            if (this.ambientLight) {
                this.ambientLight.intensity = profile.ambientIntensity;
                this.ambientLight.color.setHex(profile.ambientColor);
                this.ambientLight.groundColor.setHex(profile.groundColor);
            }
            if (this.directionalLight) {
                this.directionalLight.intensity = profile.directionalIntensity;
                this.directionalLight.color.setHex(profile.directionalColor);
                this.directionalLight.position.set(...profile.directionalPos);
            }
            if (this.rimLight) {
                this.rimLight.intensity = profile.rimIntensity;
                this.rimLight.color.setHex(profile.rimColor);
                this.rimLight.position.set(...profile.rimPos);
            }
            if (this.frontLight) {
                this.frontLight.intensity = profile.frontIntensity;
                this.frontLight.color.setHex(profile.frontColor);
            }
            if (this.renderer) {
                this.renderer.toneMappingExposure = profile.exposure;
            }
            if (this.scene.fog) {
                this.scene.fog.color.setHex(profile.fogColor);
            }
            if (this.scene.background) {
                this.scene.background.setHex(profile.fogColor);
            }
        }
    }

    getLightingProfile() {
        return this.currentLightingProfile;
    }

    getLightingProfiles() {
        return Object.keys(this.lightingProfiles);
    }

    createHDREnvironment() {
        try {
            const isMobile = (typeof window !== "undefined") && (
                window.innerWidth < 768 ||
                /Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent || "")
            );

            const pmremGenerator = new THREE.PMREMGenerator(this.renderer);
            pmremGenerator.compileEquirectangularShader();

            const envScene = new THREE.Scene();
            envScene.background = new THREE.Color(0x0a0c10);

            // 1. Overhead large studio softbox
            const overheadGeo = new THREE.PlaneGeometry(16, 22);
            const overheadMat = new THREE.MeshBasicMaterial({ color: 0xffffff, side: THREE.DoubleSide });
            const overheadSoftbox = new THREE.Mesh(overheadGeo, overheadMat);
            overheadSoftbox.rotation.x = Math.PI / 2;
            overheadSoftbox.position.set(0, 10, 0);
            envScene.add(overheadSoftbox);

            // 2. High-key left side reflection strip
            const leftStripGeo = new THREE.PlaneGeometry(3, 28);
            const leftStripMat = new THREE.MeshBasicMaterial({ color: 0xdce8ff, side: THREE.DoubleSide });
            const leftStrip = new THREE.Mesh(leftStripGeo, leftStripMat);
            leftStrip.rotation.y = Math.PI / 2;
            leftStrip.position.set(-12, 4.5, 0);
            envScene.add(leftStrip);

            // 3. Right warm accent strip
            const rightStripGeo = new THREE.PlaneGeometry(2.5, 24);
            const rightStripMat = new THREE.MeshBasicMaterial({ color: 0xffeedd, side: THREE.DoubleSide });
            const rightStrip = new THREE.Mesh(rightStripGeo, rightStripMat);
            rightStrip.rotation.y = -Math.PI / 2;
            rightStrip.position.set(12, 4.0, 0);
            envScene.add(rightStrip);

            // 4. Rear kicker strip
            const rearStripGeo = new THREE.PlaneGeometry(12, 3);
            const rearStripMat = new THREE.MeshBasicMaterial({ color: 0x88b0ff, side: THREE.DoubleSide });
            const rearStrip = new THREE.Mesh(rearStripGeo, rearStripMat);
            rearStrip.position.set(0, 5.5, -16);
            envScene.add(rearStrip);

            // 5. Absorptive ground
            const groundGeo = new THREE.PlaneGeometry(40, 40);
            const groundMat = new THREE.MeshBasicMaterial({ color: 0x050608, side: THREE.DoubleSide });
            const groundMesh = new THREE.Mesh(groundGeo, groundMat);
            groundMesh.rotation.x = -Math.PI / 2;
            groundMesh.position.y = -0.2;
            envScene.add(groundMesh);

            const sigma = isMobile ? 0.08 : 0.04;
            const envMap = pmremGenerator.fromScene(envScene, sigma).texture;
            this.scene.environment = envMap;
            this.envMapTexture = envMap;
            this.pmremGenerator = pmremGenerator;

            overheadGeo.dispose();
            overheadMat.dispose();
            leftStripGeo.dispose();
            leftStripMat.dispose();
            rightStripGeo.dispose();
            rightStripMat.dispose();
            rearStripGeo.dispose();
            rearStripMat.dispose();
            groundGeo.dispose();
            groundMat.dispose();

            console.log("SmartCarScene: Studio HDR environment lighting initialized.");
        } catch (err) {
            console.warn("SmartCarScene: Could not initialize PMREM HDR environment:", err);
        }
    }

    createContactShadow() {
        try {
            const canvas = document.createElement("canvas");
            canvas.width = 512;
            canvas.height = 512;
            const ctx = canvas.getContext("2d");
            ctx.clearRect(0, 0, 512, 512);

            const gradient = ctx.createRadialGradient(256, 256, 40, 256, 256, 220);
            gradient.addColorStop(0.0, "rgba(0, 0, 0, 0.88)");
            gradient.addColorStop(0.35, "rgba(0, 0, 0, 0.68)");
            gradient.addColorStop(0.65, "rgba(0, 0, 0, 0.32)");
            gradient.addColorStop(0.85, "rgba(0, 0, 0, 0.08)");
            gradient.addColorStop(1.0, "rgba(0, 0, 0, 0.0)");

            ctx.fillStyle = gradient;
            ctx.beginPath();
            ctx.ellipse(256, 256, 170, 235, 0, 0, Math.PI * 2);
            ctx.fill();

            const shadowTexture = new THREE.CanvasTexture(canvas);
            shadowTexture.wrapS = THREE.ClampToEdgeWrapping;
            shadowTexture.wrapT = THREE.ClampToEdgeWrapping;

            const shadowGeo = new THREE.PlaneGeometry(3.6, 5.8);
            const shadowMat = new THREE.MeshBasicMaterial({
                map: shadowTexture,
                transparent: true,
                opacity: 0.76,
                depthWrite: false
            });

            const contactShadow = new THREE.Mesh(shadowGeo, shadowMat);
            contactShadow.rotation.x = -Math.PI / 2;
            contactShadow.position.set(0, 0.002, 3.2);
            contactShadow.renderOrder = 2;

            this.contactShadow = contactShadow;
            this.world.add(contactShadow);
        } catch (err) {
            console.warn("SmartCarScene: Could not initialize contact shadow:", err);
        }
    }

    updateContactShadow(centerZ = 3.2, length = 4.8, width = 2.1) {
        if (!this.contactShadow) return;
        this.contactShadow.position.z = centerZ;
        this.contactShadow.scale.set(width / 2.0, length / 4.8, 1);
    }



    // ========================================================
    // ROAD
    // ========================================================

    createRoad() {

        const roadWidth =
            10;

        const roadLength =
            180;


        // ----------------------------------------------------
        // ROAD BASE
        // ----------------------------------------------------

        const roadGeometry =
            new THREE.PlaneGeometry(
                roadWidth,
                roadLength
            );


        const roadMaterial =
            new THREE.MeshStandardMaterial({

                color: 0x151719,

                roughness: 0.92,

                metalness: 0.05

            });


        const roadMesh =
            new THREE.Mesh(
                roadGeometry,
                roadMaterial
            );


        roadMesh.rotation.x =
            -Math.PI / 2;


        roadMesh.position.y =
            0;


        roadMesh.receiveShadow =
            true;


        this.road.add(
            roadMesh
        );


        // ----------------------------------------------------
        // ROAD SHOULDERS
        // ----------------------------------------------------

        const shoulderMaterial =
            new THREE.MeshStandardMaterial({

                color: 0x24282a,

                roughness: 1

            });


        const shoulderGeometry =
            new THREE.PlaneGeometry(
                2.5,
                roadLength
            );


        const leftShoulder =
            new THREE.Mesh(
                shoulderGeometry,
                shoulderMaterial
            );


        leftShoulder.rotation.x =
            -Math.PI / 2;


        leftShoulder.position.set(
            -6.25,
            -0.01,
            0
        );


        leftShoulder.receiveShadow =
            true;


        this.road.add(
            leftShoulder
        );


        const rightShoulder =
            leftShoulder.clone();


        rightShoulder.position.x =
            6.25;


        this.road.add(
            rightShoulder
        );

    }



    // ========================================================
    // ROAD DETAILS
    // ========================================================

    createRoadDetails() {

        // ----------------------------------------------------
        // CENTER LANE MARKERS
        // ----------------------------------------------------

        const markerMaterial =
            new THREE.MeshStandardMaterial({

                color: 0xd8d8d8,

                roughness: 0.7

            });


        for (
            let z = -85;
            z < 90;
            z += 8
        ) {

            const markerGeometry =
                new THREE.PlaneGeometry(
                    0.12,
                    4
                );


            const marker =
                new THREE.Mesh(
                    markerGeometry,
                    markerMaterial
                );


            marker.rotation.x =
                -Math.PI / 2;


            marker.position.set(
                0,
                0.025,
                z
            );


            this.road.add(
                marker
            );

        }


        // ----------------------------------------------------
        // ROAD EDGE LINES
        // ----------------------------------------------------

        const edgeMaterial =
            new THREE.MeshStandardMaterial({

                color: 0xbfc2c4,

                roughness: 0.7

            });


        const edgeGeometry =
            new THREE.PlaneGeometry(
                0.08,
                180
            );


        const leftEdge =
            new THREE.Mesh(
                edgeGeometry,
                edgeMaterial
            );


        leftEdge.rotation.x =
            -Math.PI / 2;


        leftEdge.position.set(
            -4.55,
            0.026,
            0
        );


        this.road.add(
            leftEdge
        );


        const rightEdge =
            leftEdge.clone();


        rightEdge.position.x =
            4.55;


        this.road.add(
            rightEdge
        );

    }



    // ========================================================
    // ENVIRONMENT
    // ========================================================

    createEnvironment() {

        // ----------------------------------------------------
        // GROUND
        // ----------------------------------------------------

        const groundGeometry =
            new THREE.PlaneGeometry(
                180,
                180
            );


        const groundMaterial =
            new THREE.MeshStandardMaterial({

                color: 0x172018,

                roughness: 1,

                metalness: 0

            });


        const ground =
            new THREE.Mesh(
                groundGeometry,
                groundMaterial
            );


        ground.rotation.x =
            -Math.PI / 2;


        ground.position.y =
            -0.04;


        ground.receiveShadow =
            true;


        this.environment.add(
            ground
        );


        // ----------------------------------------------------
        // SIDE TERRAIN
        // ----------------------------------------------------

        this.createTerrainSide(
            -1
        );

        this.createTerrainSide(
            1
        );


        // ----------------------------------------------------
        // ORBITAL NIGHT ENVIRONMENT (Stars, Planet & Skyline)
        // ----------------------------------------------------

        this.orbitalEnvironment =
            new SmartCarEnvironment(
                this.environment,
                this.camera
            );

    }



    // ========================================================
    // TERRAIN
    // ========================================================

    createTerrainSide(side) {

        const terrainWidth =
            35;

        const terrainLength =
            180;


        const geometry =
            new THREE.PlaneGeometry(
                terrainWidth,
                terrainLength,
                20,
                60
            );


        const position =
            geometry.attributes.position;


        for (
            let i = 0;
            i < position.count;
            i++
        ) {

            const x =
                position.getX(i);

            const z =
                position.getY(i);


            const wave =
                Math.sin(
                    z * 0.07
                ) * 0.25;


            const secondary =
                Math.sin(
                    z * 0.19
                ) * 0.08;


            position.setZ(
                i,
                wave + secondary
            );

        }


        geometry.computeVertexNormals();


        const material =
            new THREE.MeshStandardMaterial({

                color: 0x182219,

                roughness: 1

            });


        const terrain =
            new THREE.Mesh(
                geometry,
                material
            );


        terrain.rotation.x =
            -Math.PI / 2;


        terrain.position.x =
            side * 23;


        terrain.receiveShadow =
            true;


        this.environment.add(
            terrain
        );

    }



    // ========================================================
    // DISTANT HILLS
    // ========================================================

    createDistantHills() {
        const isMobile = (typeof window !== "undefined") && (
            window.innerWidth < 768 ||
            /Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent || "")
        );

        const material =
            new THREE.MeshStandardMaterial({
                color: 0x10171b,
                roughness: 1
            });

        const hillCount = isMobile ? 4 : 12;
        const segW = isMobile ? 10 : 20;
        const segH = isMobile ? 8 : 12;

        for (
            let i = 0;
            i < hillCount;
            i++
        ) {
            const radius =
                8 +
                Math.random() * 8;

            const geometry =
                new THREE.SphereGeometry(
                    radius,
                    segW,
                    segH
                );


            const hill =
                new THREE.Mesh(
                    geometry,
                    material
                );


            hill.scale.y =
                0.35;


            hill.position.set(

                (Math.random() - 0.5)
                * 100,

                radius * 0.15,

                -45 -
                Math.random() * 40

            );


            hill.receiveShadow =
                true;


            this.environment.add(
                hill
            );

        }

    }



    // ========================================================
    // ATMOSPHERE
    // ========================================================

    createAtmosphere() {
        const isMobile = (typeof window !== "undefined") && (
            window.innerWidth < 768 ||
            /Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent || "")
        );

        // ----------------------------------------------------
        // SMALL FLOATING PARTICLES (SCALED FOR MOBILE PERFORMANCE)
        // ----------------------------------------------------

        const particleCount = isMobile ? 180 : 900;


        const positions =
            new Float32Array(
                particleCount * 3
            );


        for (
            let i = 0;
            i < particleCount;
            i++
        ) {

            positions[i * 3] =
                (Math.random() - 0.5) * 80;


            positions[i * 3 + 1] =
                Math.random() * 12;


            positions[i * 3 + 2] =
                -Math.random() * 120;

        }


        const geometry =
            new THREE.BufferGeometry();


        geometry.setAttribute(

            "position",

            new THREE.BufferAttribute(
                positions,
                3
            )

        );


        const material =
            new THREE.PointsMaterial({

                color: 0xc7d5e8,

                size: 0.025,

                transparent: true,

                opacity: 0.32,

                depthWrite: false

            });


        this.particles =
            new THREE.Points(
                geometry,
                material
            );


        this.environment.add(
            this.particles
        );

    }



    // ========================================================
    // RESIZE
    // ========================================================

    getSafePixelRatio() {
        const isMobile = (typeof window !== "undefined") && (
            window.innerWidth < 768 ||
            /Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent || "")
        );
        // Phase 11 Mobile performance target: pixel ratio ≈ 1.2 (capped from 1.5 safeguard for flagship 60fps)
        const maxPR = isMobile ? 1.2 : 2.0;
        return Math.min(window.devicePixelRatio || 1, maxPR);
    }


    handleResize() {

        const width =
            this.canvas.clientWidth ||
            window.innerWidth;


        const height =
            this.canvas.clientHeight ||
            window.innerHeight;


        if (
            width <= 0 ||
            height <= 0
        ) {

            return;

        }


        const aspect =
            width / height;

        this.camera.aspect =
            aspect;

        // Responsive FOV scaling:
        // On portrait and narrow viewports (aspect < 1.25), scale vertical FOV smoothly
        // to preserve full vehicle framing without horizontal clipping or distortion.
        if (aspect < 1.25) {
            this.camera.fov =
                Math.min(58, Math.round(SCENE_CONFIG.cameraFov + (1.25 - aspect) * 16));
        } else {
            this.camera.fov =
                SCENE_CONFIG.cameraFov;
        }

        this.camera.updateProjectionMatrix();


        this.renderer.setSize(
            width,
            height,
            false
        );


        this.renderer.setPixelRatio(
            this.getSafePixelRatio()
        );

    }



    update(delta) {

        this.elapsedTime +=
            delta;


        // ----------------------------------------------------
        // SMOOTH LIGHTING PROFILE DAMPING
        // ----------------------------------------------------

        if (this.targetLighting) {
            const lerpFactor = Math.min(delta * 4.0, 1.0);

            if (this.ambientLight) {
                this.ambientLight.intensity = THREE.MathUtils.damp(
                    this.ambientLight.intensity,
                    this.targetLighting.ambientIntensity ?? this.targetLighting.ambient,
                    3.5,
                    delta
                );
                if (this.targetLighting.ambientColor !== undefined) {
                    this.ambientLight.color.lerp(new THREE.Color(this.targetLighting.ambientColor), lerpFactor);
                }
                if (this.targetLighting.groundColor !== undefined) {
                    this.ambientLight.groundColor.lerp(new THREE.Color(this.targetLighting.groundColor), lerpFactor);
                }
            }

            if (this.directionalLight) {
                this.directionalLight.intensity = THREE.MathUtils.damp(
                    this.directionalLight.intensity,
                    this.targetLighting.directionalIntensity ?? this.targetLighting.directional,
                    3.5,
                    delta
                );
                if (this.targetLighting.directionalColor !== undefined) {
                    this.directionalLight.color.lerp(new THREE.Color(this.targetLighting.directionalColor), lerpFactor);
                }
                if (this.targetLighting.directionalPos) {
                    const [px, py, pz] = this.targetLighting.directionalPos;
                    this.directionalLight.position.lerp(new THREE.Vector3(px, py, pz), lerpFactor);
                }
            }

            if (this.rimLight) {
                this.rimLight.intensity = THREE.MathUtils.damp(
                    this.rimLight.intensity,
                    this.targetLighting.rimIntensity ?? this.targetLighting.rim,
                    3.5,
                    delta
                );
                if (this.targetLighting.rimColor !== undefined) {
                    this.rimLight.color.lerp(new THREE.Color(this.targetLighting.rimColor), lerpFactor);
                }
                if (this.targetLighting.rimPos) {
                    const [rx, ry, rz] = this.targetLighting.rimPos;
                    this.rimLight.position.lerp(new THREE.Vector3(rx, ry, rz), lerpFactor);
                }
            }

            if (this.frontLight) {
                this.frontLight.intensity = THREE.MathUtils.damp(
                    this.frontLight.intensity,
                    this.targetLighting.frontIntensity ?? this.targetLighting.front,
                    3.5,
                    delta
                );
                if (this.targetLighting.frontColor !== undefined) {
                    this.frontLight.color.lerp(new THREE.Color(this.targetLighting.frontColor), lerpFactor);
                }
            }

            if (this.renderer && this.targetLighting.exposure !== undefined) {
                this.renderer.toneMappingExposure = THREE.MathUtils.damp(
                    this.renderer.toneMappingExposure,
                    this.targetLighting.exposure,
                    3.5,
                    delta
                );
            }

            if (this.scene.fog && this.targetLighting.fogColor !== undefined) {
                this.scene.fog.color.lerp(new THREE.Color(this.targetLighting.fogColor), lerpFactor);
            }
        }


        // ----------------------------------------------------
        // PARTICLE MOTION
        // ----------------------------------------------------

        if (this.particles) {

            this.particles.rotation.y =
                this.elapsedTime *
                0.003;

        }


        // ----------------------------------------------------
        // ORBITAL ENVIRONMENT UPDATE
        // ----------------------------------------------------

        if (this.orbitalEnvironment && typeof this.orbitalEnvironment.update === "function") {
            this.orbitalEnvironment.update(delta);
        }

    }



    // ========================================================
    // RENDER LOOP
    // ========================================================

    animate() {

        if (!this.isRunning) {

            return;

        }


        requestAnimationFrame(
            () => this.animate()
        );


        const delta =
            Math.min(
                this.clock.getDelta(),
                0.05
            );


        this.update(
            delta
        );


        this.renderer.render(
            this.scene,
            this.camera
        );

    }



    // ========================================================
    // PUBLIC API
    // ========================================================

    getScene() {

        return this.scene;

    }


    getCamera() {

        return this.camera;

    }


    getRenderer() {

        return this.renderer;

    }


    destroy() {

        this.isRunning =
            false;


        window.removeEventListener(
            "resize",
            this.handleResize
        );


        if (this.orbitalEnvironment && typeof this.orbitalEnvironment.dispose === "function") {
            this.orbitalEnvironment.dispose();
            this.orbitalEnvironment = null;
        }

        this.renderer.dispose();

    }

}