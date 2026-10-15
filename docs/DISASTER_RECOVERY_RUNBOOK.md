# CARSPECTIVE — DISASTER RECOVERY & BACKUP RUNBOOK
## Phase 19F Operational Standard Operating Procedure (SOP)

**System:** CarSpective Intelligent Automotive Intelligence Platform  
**Target Environment:** Production WSGI / Docker / Multi-Database (SQLite & PostgreSQL)  
**Current Baseline Database:** `data/database/carspective.db`  
**Current Head Migration:** Alembic `f3d730c46a23`  
**Primary Valuation Model:** `models/carspective_valuation_lgbm_v1.joblib`  
**Authoritative Model SHA-256:** `4a4ccf3f78c17b48826cfa55f40a24bcb808bc82fa752b793ad4eabff8b246c1`  

---

## 1. OBJECTIVES, RPO & RTO METRICS

| Metric | Target | Rationale |
|---|---|---|
| **Recovery Point Objective (RPO) — Static Catalog & Taxonomy** | **24 hours** | Vehicle catalog, generations, variants, and dimensions are reference data updated on structured release cadences. Daily snapshots satisfy zero-data-loss thresholds for reference data. |
| **Recovery Point Objective (RPO) — Market Observations & Ingestion** | **1 hour** | Live market ingestion occurs in discrete batches. In the event of catastrophic storage failure, hourly automated online backups limit lost observation data to $< 1$ batch cycle. |
| **Recovery Time Objective (RTO) — SQLite (Container / Single Node)** | **$< 15$ minutes** | Automated restore script validates cryptographic checksums, checks foreign keys and schema integrity, performs atomic substitution, and restores traffic within 15 minutes. |
| **Recovery Time Objective (RTO) — PostgreSQL (Managed / Cloud DB)** | **$< 60$ minutes** | Full cluster / table-level restoration via `pg_restore` with WAL replay, connection pool draining, and Alembic version verification within 60 minutes. |

---

## 2. REPOSITORY & STORAGE ARTIFACT TOPOLOGY

### A. Live Relational Storage
- **Path:** `data/database/carspective.db`
- **Schema:** 25 tables governed strictly by Alembic revision `f3d730c46a23`.
- **Integrity Requirement:** `PRAGMA foreign_keys = ON;`, `PRAGMA integrity_check` $\to$ `ok`.

### B. Protected Baseline Historical Snapshots (NEVER MUTATE OR PRUNE)
- **Phase 19C Safety Baseline:** `data/database/carspective.db.phase19c_safety_backup`  
  *SHA-256:* `fe9d013cee0d9e16bbd1453aaa6bcf0cf6b966a42c5da818ab75e8db2c7d47cf`  
  *Row Count:* 984 market observations, 25 tables.
- **Phase 19D Pre-Cleanup Snapshot:** `data/database/carspective.db.pre_cleanup_snapshot_20261009_191728`  
  *SHA-256:* `c6d8093a413dde469363b377ef92d76c31fca60d0eeed148c86b036a136c31a6`  
  *Purpose:* Forensic record of uncleaned test batches before controlled cleanup.

### C. Valuation Model Artifacts
- **Primary Model:** `models/carspective_valuation_lgbm_v1.joblib` (Size: 2.74 MB, SHA-256: `4a4ccf...`)
- **Companion Manifest:** `models/carspective_valuation_lgbm_v1_manifest.json`

---

## 3. SQLITE BACKUP PROCEDURES

CarSpective provides an automated, consistent backup utility using SQLite's native online backup API (`Connection.backup()`). This guarantees clean, non-blocking snapshots without locking concurrent writers or holding WAL readers.

### A. Standard Online Backup Execution
```bash
# Execute online backup with companion cryptographic manifest
python scripts/backup_database.py \
  --db-path data/database/carspective.db \
  --output-dir backups \
  --retention-count 7
```

### B. What the Backup Utility Does
1. **Online Snapshot:** Opens the source database in URI read-only mode (`mode=ro`) and copies data into a temporary staging file via `src_conn.backup(dest_conn)`.
2. **Deep Integrity Inspection:** Executes `PRAGMA integrity_check` and `PRAGMA foreign_key_check` on the backup file before declaring it valid.
3. **Table & Schema Inventory:** Computes row counts across all 25 tables and extracts the current Alembic revision.
4. **Companion Cryptographic Manifest:** Generates `<backup_file>.manifest.json` containing:
   - ISO-8601 UTC timestamp
   - SHA-256 checksum of the backup file
   - File size in bytes
   - Current Alembic revision
   - Table-by-table row count dictionary
   - Integrity and foreign key verification flags
5. **Deterministic Retention Pruning:** Retains the newest $N$ (default 7) backups. Protected historical snapshots (`*.phase19c_safety_backup*`, `*.pre_cleanup_snapshot*`) and the single newest valid backup are strictly protected and never deleted.

