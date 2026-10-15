"""
CARspective — Data Intelligence & Pipeline REST API Routes (/api/v1/data/*)
Exposes governed sources, deterministic freshness, evidence lineage, data quality scores,
and operator ingestion batch workflows.
"""

from flask import Blueprint, jsonify, request
from server.infrastructure.database import get_db
from server.domain.data_pipeline.service import DataIntelligenceService
from server.domain.data_pipeline.models import SourceType
from server.domain.data_pipeline.freshness import POLICIES
from server.utils.auth import require_admin_auth

data_bp = Blueprint("data_v1", __name__, url_prefix="/api/v1/data")

@data_bp.route("/sources", methods=["GET"])
def list_sources():
    """List governed data sources."""
    status_filter = request.args.get("status", "ACTIVE").upper()
    type_str = request.args.get("type")
    source_type = None
    if type_str:
        try:
            source_type = SourceType(type_str.upper())
        except ValueError:
            pass

    active_only = (status_filter == "ACTIVE")
    db = next(get_db())
    service = DataIntelligenceService(db)
    sources = service.list_sources(active_only=active_only, source_type=source_type)
    return jsonify([s.model_dump() for s in sources]), 200

@data_bp.route("/sources/<source_id>", methods=["GET"])
def get_source(source_id: str):
    """Retrieve governed source metadata and associated freshness policy."""
    db = next(get_db())
    service = DataIntelligenceService(db)
    source = service.get_source(source_id)
    if not source:
        return jsonify({
            "type": "about:blank",
            "title": "Source Not Found",
            "status": 404,
            "detail": f"No governed source matching identifier '{source_id}'."
        }), 404

    policy = POLICIES.get(source.freshness_policy_id)
    resp = source.model_dump()
    resp["freshness_policy"] = policy.model_dump() if policy else None
    return jsonify(resp), 200

@data_bp.route("/evidence/<evidence_id>", methods=["GET"])
def get_evidence_lineage(evidence_id: str):
    """Trace evidence source to linked knowledge claims and vehicles."""
    db = next(get_db())
    service = DataIntelligenceService(db)
    try:
        lineage = service.get_evidence_lineage(evidence_id)
        return jsonify(lineage), 200
    except ValueError as e:
        return jsonify({
            "type": "about:blank",
            "title": "Evidence Source Not Found",
            "status": 404,
            "detail": str(e)
        }), 404

@data_bp.route("/quality", methods=["GET"])
def get_quality():
    """Return current dataset quality score and metric breakdown."""
    db = next(get_db())
    service = DataIntelligenceService(db)
    report = service.get_system_dataset_quality()
    return jsonify(report.model_dump()), 200

@data_bp.route("/freshness", methods=["GET"])
def get_freshness():
    """Return freshness status across major automotive data domains."""
    db = next(get_db())
    service = DataIntelligenceService(db)
    summaries = service.get_domain_freshness()
    return jsonify([s.model_dump() for s in summaries]), 200

@data_bp.route("/lineage/<claim_id>", methods=["GET"])
def get_claim_lineage(claim_id: str):
    """Return end-to-end lineage: SOURCE -> EVIDENCE -> CLAIM -> VEHICLE -> PRODUCT SURFACE."""
    db = next(get_db())
    service = DataIntelligenceService(db)
    lineage = service.get_claim_lineage(claim_id)
    if not lineage:
        return jsonify({
            "type": "about:blank",
            "title": "Knowledge Claim Not Found",
            "status": 404,
            "detail": f"No knowledge claim found matching ID '{claim_id}'."
        }), 404
    return jsonify(lineage.model_dump()), 200

# ==============================================================================
# Admin / Operator Observability & Ingestion Endpoints (Section 15)
# ==============================================================================

@data_bp.route("/admin/batches", methods=["GET"])
@require_admin_auth
def list_batches():
    """List recent ingestion batches with processing status and rejection stats."""
    db = next(get_db())
    service = DataIntelligenceService(db)
    limit = int(request.args.get("limit", 50))
    batches = service.list_batches(limit=limit)
    return jsonify([b.model_dump() for b in batches]), 200

@data_bp.route("/admin/batches/<batch_id>", methods=["GET"])
@require_admin_auth
def get_batch(batch_id: str):
    """Retrieve detailed batch audit record."""
    db = next(get_db())
    service = DataIntelligenceService(db)
    batch = service.get_batch(batch_id)
    if not batch:
        return jsonify({
            "type": "about:blank",
            "title": "Batch Not Found",
            "status": 404,
            "detail": f"No ingestion batch found with ID '{batch_id}'."
        }), 404
    return jsonify(batch.model_dump()), 200

@data_bp.route("/admin/ingest/stage", methods=["POST"])
@require_admin_auth
def stage_batch():
    """
    Stage an ingestion batch: validate, map, and audit without committing to production tables.
    """
    payload = request.get_json(silent=True)
    if not payload or "source_id" not in payload or "records" not in payload:
        return jsonify({
            "type": "about:blank",
            "title": "Invalid Ingestion Request",
            "status": 400,
            "detail": "Request body must contain 'source_id' and a 'records' list."
        }), 400

    source_id = payload["source_id"]
    records = payload["records"]
    snapshot_ref = payload.get("source_snapshot_reference")

    if not isinstance(records, list):
        return jsonify({
            "type": "about:blank",
            "title": "Malformed Records",
            "status": 400,
            "detail": "'records' must be a JSON array of listing dictionaries."
        }), 400

    db = next(get_db())
    service = DataIntelligenceService(db)
    try:
        metadata = service.stage_batch(
            source_id=source_id,
            records=records,
            snapshot_reference=snapshot_ref
        )
        return jsonify(metadata.model_dump()), 201
    except ValueError as e:
        return jsonify({
            "type": "about:blank",
            "title": "Staging Error",
            "status": 400,
            "detail": str(e)
        }), 400

@data_bp.route("/admin/ingest/commit/<batch_id>", methods=["POST"])
@require_admin_auth
def commit_batch(batch_id: str):
    """Atomically commit a previously staged batch."""
    db = next(get_db())
    service = DataIntelligenceService(db)
    try:
        committed = service.commit_batch(batch_id)
        return jsonify(committed.model_dump()), 200
    except ValueError as e:
        return jsonify({
            "type": "about:blank",
            "title": "Commit Precondition Failed",
            "status": 400,
            "detail": str(e)
        }), 400
    except RuntimeError as e:
        return jsonify({
            "type": "about:blank",
            "title": "Commit Transaction Failed (Rolled Back)",
            "status": 500,
            "detail": str(e)
        }), 500

@data_bp.route("/admin/ingest/rollback/<batch_id>", methods=["POST"])
@require_admin_auth
def rollback_batch(batch_id: str):
    """Roll back a staged batch."""
    db = next(get_db())
    service = DataIntelligenceService(db)
    try:
        rolled_back = service.rollback_batch(batch_id)
        return jsonify(rolled_back.model_dump()), 200
    except ValueError as e:
        return jsonify({
            "type": "about:blank",
            "title": "Rollback Failed",
            "status": 404,
            "detail": str(e)
        }), 404
