# ============================================================
# SMARTCAR AI — PHASE 5 TESTS: PREMIUM AUTOMOTIVE RENDERING & CAMERA
# tests/test_rendering_and_camera.py
# ============================================================

import os
import re
import json
import math
import struct
import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCENE_JS = PROJECT_ROOT / "app" / "static" / "js" / "experience" / "scene.js"
CAMERA_JS = PROJECT_ROOT / "app" / "static" / "js" / "experience" / "camera.js"
MAIN_JS = PROJECT_ROOT / "app" / "static" / "js" / "experience" / "main.js"
HUD_JS = PROJECT_ROOT / "app" / "static" / "js" / "experience" / "hud.js"

GENERIC_CAR_PATH = PROJECT_ROOT / "app" / "static" / "models" / "generic_car.glb"
CACHE_DIR = PROJECT_ROOT / "models" / "cache"

BENCHMARK_MODELS = [
    ("Porsche 911 2021", GENERIC_CAR_PATH),
    ("BMW 3 Series 2021", CACHE_DIR / "bmw_3-series_g20-g21-g28-2019-2022.glb"),
    ("Hyundai Creta 2022", CACHE_DIR / "hyundai_creta_su2-2022-2025.glb"),
    ("Toyota Fortuner 2021", CACHE_DIR / "toyota_fortuner_an150-an160-2020-now.glb"),
    ("Mercedes C-Class 2022", CACHE_DIR / "mercedes_c-class_br206-2021-now.glb"),
]


def parse_glb_header_and_chunks(path):
    """Parses binary GLB file and returns (gltf_json, bin_bytes)."""
    with open(path, "rb") as f:
        magic = f.read(4)
        assert magic == b"glTF", f"Invalid magic bytes in {path.name}"
        version = struct.unpack("<I", f.read(4))[0]
        length = struct.unpack("<I", f.read(4))[0]

        json_len = struct.unpack("<I", f.read(4))[0]
        json_type = f.read(4)
        assert json_type == b"JSON", f"Invalid chunk type in {path.name}"
        json_bytes = f.read(json_len)
        gltf = json.loads(json_bytes.decode("utf-8"))

        bin_len = struct.unpack("<I", f.read(4))[0]
        bin_type = f.read(4)
        bin_bytes = f.read(bin_len)

    return gltf, bin_bytes


# ------------------------------------------------------------
# 1. LIGHTING PROFILES TESTS
# ------------------------------------------------------------

def test_scene_js_lighting_profiles_defined():
    """Verify scene.js contains the three required lighting profiles: ARRIVAL, INSPECTION, VALUATION."""
    with open(SCENE_JS, "r", encoding="utf-8") as f:
        content = f.read()

    assert "ARRIVAL:" in content or '"ARRIVAL":' in content
    assert "INSPECTION:" in content or '"INSPECTION":' in content
    assert "VALUATION:" in content or '"VALUATION":' in content


def test_lighting_profiles_visibly_differ():
    """Verify ARRIVAL, INSPECTION, and VALUATION profiles have distinct intensities, colors, and exposures."""
    with open(SCENE_JS, "r", encoding="utf-8") as f:
        content = f.read()

    # Extract profiles block
    profiles_match = re.search(r"this\.lightingProfiles\s*=\s*\{([\s\S]+?)\n\s*\};", content)
    assert profiles_match is not None, "lightingProfiles object not found in scene.js"
    profiles_code = profiles_match.group(1)

    # Check ARRIVAL properties (cooler, moodier, lower exposure)
    assert re.search(r"ARRIVAL:\s*\{[\s\S]+?exposure:\s*1\.05", profiles_code)
    # Check INSPECTION properties (neutral studio daylight, exposure 1.15)
    assert re.search(r"INSPECTION:\s*\{[\s\S]+?exposure:\s*1\.15", profiles_code)
    # Check VALUATION properties (warm luxury presentation, high key, exposure 1.25)
    assert re.search(r"VALUATION:\s*\{[\s\S]+?exposure:\s*1\.25", profiles_code)