### C. Verifying an Existing Backup
```bash
python scripts/backup_database.py --verify backups/carspective_backup_20261009_153000.db --json
```

---

## 4. SQLITE RESTORE PROCEDURES

The restore utility enforces fail-closed verification before mutating any destination files.

### A. Non-Destructive Inspection / Dry-Run (`--verify-only`)
Before restoring, always inspect and verify the candidate backup without modifying any files:
```bash
python scripts/restore_database.py \
  --backup-path backups/carspective_backup_20261009_153000.db \
  --verify-only
```
*Validates:*
- Backup file existence and readability.
- Companion manifest existence and JSON integrity.
- Byte-for-byte SHA-256 checksum equality between file and manifest.
- SQLite `PRAGMA integrity_check` $\to$ `ok`.
- SQLite `PRAGMA foreign_key_check` $\to$ zero violations.
- Row counts in the backup exactly match the recorded manifest.
- Alembic revision matches the manifest.

### B. Safe Restore to Non-Live Destination
To restore data into an isolated test or validation database:
```bash
python scripts/restore_database.py \
  --backup-path backups/carspective_backup_20261009_153000.db \
  --target-db-path data/database/carspective_staging.db
```

### C. Overwriting the Live Database (`--confirm-overwrite-live`)
Overwriting an existing database (especially `data/database/carspective.db`) requires explicit confirmation:
```bash
# 1. Drain incoming write traffic / stop web service
docker stop carspective-prod

# 2. Execute verified live restore with safety pre-restore backup
python scripts/restore_database.py \
  --backup-path backups/carspective_backup_20261009_153000.db \
  --target-db-path data/database/carspective.db \
  --confirm-overwrite-live \
  --verify-model

# 3. Restart web service
docker start carspective-prod

# 4. Verify system readiness probe
curl -f http://127.0.0.1:5001/health/readiness
```

**Safety Guarantees during Live Restore:**
1. **Pre-Restore Safety Snapshot:** An exact byte-for-byte snapshot of the live database (`carspective.db.pre_restore_backup_<timestamp>.db`) is automatically created and verified before any files are modified.
2. **Atomic Swap:** Restoration is performed into a temporary staging file (`.tmp_restore_*`), verified, and swapped atomically via `os.replace` to prevent partial or corrupted state.
3. **Automatic Rollback:** If post-replacement integrity or foreign-key checks fail, the utility automatically rolls back to the pre-restore safety snapshot.
4. **Protected Target Rejection:** If the target matches `*.phase19c_safety_backup*`, `*.pre_cleanup_snapshot*`, or `models/*` (via direct name, relative traversal, or hardlink), the restore aborts immediately.

### D. Cryptographic Boundary & Threat Model Note
> [!IMPORTANT]
> **Integrity vs. Authentication:**  
> The companion manifest uses SHA-256 to guarantee data integrity against accidental file corruption, bit rot, network transmission errors, and partial writes. However, **SHA-256 alone does not authenticate a backup against an attacker with write access to the filesystem**, because an adversary capable of overwriting the `.db` file can also recompute the SHA-256 and overwrite the companion `.manifest.json`. For high-threat environments, manifests should be stored on read-only object storage (WORM) or cryptographically signed with asymmetric keys (e.g., GPG or Ed25519).

---

## 5. WAL CHECKPOINTING & STORAGE SYNCHRONIZATION

When CarSpective runs with SQLite in Write-Ahead Log (`WAL`) mode:
1. Active transactions write changes into `carspective.db-wal` alongside the main database file.
2. SQLite `Connection.backup()` automatically merges WAL frames during the backup operation.
3. Before manual file-system backups or container volume snapshots, force a checkpoint:
   ```bash
   python -c "import sqlite3; conn = sqlite3.connect('data/database/carspective.db'); conn.execute('PRAGMA wal_checkpoint(TRUNCATE);'); conn.close()"
   ```
4. During live restore, stale `-wal` and `-shm` companion files are cleanly removed to prevent transaction replay collisions.

---

## 6. POSTGRESQL BACKUP & RESTORE PROCEDURES (DOCUMENTATION ONLY)

> [!NOTE]
> **Implementation Scope & Status:**  
> PostgreSQL backup and recovery is a **DOCUMENTED OPERATIONAL PROCEDURE ONLY**. It is **not** implemented as an automated Python CLI tool in `scripts/`, nor has it been executed or tested against a running PostgreSQL daemon in the local environment (which strictly runs SQLite single-file storage).

### A. Prerequisites for PostgreSQL Operations
1. **Tooling:** Native PostgreSQL client binaries (`pg_dump`, `pg_restore`, `psql`) matching the server major version must be installed on the host or inside the administration container.
2. **Network & Access:** TCP connectivity to the database host (default port 5432) with a valid `DATABASE_URL` connection string.
3. **Database Privileges:** The database user must possess `SELECT` on all tables, sequences, and schemas for backup, and `CREATE`, `DROP`, `ALTER` for restore.

