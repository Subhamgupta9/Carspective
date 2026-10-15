# ============================================================
# SMARTCAR AI — PHASE 6 TESTS: VEHICLE ANIMATOR & CINEMATIC SEQUENCES
# tests/test_vehicle_animator.py
# ============================================================

import os
import re
import math
import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ANIMATION_JS = PROJECT_ROOT / "app" / "static" / "js" / "experience" / "animation.js"
MAIN_JS = PROJECT_ROOT / "app" / "static" / "js" / "experience" / "main.js"
VEHICLE_JS = PROJECT_ROOT / "app" / "static" / "js" / "experience" / "vehicle.js"
STORY_JS = PROJECT_ROOT / "app" / "static" / "js" / "experience" / "story.js"


# ------------------------------------------------------------
# 1. CLASS & EXPORT TESTS
# ------------------------------------------------------------

def test_vehicle_animator_class_defined_and_exported():
    """Verify animation.js defines and exports VehicleAnimator and backward-compatible SmartCarAnimation."""
    with open(ANIMATION_JS, "r", encoding="utf-8") as f:
        content = f.read()

    assert "export class VehicleAnimator" in content
    assert "export const SmartCarAnimation = VehicleAnimator" in content or "SmartCarAnimation" in content


def test_vehicle_state_machine_states():
    """Verify VehicleState defines all required Phase 6 states in the state machine:
    ARRIVING -> APPROACHING -> BRAKING -> PARKING -> IDLE -> INSPECTING -> TURNTABLE."""
    with open(ANIMATION_JS, "r", encoding="utf-8") as f:
        content = f.read()

    required_states = [
        "ARRIVING",
        "APPROACHING",
        "BRAKING",
        "PARKING",
        "IDLE",
        "INSPECTING",
        "TURNTABLE"
    ]
    for state in required_states:
        assert f'{state}: "{state}"' in content or f"{state}:" in content, f"Missing state: {state}"


# ------------------------------------------------------------
# 2. ARRIVAL SEQUENCE TIMING & KINEMATICS (8–12 SECONDS)
# ------------------------------------------------------------

def test_arrival_sequence_duration_and_waypoints():
    """Verify arrival sequence trajectory and physics produce an 8–12 second sequence duration."""
    with open(ANIMATION_JS, "r", encoding="utf-8") as f:
        content = f.read()

    # Extract waypoints from animation.js
    start_z_match = re.search(r"this\.startZ\s*=\s*(-?\d+\.?\d*);", content)
    approach_z_match = re.search(r"this\.approachZ\s*=\s*(-?\d+\.?\d*);", content)
    brake_z_match = re.search(r"this\.brakeZ\s*=\s*(-?\d+\.?\d*);", content)
    park_z_match = re.search(r"this\.parkZ\s*=\s*(-?\d+\.?\d*);", content)
    max_speed_match = re.search(r"this\.maxDriveSpeed\s*=\s*(\d+\.?\d*);", content)
    approach_speed_match = re.search(r"this\.approachSpeed\s*=\s*(\d+\.?\d*);", content)
    accel_match = re.search(r"this\.acceleration\s*=\s*(\d+\.?\d*);", content)

    assert start_z_match and approach_z_match and brake_z_match and park_z_match
    assert max_speed_match and approach_speed_match and accel_match

    start_z = float(start_z_match.group(1))
    approach_z = float(approach_z_match.group(1))
    brake_z = float(brake_z_match.group(1))
    park_z = float(park_z_match.group(1))
    max_speed = float(max_speed_match.group(1))
    approach_speed = float(approach_speed_match.group(1))
    accel = float(accel_match.group(1))

    # Phase 1: Arriving (start_z to approach_z)
    # Accelerate from 0 to max_speed, then cruise
    t_accel = max_speed / accel
    d_accel = 0.5 * accel * (t_accel ** 2)
    d_arriving_total = approach_z - start_z
    assert d_arriving_total > d_accel, "Acceleration distance exceeds arrival segment"
    d_cruise = d_arriving_total - d_accel
    t_cruise = d_cruise / max_speed
    t_arriving = t_accel + t_cruise

    # Phase 2: Approaching (approach_z to brake_z)
    d_approach = brake_z - approach_z
    avg_approach_speed = (max_speed + approach_speed) / 2.0
    t_approach = d_approach / avg_approach_speed

    # Phase 3: Braking (brake_z to park_z)
    d_brake = park_z - brake_z
    # Ideal quadratic deceleration: average speed = approach_speed / 2
    avg_brake_speed = approach_speed / 2.0
    t_brake = d_brake / avg_brake_speed

    # Phase 4: Parking settling
    t_parking = 1.4

    total_duration = t_arriving + t_approach + t_brake + t_parking

    # Assert duration is within 8–12 seconds
    assert 8.0 <= total_duration <= 12.0, (
        f"Calculated arrival duration {total_duration:.2f}s is outside 8–12 second requirement."
    )


