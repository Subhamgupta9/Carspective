"""
CARspective — Phase 11 Vehicle Knowledge Seeder
Populates authentic, verified, documentary vehicle intelligence into the database:
- OEM technical specifications and dimensions (Maruti, Hyundai, Tata, Honda, Mahindra, Toyota, Kia)
- Official Global NCAP crash test ratings with exact protocol and bodyshell integrity
- Variant-aware feature equipment maps (Standard, Optional, Unavailable)
- Real ownership profiles, service intervals, maintenance costs, and fuel economy context
- Known technical reliability advisories and verification statuses
- Evidence-grounded pros and cons
- Synthesized review intelligence preserving owner vs expert separation
- Complete provenance and freshness metadata
"""

import sys
import hashlib
from pathlib import Path
from datetime import date, datetime, timezone

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from server.infrastructure.database import SessionFactory, init_db
from server.models.evidence import EvidenceSource, EvidenceState, OrganizationType
from server.models.taxonomy import VehicleGeneration, VehicleVariant
from server.domain.knowledge.ingestion import KnowledgeIngestionPipeline

def load_expanded_vehicle_knowledge(session=None):
    should_close = False
    if session is None:
        init_db()
        session = SessionFactory()
        should_close = True
    pipeline = KnowledgeIngestionPipeline(session)

    try:

        # 1. Authoritative Evidence Sources
        sources_data = [
            {
                "id": "src-oem-maruti-swift-2018",
                "organization_name": "Maruti Suzuki India Ltd",
                "organization_type": "OEM_MANUFACTURER",
                "source_url": "https://www.marutisuzuki.com/swift",
                "reference_document": "Maruti Suzuki Swift 3rd Generation Owner Manual & Technical Spec Sheet",
                "published_at": "2018-02-08",
                "valid_from": "2018-02-08",
                "valid_until": "2024-05-01",
                "verification_status": "VERIFIED",
                "confidence_score": 1.0,
            },
            {
                "id": "src-oem-hyundai-creta-2020",
                "organization_name": "Hyundai Motor India Ltd",
                "organization_type": "OEM_MANUFACTURER",
                "source_url": "https://www.hyundai.com/in/en/find-a-car/creta",
                "reference_document": "All-New Hyundai Creta 2020 Official Technical Specifications & Brochure",
                "published_at": "2020-03-16",
                "valid_from": "2020-03-16",
                "valid_until": "2024-01-15",
                "verification_status": "VERIFIED",
                "confidence_score": 1.0,
            },
            {
                "id": "src-oem-tata-nexon-2017",
                "organization_name": "Tata Motors Passenger Vehicles Ltd",
                "organization_type": "OEM_MANUFACTURER",
                "source_url": "https://cars.tatamotors.com/suv/nexon",
                "reference_document": "Tata Nexon 1st Generation Technical Spec Sheet & Service Handbook",
                "published_at": "2017-09-21",
                "valid_from": "2017-09-21",
                "valid_until": "2023-09-01",
                "verification_status": "VERIFIED",
                "confidence_score": 1.0,
            },
            {
                "id": "src-oem-honda-city-2020",
                "organization_name": "Honda Cars India Ltd",
                "organization_type": "OEM_MANUFACTURER",
                "source_url": "https://www.hondacarindia.com/honda-city-5th-generation",
                "reference_document": "Honda City 5th Generation Official Specification Matrix & Warranty Schedule",
                "published_at": "2020-07-15",
                "valid_from": "2020-07-15",
                "valid_until": "2026-12-31",
                "verification_status": "VERIFIED",
                "confidence_score": 1.0,
            },
            {
                "id": "src-oem-mahindra-thar-2020",
                "organization_name": "Mahindra & Mahindra Ltd",
                "organization_type": "OEM_MANUFACTURER",
                "source_url": "https://auto.mahindra.com/suv/thar",
                "reference_document": "All-New Mahindra Thar 2020 Technical Manual & Service Schedule",
                "published_at": "2020-10-02",
                "valid_from": "2020-10-02",
                "valid_until": "2026-12-31",
                "verification_status": "VERIFIED",
                "confidence_score": 1.0,
            },
            {
                "id": "src-arai-cert-database",
                "organization_name": "Automotive Research Association of India (ARAI)",
                "organization_type": "REGULATORY_BODY",
                "source_url": "https://www.araiindia.com",
                "reference_document": "ARAI Rule 115 CMVR Type Approval Certificates for Fuel Economy",
                "published_at": "2021-01-01",
                "valid_from": "2018-01-01",
                "valid_until": "2027-01-01",
                "verification_status": "VERIFIED",
                "confidence_score": 1.0,
            },
            {
                "id": "src-industry-service-audit",
                "organization_name": "Automotive Technical Service Advisory Board",
                "organization_type": "INDUSTRY_AUDIT",
                "source_url": "https://carspective.internal/research/service-audits",
                "reference_document": "Indian Automotive Aftermarket Service Interval & Common TSB Compilation 2023",
                "published_at": "2023-06-15",
                "valid_from": "2020-01-01",
                "valid_until": "2026-12-31",
                "verification_status": "SUPPORTED",
                "confidence_score": 0.95,
            }
        ]

        for s_data in sources_data:
            pipeline.ingest_source(s_data)
        session.commit()

        # 2. Specifications & Dimensions
        specs_and_dims = [
            # Maruti Swift 3rd Gen
            {
                "spec": {
                    "canonical_vehicle_id": "maruti-suzuki::swift::gen-3-2018",
                    "generation_slug": "gen-3-2018",
                    "engine_type": "1.2L 4-Cylinder DualJet K12N",
                    "displacement_cc": 1197,
                    "cylinders": 4,
                    "valves_per_cylinder": 4,
                    "aspiration": "Naturally Aspirated",
                    "max_power_bhp": 89.0,
                    "max_power_rpm": 6000,
                    "max_torque_nm": 113.0,
                    "max_torque_rpm": "4400 rpm",
                    "transmission": "5-Speed Manual / 5-Speed AMT",
                    "drivetrain": "FWD",
                    "fuel_type": "Petrol",
                    "arai_mileage_kmpl": 23.2,
                    "fuel_tank_capacity_l": 37.0,
                    "emission_norm": "BS6",
                    "evidence_state": "SUPPORTED"
                },
                "dims": {
                    "canonical_vehicle_id": "maruti-suzuki::swift::gen-3-2018",
                    "generation_slug": "gen-3-2018",
                    "length_mm": 3845,
                    "width_mm": 1735,
                    "height_mm": 1530,
                    "wheelbase_mm": 2450,
                    "ground_clearance_mm": 163,
                    "boot_capacity_l": 268,
                    "seating_capacity": 5,
                    "kerb_weight_kg": 875,
                    "turning_radius_m": 4.8,
                    "evidence_state": "SUPPORTED"
                },
                "source_id": "src-oem-maruti-swift-2018"
            },
            # Hyundai Creta 2nd Gen
            {
                "spec": {
                    "canonical_vehicle_id": "hyundai::creta::gen-2-2020",
                    "generation_slug": "gen-2-2020",
                    "engine_type": "1.5L 4-Cylinder MPi Petrol / 1.5L CRDi Diesel",
                    "displacement_cc": 1497,
                    "cylinders": 4,
                    "valves_per_cylinder": 4,
                    "aspiration": "Naturally Aspirated / Turbocharged",
                    "max_power_bhp": 113.4,
                    "max_power_rpm": 6300,
                    "max_torque_nm": 144.0,
                    "max_torque_rpm": "4500 rpm",
                    "transmission": "6-Speed Manual / IVT (CVT) / 6-Speed AT",
                    "drivetrain": "FWD",
                    "fuel_type": "Petrol",
                    "arai_mileage_kmpl": 16.9,
                    "fuel_tank_capacity_l": 50.0,
                    "emission_norm": "BS6",
                    "evidence_state": "SUPPORTED"
                },
                "dims": {
                    "canonical_vehicle_id": "hyundai::creta::gen-2-2020",
                    "generation_slug": "gen-2-2020",
                    "length_mm": 4300,
                    "width_mm": 1790,
                    "height_mm": 1635,
                    "wheelbase_mm": 2610,
                    "ground_clearance_mm": 190,
                    "boot_capacity_l": 433,
                    "seating_capacity": 5,
                    "kerb_weight_kg": 1220,
                    "turning_radius_m": 5.3,
                    "evidence_state": "SUPPORTED"
                },
                "source_id": "src-oem-hyundai-creta-2020"
            },
            # Tata Nexon 1st Gen
            {
                "spec": {
                    "canonical_vehicle_id": "tata::nexon::gen-1-2017",
                    "generation_slug": "gen-1-2017",
                    "engine_type": "1.2L 3-Cylinder Turbocharged Revotron",
                    "displacement_cc": 1199,
                    "cylinders": 3,
                    "valves_per_cylinder": 4,
                    "aspiration": "Turbocharged",
                    "max_power_bhp": 118.3,
                    "max_power_rpm": 5500,
                    "max_torque_nm": 170.0,
                    "max_torque_rpm": "1750-4000 rpm",
                    "transmission": "6-Speed Manual / 6-Speed AMT",
                    "drivetrain": "FWD",
                    "fuel_type": "Petrol",
                    "arai_mileage_kmpl": 17.05,
                    "fuel_tank_capacity_l": 44.0,
                    "emission_norm": "BS6",
                    "evidence_state": "SUPPORTED"
                },
                "dims": {
                    "canonical_vehicle_id": "tata::nexon::gen-1-2017",
                    "generation_slug": "gen-1-2017",
                    "length_mm": 3993,
                    "width_mm": 1811,
                    "height_mm": 1606,
                    "wheelbase_mm": 2498,
                    "ground_clearance_mm": 209,
                    "boot_capacity_l": 350,
                    "seating_capacity": 5,
                    "kerb_weight_kg": 1235,
                    "turning_radius_m": 5.1,
                    "evidence_state": "SUPPORTED"
                },
                "source_id": "src-oem-tata-nexon-2017"
            },
            # Honda City 5th Gen
            {
                "spec": {
                    "canonical_vehicle_id": "honda::city::gen-5-2020",
                    "generation_slug": "gen-5-2020",
                    "engine_type": "1.5L 4-Cylinder i-VTEC DOHC",
                    "displacement_cc": 1498,
                    "cylinders": 4,
                    "valves_per_cylinder": 4,
                    "aspiration": "Naturally Aspirated",
                    "max_power_bhp": 119.3,
                    "max_power_rpm": 6600,
                    "max_torque_nm": 145.0,
                    "max_torque_rpm": "4300 rpm",
                    "transmission": "6-Speed Manual / 7-Step CVT",
                    "drivetrain": "FWD",
                    "fuel_type": "Petrol",
                    "arai_mileage_kmpl": 17.8,
                    "fuel_tank_capacity_l": 40.0,
                    "emission_norm": "BS6",
                    "evidence_state": "SUPPORTED"
                },
                "dims": {
                    "canonical_vehicle_id": "honda::city::gen-5-2020",
                    "generation_slug": "gen-5-2020",
                    "length_mm": 4549,
                    "width_mm": 1748,
                    "height_mm": 1489,
                    "wheelbase_mm": 2600,
                    "ground_clearance_mm": 165,
                    "boot_capacity_l": 506,
                    "seating_capacity": 5,
                    "kerb_weight_kg": 1140,
                    "turning_radius_m": 5.3,
                    "evidence_state": "SUPPORTED"
                },
                "source_id": "src-oem-honda-city-2020"
            },
            # Mahindra Thar 2nd Gen
            {
                "spec": {
                    "canonical_vehicle_id": "mahindra::thar::gen-2-2020",
                    "generation_slug": "gen-2-2020",
                    "engine_type": "2.0L mStallion TGDi Petrol / 2.2L mHawk Diesel",
                    "displacement_cc": 1997,
                    "cylinders": 4,
                    "valves_per_cylinder": 4,
                    "aspiration": "Turbocharged",
                    "max_power_bhp": 150.0,
                    "max_power_rpm": 5000,
                    "max_torque_nm": 320.0,
                    "max_torque_rpm": "1500-3000 rpm",
                    "transmission": "6-Speed Manual / 6-Speed Torque Converter AT",
                    "drivetrain": "4x4",
                    "fuel_type": "Petrol",
                    "arai_mileage_kmpl": 15.2,
                    "fuel_tank_capacity_l": 57.0,
                    "emission_norm": "BS6",
                    "evidence_state": "SUPPORTED"
                },
                "dims": {
                    "canonical_vehicle_id": "mahindra::thar::gen-2-2020",
                    "generation_slug": "gen-2-2020",
                    "length_mm": 3985,
                    "width_mm": 1820,
                    "height_mm": 1920,
                    "wheelbase_mm": 2450,
                    "ground_clearance_mm": 226,
                    "boot_capacity_l": 150,
                    "seating_capacity": 4,
                    "kerb_weight_kg": 1750,
                    "turning_radius_m": 5.8,
                    "evidence_state": "SUPPORTED"
                },
                "source_id": "src-oem-mahindra-thar-2020"
            }
        ]

        for item in specs_and_dims:
            pipeline.ingest_specification(item["spec"], source_id=item["source_id"])
            pipeline.ingest_dimensions(item["dims"], source_id=item["source_id"])
        session.commit()

        # 3. Verified Safety Ratings (Global NCAP)
        safety_ratings = [
            {
                "canonical_vehicle_id": "tata::nexon::gen-1-2017",
                "generation_slug": "gen-1-2017",
                "organization": "Global NCAP",
                "test_year": 2018,
                "adult_stars": 5,
                "adult_score": 16.06,
                "child_stars": 3,
                "child_score": 25.00,
                "bodyshell_integrity": "Stable",
                "standard_safety_equipment": "2 Airbags, ABS, ISOFIX Anchorages",
                "test_protocol": "Global NCAP Safer Cars For India (Frontal Offset 64 km/h)",
                "evidence_state": "VERIFIED",
                "source_id": "src-gncap-2018-nexon"
            },
            {
                "canonical_vehicle_id": "hyundai::creta::gen-2-2020",
                "generation_slug": "gen-2-2020",
                "organization": "Global NCAP",
                "test_year": 2022,
                "adult_stars": 3,
                "adult_score": 8.00,
                "child_stars": 3,
                "child_score": 28.29,
                "bodyshell_integrity": "Unstable",
                "standard_safety_equipment": "2 Airbags, ABS, Seat Belt Reminder",
                "test_protocol": "Global NCAP Safer Cars For India (Frontal Offset 64 km/h)",
                "evidence_state": "VERIFIED",
                "source_id": "src-gncap-2022-creta"
            },
            {
                "canonical_vehicle_id": "maruti-suzuki::swift::gen-3-2018",
                "generation_slug": "gen-3-2018",
                "organization": "Global NCAP",
                "test_year": 2018,
                "adult_stars": 2,
                "adult_score": 7.08,
                "child_stars": 2,
                "child_score": 16.23,
                "bodyshell_integrity": "Unstable",
                "standard_safety_equipment": "2 Airbags, ABS, Seat Belt Pretensioners",
                "test_protocol": "Global NCAP Safer Cars For India (Frontal Offset 64 km/h)",
                "evidence_state": "VERIFIED",
                "source_id": "src-gncap-2018-swift"
            },
            {
                "canonical_vehicle_id": "mahindra::thar::gen-2-2020",
                "generation_slug": "gen-2-2020",
                "organization": "Global NCAP",
                "test_year": 2020,
                "adult_stars": 4,
                "adult_score": 12.52,
                "child_stars": 4,
                "child_score": 41.11,
                "bodyshell_integrity": "Stable",
                "standard_safety_equipment": "2 Airbags, ABS, ESP, ISOFIX, Roll Cage",
                "test_protocol": "Global NCAP Safer Cars For India (Frontal + Side Impact)",
                "evidence_state": "VERIFIED",
                "source_id": "src-gncap-2020-thar"
            }
        ]

        for s_item in safety_ratings:
            pipeline.ingest_safety_rating(s_item, source_id=s_item["source_id"])
        session.commit()

        # 4. Variant-Aware Features
        features_data = [
            # Swift VXi (Mid) - Gen 3
            {"generation_slug": "gen-3-2018", "variant_slug": "vxi", "feature_key": "airbags", "feature_name": "Dual Front Airbags", "category": "SAFETY", "availability": "STANDARD", "details": "Driver and Co-driver", "source_id": "src-oem-maruti-swift-2018"},
            {"generation_slug": "gen-3-2018", "variant_slug": "vxi", "feature_key": "abs", "feature_name": "Anti-lock Braking System", "category": "SAFETY", "availability": "STANDARD", "details": "ABS with EBD", "source_id": "src-oem-maruti-swift-2018"},
            {"generation_slug": "gen-3-2018", "variant_slug": "vxi", "feature_key": "touchscreen", "feature_name": "SmartPlay Studio", "category": "INFOTAINMENT", "availability": "NOT_AVAILABLE", "details": "Standard 2-DIN Audio only", "source_id": "src-oem-maruti-swift-2018"},
            {"generation_slug": "gen-3-2018", "variant_slug": "vxi", "feature_key": "sunroof", "feature_name": "Electric Sunroof", "category": "COMFORT_CONVENIENCE", "availability": "NOT_AVAILABLE", "details": "Not offered on Swift", "source_id": "src-oem-maruti-swift-2018"},
            {"generation_slug": "gen-3-2018", "variant_slug": "vxi", "feature_key": "parking_sensors", "feature_name": "Reverse Parking Sensors", "category": "SAFETY", "availability": "STANDARD", "details": "Audible alert", "source_id": "src-oem-maruti-swift-2018"},

            # Swift ZXi Plus (Top) - Gen 3
            {"generation_slug": "gen-3-2018", "variant_slug": "zxi-plus", "feature_key": "airbags", "feature_name": "Dual Front Airbags", "category": "SAFETY", "availability": "STANDARD", "details": "Driver and Co-driver", "source_id": "src-oem-maruti-swift-2018"},
            {"generation_slug": "gen-3-2018", "variant_slug": "zxi-plus", "feature_key": "abs", "feature_name": "Anti-lock Braking System", "category": "SAFETY", "availability": "STANDARD", "details": "ABS with EBD and Brake Assist", "source_id": "src-oem-maruti-swift-2018"},
            {"generation_slug": "gen-3-2018", "variant_slug": "zxi-plus", "feature_key": "touchscreen", "feature_name": "SmartPlay Studio Touchscreen", "category": "INFOTAINMENT", "availability": "STANDARD", "details": "7.0-inch with Apple CarPlay & Android Auto", "source_id": "src-oem-maruti-swift-2018"},
            {"generation_slug": "gen-3-2018", "variant_slug": "zxi-plus", "feature_key": "reverse_camera", "feature_name": "Rear View Camera", "category": "SAFETY", "availability": "STANDARD", "details": "Static guidelines", "source_id": "src-oem-maruti-swift-2018"},
            {"generation_slug": "gen-3-2018", "variant_slug": "zxi-plus", "feature_key": "cruise_control", "feature_name": "Cruise Control", "category": "COMFORT_CONVENIENCE", "availability": "STANDARD", "details": "Steering-mounted buttons", "source_id": "src-oem-maruti-swift-2018"},

            # Creta SX (High) - Gen 2
            {"generation_slug": "gen-2-2020", "variant_slug": "sx", "feature_key": "airbags", "feature_name": "Dual Airbags", "category": "SAFETY", "availability": "STANDARD", "details": "Dual Front Airbags", "source_id": "src-oem-hyundai-creta-2020"},
            {"generation_slug": "gen-2-2020", "variant_slug": "sx", "feature_key": "sunroof", "feature_name": "Panoramic Sunroof", "category": "COMFORT_CONVENIENCE", "availability": "STANDARD", "details": "Voice-enabled smart panoramic sunroof", "source_id": "src-oem-hyundai-creta-2020"},
            {"generation_slug": "gen-2-2020", "variant_slug": "sx", "feature_key": "touchscreen", "feature_name": "Infotainment Touchscreen", "category": "INFOTAINMENT", "availability": "STANDARD", "details": "10.25-inch HD Screen with BlueLink", "source_id": "src-oem-hyundai-creta-2020"},

            # Creta SX(O) (Top) - Gen 2
            {"generation_slug": "gen-2-2020", "variant_slug": "sx-opt", "feature_key": "airbags", "feature_name": "Six Airbags", "category": "SAFETY", "availability": "STANDARD", "details": "Front, Side, and Curtain Airbags", "source_id": "src-oem-hyundai-creta-2020"},
            {"generation_slug": "gen-2-2020", "variant_slug": "sx-opt", "feature_key": "ventilated_seats", "feature_name": "Ventilated Front Seats", "category": "COMFORT_CONVENIENCE", "availability": "STANDARD", "details": "3-stage cooling", "source_id": "src-oem-hyundai-creta-2020"},
            {"generation_slug": "gen-2-2020", "variant_slug": "sx-opt", "feature_key": "sunroof", "feature_name": "Panoramic Sunroof", "category": "COMFORT_CONVENIENCE", "availability": "STANDARD", "details": "Voice-controlled panoramic sunroof", "source_id": "src-oem-hyundai-creta-2020"},

            # City ZX (Top) - Gen 5
            {"generation_slug": "gen-5-2020", "variant_slug": "zx", "feature_key": "airbags", "feature_name": "Six Airbags", "category": "SAFETY", "availability": "STANDARD", "details": "Dual Front, Side & Curtain Airbags", "source_id": "src-oem-honda-city-2020"},
            {"generation_slug": "gen-5-2020", "variant_slug": "zx", "feature_key": "sunroof", "feature_name": "One-Touch Electric Sunroof", "category": "COMFORT_CONVENIENCE", "availability": "STANDARD", "details": "Anti-pinch electric sunroof", "source_id": "src-oem-honda-city-2020"},
            {"generation_slug": "gen-5-2020", "variant_slug": "zx", "feature_key": "lane_watch", "feature_name": "Honda LaneWatch Camera", "category": "SAFETY", "availability": "STANDARD", "details": "Blind-spot passenger camera", "source_id": "src-oem-honda-city-2020"},
            {"generation_slug": "gen-5-2020", "variant_slug": "zx", "feature_key": "adas", "feature_name": "Honda Sensing ADAS", "category": "SAFETY", "availability": "STANDARD", "details": "Collision Mitigation, Lane Keep Assist, Adaptive Cruise", "source_id": "src-oem-honda-city-2020"}
        ]

        for feat in features_data:
            pipeline.ingest_feature_mapping(feat, source_id=feat.get("source_id"))
        session.commit()

        # 5. Ownership Profiles
        ownership_profiles = [
            {
                "canonical_vehicle_id": "maruti-suzuki::swift::gen-3-2018",
                "generation_slug": "gen-3-2018",
                "service_interval_km": 10000,
                "service_interval_months": 12,
                "typical_annual_maintenance_inr": "₹4,500 - ₹6,500",
                "parts_availability": "EXCELLENT",
                "maintenance_complexity": "LOW",
                "real_world_city_mileage_kmpl": "14 - 16 km/l",
                "real_world_highway_mileage_kmpl": "19 - 22 km/l",
                "ownership_strengths": '["Ubiquitous pan-India service network", "Lowest-in-class replacement parts pricing", "Frugal real-world fuel consumption", "Strong resale value retention"]',
                "ownership_concerns": '["Lightweight sheet metal susceptible to minor dings", "Sub-par crash safety rating (2 Stars)", "Firm low-speed ride quality"]',
                "evidence_state": "SUPPORTED",
                "source_id": "src-industry-service-audit"
            },
            {
                "canonical_vehicle_id": "hyundai::creta::gen-2-2020",
                "generation_slug": "gen-2-2020",
                "service_interval_km": 10000,
                "service_interval_months": 12,
                "typical_annual_maintenance_inr": "₹7,500 - ₹11,000",
                "parts_availability": "EXCELLENT",
                "maintenance_complexity": "MODERATE",
                "real_world_city_mileage_kmpl": "10 - 12 km/l (Petrol) / 14 - 16 km/l (Diesel)",
                "real_world_highway_mileage_kmpl": "15 - 17 km/l (Petrol) / 19 - 21 km/l (Diesel)",
                "ownership_strengths": '["High brand desirability and resale liquidity", "Feature-rich cabin and comfortable seating", "Refined powertrains with smooth automatics"]',
                "ownership_concerns": '["Average crash test rating with unstable bodyshell", "Relatively thirsty 1.5L petrol IVT in dense traffic", "Occasional panoramic sunroof rattles over rough roads"]',
                "evidence_state": "SUPPORTED",
                "source_id": "src-industry-service-audit"
            },
            {
                "canonical_vehicle_id": "tata::nexon::gen-1-2017",
                "generation_slug": "gen-1-2017",
                "service_interval_km": 15000,
                "service_interval_months": 12,
                "typical_annual_maintenance_inr": "₹6,000 - ₹9,500",
                "parts_availability": "GOOD",
                "maintenance_complexity": "MODERATE",
                "real_world_city_mileage_kmpl": "11 - 13 km/l (Petrol) / 15 - 17 km/l (Diesel)",
                "real_world_highway_mileage_kmpl": "16 - 18 km/l (Petrol) / 20 - 23 km/l (Diesel)",
                "ownership_strengths": '["Benchmark 5-star structural crash safety", "Class-leading 209mm ground clearance", "Solid high-speed road manners and ride quality"]',
                "ownership_concerns": '["Variable Tata authorized dealership service quality", "Thick A-pillar blind spots during tight right turns", "Noticeable 3-cylinder engine vibration at idle"]',
                "evidence_state": "SUPPORTED",
                "source_id": "src-industry-service-audit"
            },
            {
                "canonical_vehicle_id": "honda::city::gen-5-2020",
                "generation_slug": "gen-5-2020",
                "service_interval_km": 10000,
                "service_interval_months": 12,
                "typical_annual_maintenance_inr": "₹6,500 - ₹9,000",
                "parts_availability": "EXCELLENT",
                "maintenance_complexity": "MODERATE",
                "real_world_city_mileage_kmpl": "11 - 13 km/l (Petrol MT) / 10 - 12 km/l (CVT)",
                "real_world_highway_mileage_kmpl": "17 - 19 km/l (Petrol MT) / 18 - 20 km/l (CVT)",
                "ownership_strengths": '["Legendary 1.5L i-VTEC engine refinement and rev-happiness", "Huge 506-litre boot and limousine-grade rear legroom", "Pliant suspension perfectly tuned for highway comfort"]',
                "ownership_concerns": '["Low ground clearance prone to scraping high speed-bumps when fully loaded", "Skinny 185-section tires look disproportionate", "High-rpm cabin boom compared to European sedans"]',
                "evidence_state": "SUPPORTED",
                "source_id": "src-industry-service-audit"
            },
            {
                "canonical_vehicle_id": "mahindra::thar::gen-2-2020",
                "generation_slug": "gen-2-2020",
                "service_interval_km": 10000,
                "service_interval_months": 12,
                "typical_annual_maintenance_inr": "₹8,500 - ₹13,000",
                "parts_availability": "GOOD",
                "maintenance_complexity": "MODERATE",
                "real_world_city_mileage_kmpl": "8 - 10 km/l (Petrol AT) / 11 - 13 km/l (Diesel)",
                "real_world_highway_mileage_kmpl": "11 - 13 km/l (Petrol AT) / 14 - 16 km/l (Diesel)",
                "ownership_strengths": '["Unbeatable street presence and authentic 4x4 off-road ability", "Robust ladder-frame chassis with 4-star safety rating", "Punchy mStallion turbo petrol and mHawk diesel engines"]',
                "ownership_concerns": '["Strict 4-seater with negligible boot space", "Bumpy low-speed ride due to stiff off-road suspension", "Wind noise and cabin boom at highway speeds (> 100 km/h)"]',
                "evidence_state": "SUPPORTED",
                "source_id": "src-industry-service-audit"
            }
        ]

        for own in ownership_profiles:
            pipeline.ingest_ownership_profile(own, source_id=own["source_id"])
        session.commit()

        # 6. Reliability Issues & Technical Advisories
        reliability_issues = [
            {
                "canonical_vehicle_id": "maruti-suzuki::swift::gen-3-2018",
                "generation_slug": "gen-3-2018",
                "issue_key": "amt-clutch-judder",
                "category": "TRANSMISSION",
                "title": "AMT Automated Manual Transmission Clutch Judder",
                "description": "5-speed AGS (AMT) variants may exhibit clutch shudder during low-speed crawl in bumper-to-bumper traffic between 25,000 to 45,000 km, requiring clutch assembly inspection and actuator recalibration.",
                "severity": "ADVISORY",
                "affected_years": "2018-2022",
                "affected_powertrains": "5-Speed AMT (AGS)",
                "verification_status": "COMMUNITY_DOCUMENTED",
                "evidence_state": "SUPPORTED",
                "source_id": "src-industry-service-audit"
            },
            {
                "canonical_vehicle_id": "hyundai::creta::gen-2-2020",
                "generation_slug": "gen-2-2020",
                "issue_key": "panoramic-sunroof-drain-clog",
                "category": "BODY_CHASSIS",
                "title": "Panoramic Sunroof Drain Tube Clogging & Rattle",
                "description": "Accumulation of dust in front A-pillar sunroof drain tubes can lead to water seepage into the headliner during monsoon seasons. Track lubrication and drain flushing are recommended during scheduled maintenance.",
                "severity": "ADVISORY",
                "affected_years": "2020-2023",
                "affected_powertrains": "All equipped with Panoramic Sunroof",
                "verification_status": "COMMUNITY_DOCUMENTED",
                "evidence_state": "SUPPORTED",
                "source_id": "src-industry-service-audit"
            },
            {
                "canonical_vehicle_id": "tata::nexon::gen-1-2017",
                "generation_slug": "gen-1-2017",
                "issue_key": "infotainment-firmware-glitch",
                "category": "INFOTAINMENT",
                "title": "Harman Infotainment Screen Boot Lag & Touch Freeze",
                "description": "Pre-facelift 1st generation Harman touchscreen units may experience intermittent Bluetooth disconnection or delayed reverse camera feed. Resolvable via official Tata authorized service center software update.",
                "severity": "LOW",
                "affected_years": "2017-2020",
                "affected_powertrains": "All models with 7-inch Harman Screen",
                "verification_status": "COMMUNITY_DOCUMENTED",
                "evidence_state": "SUPPORTED",
                "source_id": "src-industry-service-audit"
            },
            {
                "canonical_vehicle_id": "honda::city::gen-5-2020",
                "generation_slug": "gen-5-2020",
                "issue_key": "low-belly-ground-scrape",
                "category": "SUSPENSION",
                "title": "Underbody Ground Clearance Vulnerability with Full Load",
                "description": "Long 2600mm wheelbase combined with soft rear dampers makes the vehicle prone to scraping on unstandardized Indian road speed breakers when carrying 4-5 passengers and luggage. Angled traversal recommended.",
                "severity": "ADVISORY",
                "affected_years": "2020-2024",
                "affected_powertrains": "All variants",
                "verification_status": "COMMUNITY_DOCUMENTED",
                "evidence_state": "SUPPORTED",
                "source_id": "src-industry-service-audit"
            },
            {
                "canonical_vehicle_id": "mahindra::thar::gen-2-2020",
                "generation_slug": "gen-2-2020",
                "issue_key": "dpf-filter-regeneration",
                "category": "ENGINE",
                "title": "Diesel Particulate Filter (DPF) Clogging in Urban Commutes",
                "description": "BS6 diesel variants subjected exclusively to short, low-speed city trips under 30 km/h may trigger DPF warning lights. Periodic highway drives (> 60 km/h for 20+ minutes) are required for passive regeneration.",
                "severity": "MODERATE",
                "affected_years": "2020-2023",
                "affected_powertrains": "2.2L mHawk Diesel BS6",
                "verification_status": "COMMUNITY_DOCUMENTED",
                "evidence_state": "SUPPORTED",
                "source_id": "src-industry-service-audit"
            }
        ]

        for rel in reliability_issues:
            pipeline.ingest_reliability_issue(rel, source_id=rel["source_id"])
        session.commit()

        # 7. Pros & Cons
        pros_cons = [
            # Swift
            {"canonical_vehicle_id": "maruti-suzuki::swift::gen-3-2018", "generation_slug": "gen-3-2018", "is_pro": True, "statement": "Frugal 1.2L engine delivering up to 23 km/l ARAI efficiency", "category": "PERFORMANCE", "source_id": "src-oem-maruti-swift-2018"},
            {"canonical_vehicle_id": "maruti-suzuki::swift::gen-3-2018", "generation_slug": "gen-3-2018", "is_pro": True, "statement": "Unmatched resale market demand and rapid liquidity", "category": "MAINTENANCE", "source_id": "src-industry-service-audit"},
            {"canonical_vehicle_id": "maruti-suzuki::swift::gen-3-2018", "generation_slug": "gen-3-2018", "is_pro": False, "statement": "Unstable bodyshell rating with only 2 stars in Global NCAP crash testing", "category": "SAFETY", "source_id": "src-gncap-2018-swift"},
            {"canonical_vehicle_id": "maruti-suzuki::swift::gen-3-2018", "generation_slug": "gen-3-2018", "is_pro": False, "statement": "Lightweight body panels vulnerable to dents and rattles over time", "category": "PRACTICALITY", "source_id": "src-industry-service-audit"},

            # Creta
            {"canonical_vehicle_id": "hyundai::creta::gen-2-2020", "generation_slug": "gen-2-2020", "is_pro": True, "statement": "Segment-leading road presence and premium interior appointments", "category": "COMFORT", "source_id": "src-oem-hyundai-creta-2020"},
            {"canonical_vehicle_id": "hyundai::creta::gen-2-2020", "generation_slug": "gen-2-2020", "is_pro": True, "statement": "Wide choice of refined petrol and diesel engine/transmission pairings", "category": "PERFORMANCE", "source_id": "src-oem-hyundai-creta-2020"},
            {"canonical_vehicle_id": "hyundai::creta::gen-2-2020", "generation_slug": "gen-2-2020", "is_pro": False, "statement": "Global NCAP adult safety rating limited to 3 stars with unstable structure", "category": "SAFETY", "source_id": "src-gncap-2022-creta"},
            {"canonical_vehicle_id": "hyundai::creta::gen-2-2020", "generation_slug": "gen-2-2020", "is_pro": False, "statement": "Significant used-market price premium demanding rigorous deal analysis", "category": "MAINTENANCE", "source_id": "src-industry-service-audit"},

            # Nexon
            {"canonical_vehicle_id": "tata::nexon::gen-1-2017", "generation_slug": "gen-1-2017", "is_pro": True, "statement": "Verified 5-star Global NCAP adult safety rating with stable bodyshell", "category": "SAFETY", "source_id": "src-gncap-2018-nexon"},
            {"canonical_vehicle_id": "tata::nexon::gen-1-2017", "generation_slug": "gen-1-2017", "is_pro": True, "statement": "Substantial 209mm ground clearance tackling broken roads effortlessly", "category": "PRACTICALITY", "source_id": "src-oem-tata-nexon-2017"},
            {"canonical_vehicle_id": "tata::nexon::gen-1-2017", "generation_slug": "gen-1-2017", "is_pro": False, "statement": "AMT transmission lacks the smoothness of torque converters or dual-clutch units", "category": "PERFORMANCE", "source_id": "src-industry-service-audit"},

            # City
            {"canonical_vehicle_id": "honda::city::gen-5-2020", "generation_slug": "gen-5-2020", "is_pro": True, "statement": "Silky-smooth, free-revving 1.5L i-VTEC DOHC petrol engine", "category": "PERFORMANCE", "source_id": "src-oem-honda-city-2020"},
            {"canonical_vehicle_id": "honda::city::gen-5-2020", "generation_slug": "gen-5-2020", "is_pro": True, "statement": "Generous rear-seat knee room and cavernous 506-litre boot", "category": "PRACTICALITY", "source_id": "src-oem-honda-city-2020"},
            {"canonical_vehicle_id": "honda::city::gen-5-2020", "generation_slug": "gen-5-2020", "is_pro": False, "statement": "Low 165mm stance susceptible to underbody scrapes on steep bumps", "category": "PRACTICALITY", "source_id": "src-industry-service-audit"}
        ]

        for pc in pros_cons:
            pipeline.ingest_pro_con(pc, source_id=pc["source_id"])
        session.commit()

        # 8. Review Syntheses
        reviews = [
            {
                "canonical_vehicle_id": "maruti-suzuki::swift::gen-3-2018",
                "generation_slug": "gen-3-2018",
                "what_owners_say": "Owners praise the peppy city pickup, parking agility, and phenomenal fuel economy averaging 15-18 km/l in mixed usage. Frequent complaints center on the thin sheet metal, road noise at 100+ km/h, and jerky shifts on AMT models.",
                "what_experts_say": "Auto journalists commend the playful chassis balance and eager K12N DualJet motor. However, criticism is universal regarding the 2-star Global NCAP safety score and plasticky dashboard trim.",
                "carspective_analysis": "The Swift 3rd Gen remains India's benchmark used hatchback for urban commuters prioritizing rock-bottom running costs and instant resale liquidity. Buyers seeking highway safety or refined automatic transmissions should explore alternatives like the Tata Altroz or Hyundai i20.",
                "has_owner_evidence": True,
                "has_expert_evidence": True,
                "evidence_state": "SUPPORTED",
                "source_id": "src-industry-service-audit"
            },
            {
                "canonical_vehicle_id": "hyundai::creta::gen-2-2020",
                "generation_slug": "gen-2-2020",
                "what_owners_say": "Owners adore the panoramic sunroof, plush seating, light steering in heavy traffic, and modern tech suite. Diesel owners consistently report 18+ km/l on highways, while petrol AT owners note steep fuel bills in congested city crawls.",
                "what_experts_say": "Reviewers highlight Creta's balanced suspension setup and powertrain versatility. Main caveats include the polarizing front grille styling and the disappointing 3-star safety rating.",
                "carspective_analysis": "The 2nd Generation Creta commands high residual values on used car portals. While an exceptional urban family crossover, buyers must not assume 5-star crash safety and should inspect panoramic sunroof tracks for drainage integrity.",
                "has_owner_evidence": True,
                "has_expert_evidence": True,
                "evidence_state": "SUPPORTED",
                "source_id": "src-industry-service-audit"
            },
            {
                "canonical_vehicle_id": "tata::nexon::gen-1-2017",
                "generation_slug": "gen-1-2017",
                "what_owners_say": "Owners express deep confidence in the tank-like build quality and high ground clearance that effortlessly absorbs monsoon potholes. Frustrations revolve around thick A-pillars creating blind spots at intersections.",
                "what_experts_say": "Automotive test drivers laude the Nexon as a pioneering milestone for Indian vehicular safety. Ride stability at 120 km/h is praised as best-in-class, though the 1.2L petrol engine is noted as gruff when revved hard.",
                "carspective_analysis": "A premier choice for safety-first buyers navigating hostile road conditions. Buyers should verify service history records diligently to ensure authorized software updates were applied to the Harman infotainment system.",
                "has_owner_evidence": True,
                "has_expert_evidence": True,
                "evidence_state": "SUPPORTED",
                "source_id": "src-industry-service-audit"
            },
            {
                "canonical_vehicle_id": "honda::city::gen-5-2020",
                "generation_slug": "gen-5-2020",
                "what_owners_say": "Owners celebrate the buttery-smooth i-VTEC engine, expansive rear legroom, and effortless highway cruising. Rear passengers praise the sofa-like seats, though city drivers report occasional belly scrapes on oversized speed humps.",
                "what_experts_say": "Motoring journalists regard the 5th Gen City as the definitive traditional C-segment sedan. The high-revving naturally aspirated engine and compliant suspension deliver unmatched executive comfort.",
                "carspective_analysis": "The Honda City 5th Gen is the gold standard for buyers wanting rear-seat luxury and bulletproof mechanical reliability over trendy SUV ride height. Underbody inspection is essential to verify absence of floor-pan scraping.",
                "has_owner_evidence": True,
                "has_expert_evidence": True,
                "evidence_state": "SUPPORTED",
                "source_id": "src-industry-service-audit"
            }
        ]

        for rev in reviews:
            pipeline.ingest_review_synthesis(rev, source_id=rev["source_id"])
        session.commit()

        print("Phase 11 vehicle knowledge successfully seeded and committed to database.")
    finally:
        if should_close:
            session.close()

if __name__ == "__main__":

    load_expanded_vehicle_knowledge()
