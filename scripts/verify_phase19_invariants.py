#!/usr/bin/env python3
"""
CARspective — Phase 19/20 Invariants & Protected Baseline Verification Utility
Verifies that all protected database assets, historical backups, model weights,
and schema invariants match authoritative baseline values bit-for-bit.
"""

import hashlib
import json
import sqlite3
import sys
from pathlib import Path

# Authoritative Expected Values
EXPECTED_LIVE_DB_SHA256 = "cb655c06225c07af98a85a1171595d3c0d368db4e270c3170d57f96a874209e9"
EXPECTED_19C_BACKUP_SHA256 = "fe9d013cee0d9e16bbd1453aaa6bcf0cf6b966a42c5da818ab75e8db2c7d47cf"
EXPECTED_PRE_CLEANUP_SHA256 = "c6d8093a413dde469363b377ef92d76c31fca60d0eeed148c86b036a136c31a6"
EXPECTED_MODEL_SHA256 = "4a4ccf3f78c17b48826cfa55f40a24bcb808bc82fa752b793ad4eabff8b246c1"
EXPECTED_ALEMBIC_REVISION = "f3d730c46a23"
EXPECTED_TABLE_COUNT = 25
EXPECTED_CMO_ROW_COUNT = 984
EXPECTED_CMO_BATCHES = 41
EXPECTED_INGESTION_BATCHES = 29
EXPECTED_INGESTION_RECORDS = 29
EXPECTED_DQR_ROWS = 0
EXPECTED_MANUFACTURERS = 7
EXPECTED_CATALOG_VERSION = "2.0.0"
EXPECTED_CATALOG_ITEMS = 49

def compute_sha256(filepath: Path) -> str:
    if not filepath.is_file():
        raise FileNotFoundError(f"File not found: {filepath}")
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()