### B. Logical Backup (`pg_dump`)
```bash
# Export consistent compressed archive with custom format
pg_dump \
  --dbname="${DATABASE_URL}" \
  --format=custom \
  --compress=9 \
  --file="backups/carspective_pg_backup_$(date +%Y%m%d_%H%M%S).dump"
```

### C. Point-in-Time Recovery / Full Restore (`pg_restore`)
```bash
# 1. Terminate active backend connections to release locks
psql "${DATABASE_URL}" -c "
  SELECT pg_terminate_backend(pid) 
  FROM pg_stat_activity 
  WHERE datname = current_database() AND pid <> pg_backend_pid();
"

# 2. Restore schema and data cleanly
pg_restore \
  --dbname="${DATABASE_URL}" \
  --clean \
  --if-exists \
  --no-owner \
  --no-privileges \
  "backups/carspective_pg_backup_<timestamp>.dump"

# 3. Verify Alembic migration head
python -m alembic current
# Expected output: f3d730c46a23 (head)
```

### D. Known Failure Conditions & Remediation
- **Connection Lockout (`cannot drop table while referenced by other connections`):** Occurs if web workers are active. Remediate by draining/stopping web containers before restore and terminating backends.
- **Client/Server Version Incompatibility (`pg_dump: server version: 16.x; pg_dump version: 15.x`):** `pg_dump` version must be greater than or equal to the target PostgreSQL server version.
- **Ownership / Permission Errors (`must be owner of relation`):** Restoring with `--no-owner` and `--no-privileges` prevents failures when restoring into databases where roles differ from the original database.

## 7. VALUATION MODEL ARTIFACT RECOVERY

The primary valuation engine relies on `models/carspective_valuation_lgbm_v1.joblib`. If the model is corrupted or deleted:
1. The readiness probe (`GET /health/readiness`) immediately reports `503 Service Unavailable`:
   ```json
   {
     "status": "NOT_READY",
     "checks": {
       "valuation_model": "UNAVAILABLE"
     }
   }
   ```
2. Verify model artifact integrity:
   ```bash
   python scripts/backup_database.py --verify-model
   ```
3. If corrupted, restore the model from cold object storage or artifact repository:
   ```bash
   # Verify recovered model SHA-256 against manifest
   python -c "
   import hashlib, json
   with open('models/carspective_valuation_lgbm_v1_manifest.json') as f:
       expected = json.load(f)['artifact']['sha256']
   with open('models/carspective_valuation_lgbm_v1.joblib', 'rb') as f:
       actual = hashlib.sha256(f.read()).hexdigest()
   assert actual == expected == '4a4ccf3f78c17b48826cfa55f40a24bcb808bc82fa752b793ad4eabff8b246c1'
   print('MODEL INTEGRITY VERIFIED')
   "
   ```

---

## 8. ROLLBACK DECISION MATRIX

```
                       INCIDENT DETECTED
                               │
               Is database schema corrupted?
                 ┌─────────────┴─────────────┐
                YES                          NO
                 │                           │
     Did release introduce DDL?      Is issue purely code?
       ┌─────────┴─────────┐                 │
      YES                  NO               YES
       │                   │                 │
 Downgrade Alembic    Restore verified   Roll back container
 revision via:        backup with:       image to previous
 `alembic downgrade`  `restore_database` Git release tag
```

| Incident Category | Severity | Primary Remediation | Recovery Tool |
|---|:---:|---|---|
| **P1: Catastrophic Database Corruption** | Critical | Full restore from latest verified backup | `scripts/restore_database.py --confirm-overwrite-live` |
| **P1: Service Outage (Process Crash)** | Critical | Restart container / check logs | `docker restart carspective-prod` |
| **P2: Failed Ingestion Batch Corruption** | High | Restore from pre-ingestion snapshot or delete isolated batch | Batch deletion API or DB restore |
| **P2: Valuation Model Hash Mismatch** | High | Restore `.joblib` from cold storage | Verify with `--verify-model` |
| **P3: Backup Checksum Failure** | Medium | Re-run online backup; inspect disk health | `scripts/backup_database.py` |
| **P3: Code Regression (No Schema Change)**| Medium | Roll back application container tag | Docker image rollback |

---

## 9. INCIDENT ESCALATION & CONTACTS

- **Incident Commander:** Platform Lead
- **Escalation Path:**
  1. **Level 1 (Detection):** Alert triggered via `/health/readiness` (503) or `/metrics` error rate spike ($> 1\%$).
  2. **Level 2 (Triage):** On-call engineer inspects logs (`docker logs --tail 200 carspective-prod`).
  3. **Level 3 (Mitigation):** Initiate Disaster Recovery SOP section corresponding to incident category.
  4. **Level 4 (Post-Mortem):** Verify post-restore table counts, verify Alembic revision `f3d730c46a23`, and archive incident report.
