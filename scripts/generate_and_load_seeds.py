"""
CARspective — Taxonomy & Evidence Seeder
Generates data/taxonomy_seeds/tier1_taxonomy_seed.json and populates the database.
Enforces the 6-tier hierarchy and exact Phase 1.2 evidence states:
VERIFIED, SUPPORTED, EMPIRICAL, MODEL_ESTIMATE, INSUFFICIENT_DATA, UNVERIFIED, DEPRECATED
"""

import json
import hashlib
import sys
from datetime import date
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from server.infrastructure.database import SessionFactory, init_db
from server.models.taxonomy import (
    Manufacturer,
    ManufacturerAlias,
    VehicleModel,
    ModelAlias,
    VehicleGeneration,
    ModelYear,
    VehicleVariant,
    PowertrainConfiguration,
)
from server.models.evidence import (
    EvidenceSource,
    KnowledgeClaim,
    ClaimEvidenceMapping,
    EvidenceState,
    OrganizationType,
    HierarchyLevel,
)
from server.domain.taxonomy.slugifier import slugify

def build_seed_data():
    seed = {
        "metadata": {
            "version": "1.2.0",
            "description": "Empirical Tier 1 High-Volume Indian Vehicle Taxonomy & Evidence Seed",
            "generated_from": "57,480 historical Indian used-car listing records"
        },
        "evidence_sources": [
            {
                "id": "src-gncap-2018-nexon",
                "organization_name": "Global NCAP",
                "organization_type": "SAFETY_AGENCY",
                "source_url": "https://www.globalncap.org/news/tata-nexon-first-five-star-car-for-india",
                "reference_document": "Global NCAP Safer Cars For India 2018 - Tata Nexon",
                "published_at": "2018-12-07",
                "valid_from": "2018-12-07",
                "valid_until": "2023-09-01",
                "verification_status": "VERIFIED",
                "confidence_score": 1.0,
                "payload_hash": hashlib.sha256(b"GNCAP_NEXON_2018_5STAR_REPORT").hexdigest()
            },
            {
                "id": "src-gncap-2022-creta",
                "organization_name": "Global NCAP",
                "organization_type": "SAFETY_AGENCY",
                "source_url": "https://www.globalncap.org/news/hyundai-creta-three-stars",
                "reference_document": "Global NCAP Safer Cars For India 2022 - Hyundai Creta",
                "published_at": "2022-04-12",
                "valid_from": "2020-03-01",
                "valid_until": "2024-01-15",
                "verification_status": "VERIFIED",
                "confidence_score": 1.0,
                "payload_hash": hashlib.sha256(b"GNCAP_CRETA_2022_3STAR_REPORT").hexdigest()
            },
            {
                "id": "src-gncap-2018-swift",
                "organization_name": "Global NCAP",
                "organization_type": "SAFETY_AGENCY",
                "source_url": "https://www.globalncap.org/news/maruti-suzuki-swift-two-stars",
                "reference_document": "Global NCAP Safer Cars For India 2018 - Maruti Suzuki Swift",
                "published_at": "2018-10-10",
                "valid_from": "2018-02-01",
                "valid_until": "2024-05-01",
                "verification_status": "VERIFIED",
                "confidence_score": 1.0,
                "payload_hash": hashlib.sha256(b"GNCAP_SWIFT_2018_2STAR_REPORT").hexdigest()
            },
            {
                "id": "src-gncap-2020-thar",
                "organization_name": "Global NCAP",
                "organization_type": "SAFETY_AGENCY",
                "source_url": "https://www.globalncap.org/news/mahindra-thar-four-stars",
                "reference_document": "Global NCAP Safer Cars For India 2020 - Mahindra Thar",
                "published_at": "2020-11-25",
                "valid_from": "2020-10-01",
                "valid_until": "2025-12-31",
                "verification_status": "VERIFIED",
                "confidence_score": 1.0,
                "payload_hash": hashlib.sha256(b"GNCAP_THAR_2020_4STAR_REPORT").hexdigest()
            },
            {
                "id": "src-empirical-listings-57480",
                "organization_name": "CARspective Research Engine",
                "organization_type": "EMPIRICAL_DATASET",
                "source_url": "data/raw/indian_used_cars_raw_57480.csv",
                "reference_document": "57,480 Historical Indian Used-Car Listing Records",
                "published_at": "2026-09-01",
                "valid_from": "2015-01-01",
                "valid_until": "2026-12-31",
                "verification_status": "EMPIRICAL",
                "confidence_score": 0.95,
                "payload_hash": hashlib.sha256(b"57480_HISTORICAL_LISTING_BASELINE_2026").hexdigest()
            }
        ],
        "manufacturers": [
            {
                "name": "Maruti Suzuki",
                "slug": "maruti-suzuki",
                "country_of_origin": "India / Japan",
                "aliases": ["Maruti", "Maruti-Suzuki", "MSIL", "Suzuki"],
                "models": [
                    {
                        "name": "Swift",
                        "slug": "swift",
                        "body_type": "Hatchback",
                        "segment": "B",
                        "coverage_tier": "TIER_1_DEEP",
                        "aliases": ["Maruti Swift", "Swift Hatchback"],
                        "generations": [
                            {
                                "name": "2nd Generation",
                                "slug": "gen-2-2011",
                                "year_start": 2011,
                                "year_end": 2018,
                                "is_facelift": False,
                                "years": [2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018],
                                "variants": [
                                    {
                                        "name": "VXi",
                                        "slug": "vxi",
                                        "trim_level": "Mid",
                                        "powertrains": [
                                            {"fuel_type": "Petrol", "transmission_type": "Manual", "displacement_cc": 1197, "power_bhp": 84.0, "slug": "1-2-petrol-5mt"}
                                        ]
                                    },
                                    {
                                        "name": "VDi",
                                        "slug": "vdi",
                                        "trim_level": "Mid",
                                        "powertrains": [
                                            {"fuel_type": "Diesel", "transmission_type": "Manual", "displacement_cc": 1248, "power_bhp": 74.0, "slug": "1-3-ddis-5mt"}
                                        ]
                                    }
                                ]
                            },
                            {
                                "name": "3rd Generation",
                                "slug": "gen-3-2018",
                                "year_start": 2018,
                                "year_end": 2024,
                                "is_facelift": False,
                                "years": [2018, 2019, 2020, 2021, 2022, 2023, 2024],
                                "variants": [
                                    {
                                        "name": "VXi",
                                        "slug": "vxi",
                                        "trim_level": "Mid",
                                        "powertrains": [
                                            {"fuel_type": "Petrol", "transmission_type": "Manual", "displacement_cc": 1197, "power_bhp": 88.5, "slug": "1-2-dualjet-5mt"},
                                            {"fuel_type": "Petrol", "transmission_type": "Automatic (AMT)", "displacement_cc": 1197, "power_bhp": 88.5, "slug": "1-2-dualjet-5amt"}
                                        ]
                                    },
                                    {
                                        "name": "ZXi",
                                        "slug": "zxi",
                                        "trim_level": "High",
                                        "powertrains": [
                                            {"fuel_type": "Petrol", "transmission_type": "Manual", "displacement_cc": 1197, "power_bhp": 88.5, "slug": "1-2-dualjet-5mt"},
                                            {"fuel_type": "Petrol", "transmission_type": "Automatic (AMT)", "displacement_cc": 1197, "power_bhp": 88.5, "slug": "1-2-dualjet-5amt"}
                                        ]
                                    },
                                    {
                                        "name": "ZXi Plus",
                                        "slug": "zxi-plus",
                                        "trim_level": "Top",
                                        "powertrains": [
                                            {"fuel_type": "Petrol", "transmission_type": "Manual", "displacement_cc": 1197, "power_bhp": 88.5, "slug": "1-2-dualjet-5mt"},
                                            {"fuel_type": "Petrol", "transmission_type": "Automatic (AMT)", "displacement_cc": 1197, "power_bhp": 88.5, "slug": "1-2-dualjet-5amt"}
                                        ]
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "name": "Baleno",
                        "slug": "baleno",
                        "body_type": "Hatchback",
                        "segment": "Premium Hatchback",
                        "coverage_tier": "TIER_1_DEEP",
                        "aliases": ["Maruti Baleno", "Baleno Nexa"],
                        "generations": [
                            {
                                "name": "1st Gen Nexa Baleno",
                                "slug": "gen-1-2015",
                                "year_start": 2015,
                                "year_end": 2022,
                                "is_facelift": False,
                                "years": [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022],
                                "variants": [
                                    {
                                        "name": "Delta",
                                        "slug": "delta",
                                        "trim_level": "Mid",
                                        "powertrains": [
                                            {"fuel_type": "Petrol", "transmission_type": "Manual", "displacement_cc": 1197, "power_bhp": 83.0, "slug": "1-2-k12-5mt"},
                                            {"fuel_type": "Petrol", "transmission_type": "Automatic (CVT)", "displacement_cc": 1197, "power_bhp": 83.0, "slug": "1-2-k12-cvt"}
                                        ]
                                    },
                                    {
                                        "name": "Zeta",
                                        "slug": "zeta",
                                        "trim_level": "High",
                                        "powertrains": [
                                            {"fuel_type": "Petrol", "transmission_type": "Manual", "displacement_cc": 1197, "power_bhp": 83.0, "slug": "1-2-k12-5mt"},
                                            {"fuel_type": "Petrol", "transmission_type": "Automatic (CVT)", "displacement_cc": 1197, "power_bhp": 83.0, "slug": "1-2-k12-cvt"}
                                        ]
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "name": "Wagon R",
                        "slug": "wagon-r",
                        "body_type": "Hatchback",
                        "segment": "Tallboy Hatchback",
                        "coverage_tier": "TIER_1_DEEP",
                        "aliases": ["Maruti Wagon R", "WagonR"],
                        "generations": [
                            {
                                "name": "3rd Generation",
                                "slug": "gen-3-2019",
                                "year_start": 2019,
                                "year_end": None,
                                "is_facelift": False,
                                "years": [2019, 2020, 2021, 2022, 2023, 2024, 2025],
                                "variants": [
                                    {
                                        "name": "LXi",
                                        "slug": "lxi",
                                        "trim_level": "Base",
                                        "powertrains": [
                                            {"fuel_type": "Petrol", "transmission_type": "Manual", "displacement_cc": 998, "power_bhp": 67.0, "slug": "1-0-k10-5mt"},
                                            {"fuel_type": "CNG", "transmission_type": "Manual", "displacement_cc": 998, "power_bhp": 58.0, "slug": "1-0-cng-5mt"}
                                        ]
                                    },
                                    {
                                        "name": "VXi",
                                        "slug": "vxi",
                                        "trim_level": "Mid",
                                        "powertrains": [
                                            {"fuel_type": "Petrol", "transmission_type": "Manual", "displacement_cc": 1197, "power_bhp": 81.0, "slug": "1-2-k12-5mt"},
                                            {"fuel_type": "Petrol", "transmission_type": "Automatic (AMT)", "displacement_cc": 1197, "power_bhp": 81.0, "slug": "1-2-k12-5amt"}
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                ]
            },
            {
                "name": "Hyundai",
                "slug": "hyundai",
                "country_of_origin": "South Korea",
                "aliases": ["Hyundai Motors", "HMIL"],
                "models": [
                    {
                        "name": "Creta",
                        "slug": "creta",
                        "body_type": "SUV",
                        "segment": "Mid-Size SUV",
                        "coverage_tier": "TIER_1_DEEP",
                        "aliases": ["Hyundai Creta"],
                        "generations": [
                            {
                                "name": "1st Generation",
                                "slug": "gen-1-2015",
                                "year_start": 2015,
                                "year_end": 2020,
                                "is_facelift": False,
                                "years": [2015, 2016, 2017, 2018, 2019, 2020],
                                "variants": [
                                    {
                                        "name": "SX",
                                        "slug": "sx",
                                        "trim_level": "High",
                                        "powertrains": [
                                            {"fuel_type": "Petrol", "transmission_type": "Manual", "displacement_cc": 1591, "power_bhp": 121.0, "slug": "1-6-vtvt-6mt"},
                                            {"fuel_type": "Diesel", "transmission_type": "Manual", "displacement_cc": 1582, "power_bhp": 126.0, "slug": "1-6-crdi-6mt"},
                                            {"fuel_type": "Diesel", "transmission_type": "Automatic", "displacement_cc": 1582, "power_bhp": 126.0, "slug": "1-6-crdi-6at"}
                                        ]
                                    }
                                ]
                            },
                            {
                                "name": "2nd Generation Pre-Facelift",
                                "slug": "gen-2-2020",
                                "year_start": 2020,
                                "year_end": 2024,
                                "is_facelift": False,
                                "years": [2020, 2021, 2022, 2023, 2024],
                                "variants": [
                                    {
                                        "name": "SX",
                                        "slug": "sx",
                                        "trim_level": "High",
                                        "powertrains": [
                                            {"fuel_type": "Petrol", "transmission_type": "Manual", "displacement_cc": 1497, "power_bhp": 113.4, "slug": "1-5-mp-6mt"},
                                            {"fuel_type": "Diesel", "transmission_type": "Manual", "displacement_cc": 1493, "power_bhp": 113.4, "slug": "1-5-crdi-6mt"}
                                        ]
                                    },
                                    {
                                        "name": "SX (O)",
                                        "slug": "sx-opt",
                                        "trim_level": "Top",
                                        "powertrains": [
                                            {"fuel_type": "Petrol", "transmission_type": "Automatic (CVT)", "displacement_cc": 1497, "power_bhp": 113.4, "slug": "1-5-mp-ivt"},
                                            {"fuel_type": "Diesel", "transmission_type": "Automatic", "displacement_cc": 1493, "power_bhp": 113.4, "slug": "1-5-crdi-6at"},
                                            {"fuel_type": "Petrol", "transmission_type": "Automatic (DCT)", "displacement_cc": 1353, "power_bhp": 138.0, "slug": "1-4-turbo-7dct"}
                                        ]
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "name": "i20",
                        "slug": "i20",
                        "body_type": "Hatchback",
                        "segment": "Premium Hatchback",
                        "coverage_tier": "TIER_1_DEEP",
                        "aliases": ["Hyundai i20", "Elite i20"],
                        "generations": [
                            {
                                "name": "Elite i20 (2nd Gen)",
                                "slug": "gen-2-2014",
                                "year_start": 2014,
                                "year_end": 2020,
                                "is_facelift": False,
                                "years": [2014, 2015, 2016, 2017, 2018, 2019, 2020],
                                "variants": [
                                    {
                                        "name": "Sportz",
                                        "slug": "sportz",
                                        "trim_level": "Mid",
                                        "powertrains": [
                                            {"fuel_type": "Petrol", "transmission_type": "Manual", "displacement_cc": 1197, "power_bhp": 82.0, "slug": "1-2-kappa-5mt"},
                                            {"fuel_type": "Diesel", "transmission_type": "Manual", "displacement_cc": 1396, "power_bhp": 89.0, "slug": "1-4-crdi-6mt"}
                                        ]
                                    },
                                    {
                                        "name": "Asta",
                                        "slug": "asta",
                                        "trim_level": "Top",
                                        "powertrains": [
                                            {"fuel_type": "Petrol", "transmission_type": "Manual", "displacement_cc": 1197, "power_bhp": 82.0, "slug": "1-2-kappa-5mt"}
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                ]
            },
            {
                "name": "Tata",
                "slug": "tata",
                "country_of_origin": "India",
                "aliases": ["Tata Motors"],
                "models": [
                    {
                        "name": "Nexon",
                        "slug": "nexon",
                        "body_type": "SUV",
                        "segment": "Compact SUV",
                        "coverage_tier": "TIER_1_DEEP",
                        "aliases": ["Tata Nexon"],
                        "generations": [
                            {
                                "name": "1st Generation",
                                "slug": "gen-1-2017",
                                "year_start": 2017,
                                "year_end": 2023,
                                "is_facelift": False,
                                "years": [2017, 2018, 2019, 2020, 2021, 2022, 2023],
                                "variants": [
                                    {
                                        "name": "XM",
                                        "slug": "xm",
                                        "trim_level": "Mid",
                                        "powertrains": [
                                            {"fuel_type": "Petrol", "transmission_type": "Manual", "displacement_cc": 1199, "power_bhp": 118.0, "slug": "1-2-revotron-6mt"},
                                            {"fuel_type": "Diesel", "transmission_type": "Manual", "displacement_cc": 1497, "power_bhp": 108.0, "slug": "1-5-revotorq-6mt"}
                                        ]
                                    },
                                    {
                                        "name": "XZ Plus",
                                        "slug": "xz-plus",
                                        "trim_level": "Top",
                                        "powertrains": [
                                            {"fuel_type": "Petrol", "transmission_type": "Manual", "displacement_cc": 1199, "power_bhp": 118.0, "slug": "1-2-revotron-6mt"},
                                            {"fuel_type": "Petrol", "transmission_type": "Automatic (AMT)", "displacement_cc": 1199, "power_bhp": 118.0, "slug": "1-2-revotron-6amt"},
                                            {"fuel_type": "Diesel", "transmission_type": "Manual", "displacement_cc": 1497, "power_bhp": 108.0, "slug": "1-5-revotorq-6mt"}
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                ]
            },
            {
                "name": "Mahindra",
                "slug": "mahindra",
                "country_of_origin": "India",
                "aliases": ["M&M", "Mahindra & Mahindra"],
                "models": [
                    {
                        "name": "Thar",
                        "slug": "thar",
                        "body_type": "SUV",
                        "segment": "Lifestyle 4x4",
                        "coverage_tier": "TIER_1_DEEP",
                        "aliases": ["Mahindra Thar", "Thar 4x4"],
                        "generations": [
                            {
                                "name": "2nd Generation",
                                "slug": "gen-2-2020",
                                "year_start": 2020,
                                "year_end": None,
                                "is_facelift": False,
                                "years": [2020, 2021, 2022, 2023, 2024, 2025],
                                "variants": [
                                    {
                                        "name": "AX (O)",
                                        "slug": "ax-opt",
                                        "trim_level": "Mid",
                                        "powertrains": [
                                            {"fuel_type": "Diesel", "transmission_type": "Manual", "displacement_cc": 2184, "power_bhp": 130.0, "slug": "2-2-mhawk-6mt"}
                                        ]
                                    },
                                    {
                                        "name": "LX",
                                        "slug": "lx",
                                        "trim_level": "Top",
                                        "powertrains": [
                                            {"fuel_type": "Petrol", "transmission_type": "Manual", "displacement_cc": 1997, "power_bhp": 150.0, "slug": "2-0-mstallion-6mt"},
                                            {"fuel_type": "Petrol", "transmission_type": "Automatic", "displacement_cc": 1997, "power_bhp": 150.0, "slug": "2-0-mstallion-6at"},
                                            {"fuel_type": "Diesel", "transmission_type": "Manual", "displacement_cc": 2184, "power_bhp": 130.0, "slug": "2-2-mhawk-6mt"},
                                            {"fuel_type": "Diesel", "transmission_type": "Automatic", "displacement_cc": 2184, "power_bhp": 130.0, "slug": "2-2-mhawk-6at"}
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                ]
            },
            {
                "name": "Honda",
                "slug": "honda",
                "country_of_origin": "Japan",
                "aliases": ["Honda Cars India", "HCIL"],
                "models": [
                    {
                        "name": "City",
                        "slug": "city",
                        "body_type": "Sedan",
                        "segment": "Mid-Size Sedan",
                        "coverage_tier": "TIER_1_DEEP",
                        "aliases": ["Honda City"],
                        "generations": [
                            {
                                "name": "4th Generation",
                                "slug": "gen-4-2014",
                                "year_start": 2014,
                                "year_end": 2020,
                                "is_facelift": False,
                                "years": [2014, 2015, 2016, 2017, 2018, 2019, 2020],
                                "variants": [
                                    {
                                        "name": "V",
                                        "slug": "v",
                                        "trim_level": "Mid",
                                        "powertrains": [
                                            {"fuel_type": "Petrol", "transmission_type": "Manual", "displacement_cc": 1497, "power_bhp": 117.3, "slug": "1-5-ivtec-5mt"}
                                        ]
                                    },
                                    {
                                        "name": "VX",
                                        "slug": "vx",
                                        "trim_level": "High",
                                        "powertrains": [
                                            {"fuel_type": "Petrol", "transmission_type": "Manual", "displacement_cc": 1497, "power_bhp": 117.3, "slug": "1-5-ivtec-5mt"},
                                            {"fuel_type": "Petrol", "transmission_type": "Automatic (CVT)", "displacement_cc": 1497, "power_bhp": 117.3, "slug": "1-5-ivtec-cvt"}
                                        ]
                                    }
                                ]
                            },
                            {
                                "name": "5th Generation",
                                "slug": "gen-5-2020",
                                "year_start": 2020,
                                "year_end": None,
                                "is_facelift": False,
                                "years": [2020, 2021, 2022, 2023, 2024, 2025],
                                "variants": [
                                    {
                                        "name": "ZX",
                                        "slug": "zx",
                                        "trim_level": "Top",
                                        "powertrains": [
                                            {"fuel_type": "Petrol", "transmission_type": "Manual", "displacement_cc": 1498, "power_bhp": 119.3, "slug": "1-5-ivtec-6mt"},
                                            {"fuel_type": "Petrol", "transmission_type": "Automatic (CVT)", "displacement_cc": 1498, "power_bhp": 119.3, "slug": "1-5-ivtec-cvt"},
                                            {"fuel_type": "Diesel", "transmission_type": "Manual", "displacement_cc": 1498, "power_bhp": 98.6, "slug": "1-5-idtec-6mt"}
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                ]
            },
            {
                "name": "Toyota",
                "slug": "toyota",
                "country_of_origin": "Japan",
                "aliases": ["Toyota Kirloskar", "TKML"],
                "models": [
                    {
                        "name": "Innova Crysta",
                        "slug": "innova-crysta",
                        "body_type": "MUV",
                        "segment": "Premium MPV",
                        "coverage_tier": "TIER_1_DEEP",
                        "aliases": ["Toyota Innova Crysta", "Crysta"],
                        "generations": [
                            {
                                "name": "1st Gen Crysta",
                                "slug": "gen-1-2016",
                                "year_start": 2016,
                                "year_end": None,
                                "is_facelift": False,
                                "years": [2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024],
                                "variants": [
                                    {
                                        "name": "GX",
                                        "slug": "gx",
                                        "trim_level": "Entry",
                                        "powertrains": [
                                            {"fuel_type": "Diesel", "transmission_type": "Manual", "displacement_cc": 2393, "power_bhp": 148.0, "slug": "2-4-d4d-5mt"},
                                            {"fuel_type": "Diesel", "transmission_type": "Automatic", "displacement_cc": 2755, "power_bhp": 172.0, "slug": "2-8-d4d-6at"}
                                        ]
                                    },
                                    {
                                        "name": "ZX",
                                        "slug": "zx",
                                        "trim_level": "Top",
                                        "powertrains": [
                                            {"fuel_type": "Diesel", "transmission_type": "Automatic", "displacement_cc": 2755, "power_bhp": 172.0, "slug": "2-8-d4d-6at"}
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                ]
            },
            {
                "name": "Kia",
                "slug": "kia",
                "country_of_origin": "South Korea",
                "aliases": ["Kia Motors", "Kia India"],
                "models": [
                    {
                        "name": "Seltos",
                        "slug": "seltos",
                        "body_type": "SUV",
                        "segment": "Mid-Size SUV",
                        "coverage_tier": "TIER_1_DEEP",
                        "aliases": ["Kia Seltos"],
                        "generations": [
                            {
                                "name": "1st Generation",
                                "slug": "gen-1-2019",
                                "year_start": 2019,
                                "year_end": 2023,
                                "is_facelift": False,
                                "years": [2019, 2020, 2021, 2022, 2023],
                                "variants": [
                                    {
                                        "name": "HTX",
                                        "slug": "htx",
                                        "trim_level": "High Tech Line",
                                        "powertrains": [
                                            {"fuel_type": "Petrol", "transmission_type": "Manual", "displacement_cc": 1497, "power_bhp": 113.4, "slug": "1-5-smartstream-6mt"},
                                            {"fuel_type": "Diesel", "transmission_type": "Manual", "displacement_cc": 1493, "power_bhp": 113.4, "slug": "1-5-crdi-6mt"}
                                        ]
                                    },
                                    {
                                        "name": "GTX Plus",
                                        "slug": "gtx-plus",
                                        "trim_level": "Top GT Line",
                                        "powertrains": [
                                            {"fuel_type": "Petrol", "transmission_type": "Automatic (DCT)", "displacement_cc": 1353, "power_bhp": 138.0, "slug": "1-4-t-gdi-7dct"},
                                            {"fuel_type": "Diesel", "transmission_type": "Automatic", "displacement_cc": 1493, "power_bhp": 113.4, "slug": "1-5-crdi-6at"}
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ],
        "knowledge_claims": [
            {
                "canonical_vehicle_id": "tata::nexon::gen-1-2017",
                "hierarchy_level": "GENERATION",
                "attribute_category": "SAFETY",
                "attribute_key": "adult_occupant_crash_rating",
                "claim_value": "5 Stars (Global NCAP)",
                "evidence_state": "VERIFIED",
                "source_id": "src-gncap-2018-nexon",
                "verification_notes": "First Indian-manufactured vehicle to achieve 5-star adult occupant rating."
            },
            {
                "canonical_vehicle_id": "hyundai::creta::gen-2-2020",
                "hierarchy_level": "GENERATION",
                "attribute_category": "SAFETY",
                "attribute_key": "adult_occupant_crash_rating",
                "claim_value": "3 Stars (Global NCAP)",
                "evidence_state": "VERIFIED",
                "source_id": "src-gncap-2022-creta",
                "verification_notes": "Global NCAP 2022 test result for Creta 2nd gen Indian specification."
            },
            {
                "canonical_vehicle_id": "maruti-suzuki::swift::gen-3-2018",
                "hierarchy_level": "GENERATION",
                "attribute_category": "SAFETY",
                "attribute_key": "adult_occupant_crash_rating",
                "claim_value": "2 Stars (Global NCAP)",
                "evidence_state": "VERIFIED",
                "source_id": "src-gncap-2018-swift",
                "verification_notes": "Global NCAP 2018 test report for Maruti Suzuki Swift 3rd generation."
            },
            {
                "canonical_vehicle_id": "mahindra::thar::gen-2-2020",
                "hierarchy_level": "GENERATION",
                "attribute_category": "SAFETY",
                "attribute_key": "adult_occupant_crash_rating",
                "claim_value": "4 Stars (Global NCAP)",
                "evidence_state": "VERIFIED",
                "source_id": "src-gncap-2020-thar",
                "verification_notes": "Global NCAP 2020 rating for Mahindra Thar 2nd Gen."
            },
            {
                "canonical_vehicle_id": "maruti-suzuki::swift",
                "hierarchy_level": "MODEL",
                "attribute_category": "RESALE",
                "attribute_key": "historical_listing_volume_rank",
                "claim_value": "Rank 1 (2,314 normalized listings, 4.03% total market share)",
                "evidence_state": "EMPIRICAL",
                "source_id": "src-empirical-listings-57480",
                "verification_notes": "Highest volume used vehicle model in the 57,480-record listing baseline."
            },
            {
                "canonical_vehicle_id": "hyundai::creta",
                "hierarchy_level": "MODEL",
                "attribute_category": "RESALE",
                "attribute_key": "historical_listing_volume_rank",
                "claim_value": "Rank 2 (1,777 normalized listings, 3.09% total market share)",
                "evidence_state": "EMPIRICAL",
                "source_id": "src-empirical-listings-57480",
                "verification_notes": "Second highest volume model and highest volume SUV in the 57,480 listing baseline."
            }
        ]
    }
    return seed

def load_seed_to_database(seed: dict):
    init_db()
    session = SessionFactory()
    try:
        # 1. Sources
        source_map = {}
        for s in seed["evidence_sources"]:
            src_obj = session.get(EvidenceSource, s["id"])
            if not src_obj:
                src_obj = EvidenceSource(
                    id=s["id"],
                    organization_name=s["organization_name"],
                    organization_type=OrganizationType(s["organization_type"]),
                    source_url=s.get("source_url"),
                    reference_document=s.get("reference_document"),
                    published_at=date.fromisoformat(s["published_at"]) if s.get("published_at") else None,
                    valid_from=date.fromisoformat(s["valid_from"]) if s.get("valid_from") else None,
                    valid_until=date.fromisoformat(s["valid_until"]) if s.get("valid_until") else None,
                    verification_status=EvidenceState(s["verification_status"]),
                    confidence_score=s["confidence_score"],
                    payload_hash=s["payload_hash"]
                )
                session.add(src_obj)
            source_map[s["id"]] = src_obj
        session.commit()

        # 2. Manufacturers & Hierarchy
        for m_data in seed["manufacturers"]:
            # Check manufacturer
            m_obj = session.query(Manufacturer).filter_by(slug=m_data["slug"]).first()
            if not m_obj:
                m_obj = Manufacturer(
                    name=m_data["name"],
                    slug=m_data["slug"],
                    country_of_origin=m_data.get("country_of_origin"),
                    is_active=True
                )
                session.add(m_obj)
                session.flush()

            # Aliases
            for alias_str in m_data.get("aliases", []):
                alias_clean = alias_str.strip()
                if not session.query(ManufacturerAlias).filter_by(alias=alias_clean).first():
                    session.add(ManufacturerAlias(manufacturer_id=m_obj.id, alias=alias_clean))

            # Models
            for mod_data in m_data.get("models", []):
                mod_obj = session.query(VehicleModel).filter_by(
                    manufacturer_id=m_obj.id,
                    slug=mod_data["slug"]
                ).first()
                if not mod_obj:
                    mod_obj = VehicleModel(
                        manufacturer_id=m_obj.id,
                        name=mod_data["name"],
                        slug=mod_data["slug"],
                        body_type=mod_data["body_type"],
                        segment=mod_data.get("segment"),
                        coverage_tier=mod_data.get("coverage_tier", "TIER_1_DEEP"),
                        is_active=True
                    )
                    session.add(mod_obj)
                    session.flush()

                for ma_str in mod_data.get("aliases", []):
                    ma_clean = ma_str.strip()
                    if not session.query(ModelAlias).filter_by(model_id=mod_obj.id, alias=ma_clean).first():
                        session.add(ModelAlias(model_id=mod_obj.id, alias=ma_clean))

                # Generations
                for gen_data in mod_data.get("generations", []):
                    gen_obj = session.query(VehicleGeneration).filter_by(
                        model_id=mod_obj.id,
                        slug=gen_data["slug"]
                    ).first()
                    if not gen_obj:
                        gen_obj = VehicleGeneration(
                            model_id=mod_obj.id,
                            name=gen_data["name"],
                            slug=gen_data["slug"],
                            year_start=gen_data["year_start"],
                            year_end=gen_data.get("year_end"),
                            is_facelift=gen_data.get("is_facelift", False)
                        )
                        session.add(gen_obj)
                        session.flush()

                    # Model Years
                    for yr in gen_data.get("years", []):
                        if not session.query(ModelYear).filter_by(generation_id=gen_obj.id, calendar_year=yr).first():
                            session.add(ModelYear(generation_id=gen_obj.id, calendar_year=yr))

                    # Variants
                    for var_data in gen_data.get("variants", []):
                        var_obj = session.query(VehicleVariant).filter_by(
                            generation_id=gen_obj.id,
                            slug=var_data["slug"]
                        ).first()
                        if not var_obj:
                            var_obj = VehicleVariant(
                                generation_id=gen_obj.id,
                                name=var_data["name"],
                                slug=var_data["slug"],
                                trim_level=var_data.get("trim_level")
                            )
                            session.add(var_obj)
                            session.flush()

                        # Powertrains
                        for pt_data in var_data.get("powertrains", []):
                            pt_slug = pt_data.get("slug") or f"{slugify(pt_data['fuel_type'])}-{slugify(pt_data['transmission_type'])}"
                            pt_obj = session.query(PowertrainConfiguration).filter_by(
                                variant_id=var_obj.id,
                                slug=pt_slug
                            ).first()
                            if not pt_obj:
                                pt_obj = PowertrainConfiguration(
                                    variant_id=var_obj.id,
                                    engine_name=pt_data.get("engine_name"),
                                    displacement_cc=pt_data.get("displacement_cc"),
                                    fuel_type=pt_data["fuel_type"],
                                    transmission_type=pt_data["transmission_type"],
                                    power_bhp=pt_data.get("power_bhp"),
                                    torque_nm=pt_data.get("torque_nm"),
                                    arai_mileage_kmpl=pt_data.get("arai_mileage_kmpl"),
                                    slug=pt_slug
                                )
                                session.add(pt_obj)

        session.commit()

        # 3. Knowledge Claims
        for c_data in seed.get("knowledge_claims", []):
            claim = session.query(KnowledgeClaim).filter_by(
                canonical_vehicle_id=c_data["canonical_vehicle_id"],
                attribute_key=c_data["attribute_key"]
            ).first()
            if not claim:
                claim = KnowledgeClaim(
                    canonical_vehicle_id=c_data["canonical_vehicle_id"],
                    hierarchy_level=HierarchyLevel(c_data["hierarchy_level"]),
                    attribute_category=c_data["attribute_category"],
                    attribute_key=c_data["attribute_key"],
                    claim_value=c_data["claim_value"],
                    evidence_state=EvidenceState(c_data["evidence_state"]),
                    verification_notes=c_data.get("verification_notes")
                )
                session.add(claim)
                session.flush()

                if c_data.get("source_id"):
                    session.add(ClaimEvidenceMapping(
                        claim_id=claim.id,
                        source_id=c_data["source_id"],
                        citation_note=c_data.get("verification_notes")
                    ))
        session.commit()
        print("Database seed successfully loaded.")
    finally:
        session.close()

if __name__ == "__main__":
    out_dir = Path("data/taxonomy_seeds")
    out_dir.mkdir(parents=True, exist_ok=True)
    seed_json = out_dir / "tier1_taxonomy_seed.json"
    
    data = build_seed_data()
    with open(seed_json, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Seed manifest saved to: {seed_json}")
    
    load_seed_to_database(data)