def verify_invariants() -> bool:
    all_passed = True
    print("=" * 70)
    print("CARSPECTIVE PHASE 19/20 BASELINE INVARIANT VERIFICATION")
    print("=" * 70)

    # 1. File Hash Verifications
    files_to_check = [
        ("Live Database", Path("data/database/carspective.db"), EXPECTED_LIVE_DB_SHA256),
        ("Phase 19C Safety Backup", Path("data/database/carspective.db.phase19c_safety_backup"), EXPECTED_19C_BACKUP_SHA256),
        ("Pre-Cleanup Snapshot", Path("data/database/carspective.db.pre_cleanup_snapshot_20261009_191728"), EXPECTED_PRE_CLEANUP_SHA256),
        ("Valuation Model", Path("models/carspective_valuation_lgbm_v1.joblib"), EXPECTED_MODEL_SHA256),
    ]

    for label, path, expected_hash in files_to_check:
        try:
            actual_hash = compute_sha256(path)
            if actual_hash.lower() == expected_hash.lower():
                print(f"[PASS] {label}: {actual_hash[:16]}... (Exact Match)")
            else:
                print(f"[FAIL] {label}: Expected {expected_hash}, got {actual_hash}")
                all_passed = False
        except Exception as e:
            print(f"[FAIL] {label}: Error - {e}")
            all_passed = False

    # 2. SQLite Database Integrity & Invariants
    live_db = Path("data/database/carspective.db")
    try:
        uri = f"file:{live_db.resolve().as_posix()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=10.0)
        cur = conn.cursor()

        # PRAGMA integrity_check
        integrity = cur.execute("PRAGMA integrity_check;").fetchall()
        if integrity == [("ok",)]:
            print("[PASS] SQLite PRAGMA integrity_check: ok")
        else:
            print(f"[FAIL] SQLite PRAGMA integrity_check: {integrity}")
            all_passed = False

        # PRAGMA foreign_key_check
        fk_violations = cur.execute("PRAGMA foreign_key_check;").fetchall()
        if not fk_violations:
            print("[PASS] SQLite PRAGMA foreign_key_check: 0 violations")
        else:
            print(f"[FAIL] SQLite PRAGMA foreign_key_check: {fk_violations}")
            all_passed = False

        # Tables inventory
        tables = [
            r[0]
            for r in cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;"
            ).fetchall()
        ]
        if len(tables) == EXPECTED_TABLE_COUNT:
            print(f"[PASS] Table count: {len(tables)} tables")
        else:
            print(f"[FAIL] Table count: Expected {EXPECTED_TABLE_COUNT}, got {len(tables)}")
            all_passed = False

        # Table rows
        cmo_count = cur.execute("SELECT COUNT(*) FROM current_market_observations;").fetchone()[0]
        if cmo_count == EXPECTED_CMO_ROW_COUNT:
            print(f"[PASS] Current Market Observations: {cmo_count} rows")
        else:
            print(f"[FAIL] CMO Count: Expected {EXPECTED_CMO_ROW_COUNT}, got {cmo_count}")
            all_passed = False

        cmo_batches = cur.execute("SELECT COUNT(DISTINCT ingestion_batch_id) FROM current_market_observations;").fetchone()[0]
        if cmo_batches == EXPECTED_CMO_BATCHES:
            print(f"[PASS] CMO Distinct Batches: {cmo_batches} batches")
        else:
            print(f"[FAIL] CMO Distinct Batches: Expected {EXPECTED_CMO_BATCHES}, got {cmo_batches}")
            all_passed = False

        ingest_batches = cur.execute("SELECT COUNT(*) FROM ingestion_batches;").fetchone()[0]
        if ingest_batches == EXPECTED_INGESTION_BATCHES:
            print(f"[PASS] Ingestion Batches: {ingest_batches} rows")
        else:
            print(f"[FAIL] Ingestion Batches: Expected {EXPECTED_INGESTION_BATCHES}, got {ingest_batches}")
            all_passed = False

        ingest_records = cur.execute("SELECT COUNT(*) FROM ingestion_records;").fetchone()[0]
        if ingest_records == EXPECTED_INGESTION_RECORDS:
            print(f"[PASS] Ingestion Records: {ingest_records} rows")
        else:
            print(f"[FAIL] Ingestion Records: Expected {EXPECTED_INGESTION_RECORDS}, got {ingest_records}")
            all_passed = False

        dqr_count = cur.execute("SELECT COUNT(*) FROM data_quality_reports;").fetchone()[0]
        if dqr_count == EXPECTED_DQR_ROWS:
            print(f"[PASS] Data Quality Reports: {dqr_count} rows")
        else:
            print(f"[FAIL] DQR Count: Expected {EXPECTED_DQR_ROWS}, got {dqr_count}")
            all_passed = False

        mfg_count = cur.execute("SELECT COUNT(*) FROM manufacturers;").fetchone()[0]
        if mfg_count == EXPECTED_MANUFACTURERS:
            print(f"[PASS] Manufacturers: {mfg_count} rows")
        else:
            print(f"[FAIL] Manufacturers: Expected {EXPECTED_MANUFACTURERS}, got {mfg_count}")
            all_passed = False

        alem_rev = cur.execute("SELECT version_num FROM alembic_version;").fetchone()[0]
        if alem_rev == EXPECTED_ALEMBIC_REVISION:
            print(f"[PASS] Alembic Revision: {alem_rev}")
        else:
            print(f"[FAIL] Alembic Revision: Expected {EXPECTED_ALEMBIC_REVISION}, got {alem_rev}")
            all_passed = False

        conn.close()
    except Exception as e:
        print(f"[FAIL] Database checks failed with exception: {e}")
        all_passed = False

    # 3. Canonical Inspection Catalog Invariant
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from server.domain.inspection.checklist import (
            INSPECTION_CATALOG_VERSION,
            CANONICAL_CHECKLIST_CATALOG,
        )
        if INSPECTION_CATALOG_VERSION == EXPECTED_CATALOG_VERSION:
            print(f"[PASS] Inspection Catalog Version: {INSPECTION_CATALOG_VERSION}")
        else:
            print(f"[FAIL] Inspection Catalog Version: Expected {EXPECTED_CATALOG_VERSION}, got {INSPECTION_CATALOG_VERSION}")
            all_passed = False

        if len(CANONICAL_CHECKLIST_CATALOG) == EXPECTED_CATALOG_ITEMS:
            print(f"[PASS] Inspection Catalog Items: {len(CANONICAL_CHECKLIST_CATALOG)} items")
        else:
            print(f"[FAIL] Inspection Catalog Items: Expected {EXPECTED_CATALOG_ITEMS}, got {len(CANONICAL_CHECKLIST_CATALOG)}")
            all_passed = False
    except Exception as e:
        print(f"[FAIL] Inspection Catalog check failed: {e}")
        all_passed = False

    print("=" * 70)
    if all_passed:
        print("RESULT: ALL INVARIANTS VERIFIED SUCCESSFULLY (PASS)")
    else:
        print("RESULT: ONE OR MORE INVARIANTS FAILED")
    print("=" * 70)
    return all_passed

if __name__ == "__main__":
    success = verify_invariants()
    sys.exit(0 if success else 1)