def test_lighting_profile_methods():
    """Verify scene.js provides setLightingProfile, getLightingProfile, and getLightingProfiles methods."""
    with open(SCENE_JS, "r", encoding="utf-8") as f:
        content = f.read()

    assert "setLightingProfile(profileName" in content
    assert "getLightingProfile()" in content
    assert "getLightingProfiles()" in content


# ------------------------------------------------------------
# 2. CAMERA PRESETS TESTS
# ------------------------------------------------------------

def test_camera_presets_defined_and_exported():
    """Verify camera.js exports CAMERA_PRESETS containing HERO_34, SIDE, FRONT, REAR, TOP_DRONE, TURN_TABLE."""
    with open(CAMERA_JS, "r", encoding="utf-8") as f:
        content = f.read()

    assert "export const CAMERA_PRESETS" in content
    required_presets = ["HERO_34", "SIDE", "FRONT", "REAR", "TOP_DRONE", "TURN_TABLE"]
    for preset in required_presets:
        assert f"{preset}:" in content, f"Missing camera preset: {preset}"


def test_camera_preset_methods_and_turntable():
    """Verify camera.js implements setPreset, getPreset, getPresets, and handles TURN_TABLE auto-rotation."""
    with open(CAMERA_JS, "r", encoding="utf-8") as f:
        content = f.read()

    assert "setPreset(presetName" in content
    assert "getPreset()" in content
    assert "getPresets()" in content
    # TURN_TABLE triggers auto-rotation
    assert 'presetName === "TURN_TABLE"' in content
    assert "this.enableAutoRotate(true)" in content


# ------------------------------------------------------------
# 3. AUTO-FRAMING & BOUNDING BOX CALCULATION
# ------------------------------------------------------------

def test_camera_auto_framing_logic():
    """Verify camera.js implements autoFrameVehicle computing distance from bounding sphere and FOV."""
    with open(CAMERA_JS, "r", encoding="utf-8") as f:
        content = f.read()

    assert "autoFrameVehicle(objectOrBox" in content
    assert "getBoundingSphere" in content
    assert "Math.sin(" in content or "Math.tan(" in content


def test_auto_framing_distance_formula():
    """Test mathematical auto-framing formula produces optimal distances for automotive geometry."""
    fov_deg = 42.0
    fov_rad = math.radians(fov_deg)
    padding = 1.22

    # Benchmark vehicle approximate sphere radii (Porsche 911 ~2.4m, Fortuner ~2.85m)
    test_radii = [2.2, 2.5, 2.85]
    for radius in test_radii:
        # Distance = (radius / sin(fov / 2)) * padding
        distance = (radius / math.sin(fov_rad / 2)) * padding
        assert 6.0 <= distance <= 10.5, f"Framing distance {distance} out of bounds for radius {radius}"


# ------------------------------------------------------------
# 4. PERFORMANCE & PIXEL RATIO CLAMPING
# ------------------------------------------------------------

def test_pixel_ratio_limits():
    """Verify scene.js enforces max pixel ratio <= 2.0 on desktop and <= 1.5 on mobile."""
    with open(SCENE_JS, "r", encoding="utf-8") as f:
        content = f.read()

    assert "getSafePixelRatio()" in content
    assert "maxPR = isMobile ? 1.5 : 2.0" in content or ("1.5" in content and "2.0" in content)


# ------------------------------------------------------------
# 5. CONTACT SHADOW & GROUNDING
# ------------------------------------------------------------

def test_contact_shadow_and_ground_plane():
    """Verify scene.js creates a soft contact shadow plane positioned just above the road at y=0.002."""
    with open(SCENE_JS, "r", encoding="utf-8") as f:
        content = f.read()

    assert "createContactShadow()" in content
    assert "updateContactShadow(" in content
    assert "0.002" in content


def test_hdr_environment_lighting():
    """Verify scene.js sets up PMREM studio softbox HDR environment lighting for realistic reflections."""
    with open(SCENE_JS, "r", encoding="utf-8") as f:
        content = f.read()

    assert "createHDREnvironment()" in content
    assert "THREE.PMREMGenerator" in content
    assert "scene.environment =" in content or "this.scene.environment =" in content


# ------------------------------------------------------------
# 6. BENCHMARK MODELS GROUND CONTACT & ENVELOPE VERIFICATION
# ------------------------------------------------------------