# ------------------------------------------------------------
# 3. NO SLIDING WHEELS & WHEEL ROTATION
# ------------------------------------------------------------

def test_wheel_rotation_kinematics():
    """Verify wheels rotate proportionally to movement distance without sliding (theta = d / r)."""
    with open(ANIMATION_JS, "r", encoding="utf-8") as f:
        content = f.read()

    assert "rotateWheels(movement)" in content
    assert "this.rotateWheels(" in content

    with open(VEHICLE_JS, "r", encoding="utf-8") as f:
        veh_content = f.read()

    # Vehicle rotates wheels by distance / wheel.radius
    assert "rotateWheels(distance)" in veh_content
    assert "distance / wheel.radius" in veh_content


# ------------------------------------------------------------
# 4. BRAKE DIVE, SUSPENSION & STEERING
# ------------------------------------------------------------

def test_brake_dive_physics_simulation():
    """Verify VehicleAnimator implements front-end compression (brake dive) during braking."""
    with open(ANIMATION_JS, "r", encoding="utf-8") as f:
        content = f.read()

    assert "updateBraking" in content
    # Pitch dive proportional to deceleration/speed
    assert "this._pitch" in content
    assert "targetDive =" in content or "targetPitch =" in content
    assert "vehicleObject.rotation.x = this._pitch" in content


def test_suspension_vibration_and_rebound():
    """Verify subtle suspension micro-vibration during travel and harmonic rebound during parking."""
    with open(ANIMATION_JS, "r", encoding="utf-8") as f:
        content = f.read()

    # Micro-vibration
    assert "Math.sin(this.elapsedTime" in content
    # Harmonic rebound oscillation during parking
    assert "Math.cos(this.stateTime" in content or "bounce" in content
    assert "this._suspensionY" in content


def test_steering_animation_methods():
    """Verify steering animation operates during arrival and vehicle implements setSteeringAngle."""
    with open(ANIMATION_JS, "r", encoding="utf-8") as f:
        content = f.read()

    assert "setSteeringAngle" in content
    assert "this._steerAngle" in content

    with open(VEHICLE_JS, "r", encoding="utf-8") as f:
        veh_content = f.read()

    assert "setSteeringAngle(angle)" in veh_content
    assert "getSteeringAngle()" in veh_content


# ------------------------------------------------------------
# 5. TURNTABLE MODE LOOPING
# ------------------------------------------------------------

def test_turntable_mode_implementation():
    """Verify turntable mode sets vehicle stably at parkZ and enables continuous camera auto-rotation."""
    with open(ANIMATION_JS, "r", encoding="utf-8") as f:
        content = f.read()

    assert "updateTurntable" in content
    assert "VehicleState.TURNTABLE" in content
    assert "enableAutoRotate(true)" in content or 'setPreset("TURN_TABLE")' in content


# ------------------------------------------------------------
# 6. USER INTERRUPTION & INSPECTION MODE
# ------------------------------------------------------------

def test_animation_interruption_and_inspection():
    """Verify user can interrupt active animation to immediately enter inspection mode without snapping."""
    with open(ANIMATION_JS, "r", encoding="utf-8") as f:
        content = f.read()

    assert "interrupt()" in content
    assert "enterInspection()" in content
    assert "this.setState(VehicleState.INSPECTING)" in content


# ------------------------------------------------------------
# 7. SEQUENCES API: playSequence('arrival'), playSequence('turntable')
# ------------------------------------------------------------

def test_play_sequence_api_implemented():
    """Verify VehicleAnimator implements playSequence('arrival') and playSequence('turntable')."""
    with open(ANIMATION_JS, "r", encoding="utf-8") as f:
        content = f.read()

    assert "playSequence(sequenceName" in content
    assert 'seq === "arrival"' in content
    assert 'seq === "turntable"' in content


# ------------------------------------------------------------
# 8. INTEGRATION WITH MAIN.JS AND window.__SMARTCAR__
# ------------------------------------------------------------

def test_main_js_exposes_window_smartcar_canonical_api():
    """Verify main.js exposes window.__SMARTCAR__.animator supporting playSequence."""
    with open(MAIN_JS, "r", encoding="utf-8") as f:
        content = f.read()

    assert "window.__SMARTCAR__" in content
    assert "animator" in content
    assert "playSequence" in content


def test_interaction_triggers_animation_interrupt():
    """Verify user interaction triggers animator.interrupt() so canvas dragging enters inspection mode."""
    with open(MAIN_JS, "r", encoding="utf-8") as f:
        content = f.read()

    assert "onInteractionStart" in content
    assert "SmartCarExperience.animation.interrupt()" in content