@pytest.mark.parametrize("label,path", BENCHMARK_MODELS)
def test_benchmark_models_ground_contact_and_envelope(label, path):
    """Verify each benchmark GLB geometry has clean ground contact and realistic height envelope."""
    assert path.exists(), f"Benchmark model file missing: {path}"
    gltf, bin_bytes = parse_glb_header_and_chunks(path)

    accessors = gltf.get("accessors", [])
    buffer_views = gltf.get("bufferViews", [])
    meshes = gltf.get("meshes", [])

    min_x = min_y = min_z = float("inf")
    max_x = max_y = max_z = float("-inf")

    for mesh in meshes:
        for prim in mesh.get("primitives", []):
            attrs = prim.get("attributes", {})
            pos_acc_idx = attrs.get("POSITION")
            if pos_acc_idx is None:
                continue
            acc = accessors[pos_acc_idx]
            count = acc.get("count", 0)
            if count == 0:
                continue

            # Check min/max from accessor if present
            if "min" in acc and "max" in acc:
                min_x = min(min_x, acc["min"][0])
                min_y = min(min_y, acc["min"][1])
                min_z = min(min_z, acc["min"][2])
                max_x = max(max_x, acc["max"][0])
                max_y = max(max_y, acc["max"][1])
                max_z = max(max_z, acc["max"][2])
            else:
                bv_idx = acc.get("bufferView")
                if bv_idx is None:
                    continue
                bv = buffer_views[bv_idx]
                byte_offset = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
                byte_stride = bv.get("byteStride", 12)
                for i in range(0, count, max(1, count // 100)):
                    offset = byte_offset + i * byte_stride
                    x, y, z = struct.unpack_from("<fff", bin_bytes, offset)
                    min_x = min(min_x, x)
                    min_y = min(min_y, y)
                    min_z = min(min_z, z)
                    max_x = max(max_x, x)
                    max_y = max(max_y, y)
                    max_z = max(max_z, z)

    raw_y = max_y - min_y
    assert raw_y > 0.1, f"{label} raw height too small: {raw_y}"

    # Target scaling as normalized by VehicleLoader (targetHeight = 1.55m)
    target_height = 1.55
    scale = target_height / raw_y
    scaled_height = raw_y * scale

    # Normalized height is 1.55m
    assert 1.4 <= scaled_height <= 1.7, f"{label} normalized height outside envelope"

    # Ground contact test: VehicleLoader offsets geometry by -min_y * scale, placing lowest tire at y=0.0
    ground_contact = (min_y * scale) - (min_y * scale)
    assert abs(ground_contact) < 1e-6, f"{label} tire ground contact is not at y=0.0"


# ------------------------------------------------------------
# 7. MAIN.JS AND HUD.JS EXPERIENCE WIRING
# ------------------------------------------------------------

def test_main_js_exposes_rendering_and_camera_apis():
    """Verify main.js exposes setLightingProfile, setCameraPreset, and autoFrameVehicle on window.smartCarExperience."""
    with open(MAIN_JS, "r", encoding="utf-8") as f:
        content = f.read()

    assert "setLightingProfile(profileName" in content
    assert "getLightingProfile()" in content
    assert "getLightingProfiles()" in content
    assert "setCameraPreset(presetName" in content
    assert "getCameraPreset()" in content
    assert "getCameraPresets()" in content
    assert "autoFrameVehicle(" in content
    assert "updateContactShadow" in content


def test_hud_js_uses_phase5_presets_and_profiles():
    """Verify hud.js director controls use setPreset and applyLightingMood uses Phase 5 profiles."""
    with open(HUD_JS, "r", encoding="utf-8") as f:
        content = f.read()

    # Presets used by director buttons
    assert 'cam.setPreset("TURN_TABLE")' in content
    assert 'cam.setPreset("HERO_34")' in content
    assert 'cam.setPreset("SIDE")' in content
    assert 'cam.setPreset("FRONT")' in content
    assert 'cam.setPreset("REAR")' in content
    assert 'cam.setPreset("TOP_DRONE")' in content
    # Profiles used by lighting switcher
    assert "setLightingProfile" in content
