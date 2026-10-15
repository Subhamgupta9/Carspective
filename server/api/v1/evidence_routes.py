"""
CARspective — Evidence & Provenance REST API Blueprints (/api/v1/evidence/*)
"""

from flask import Blueprint, jsonify
from server.infrastructure.database import get_db
from server.domain.evidence.service import EvidenceService

evidence_bp = Blueprint("evidence_v1", __name__, url_prefix="/api/v1/evidence")

@evidence_bp.route("/sources", methods=["GET"])
def list_sources():
    db = next(get_db())
    service = EvidenceService(db)
    sources = service.list_sources()
    return jsonify([s.model_dump() for s in sources]), 200

@evidence_bp.route("/sources/<source_id>", methods=["GET"])
def get_source(source_id: str):
    db = next(get_db())
    service = EvidenceService(db)
    source = service.repo.get_source(source_id)
    if not source:
        return jsonify({
            "type": "about:blank",
            "title": "Evidence Source Not Found",
            "status": 404,
            "detail": f"No source record matching ID '{source_id}'."
        }), 404
    from server.schemas.evidence import EvidenceSourceSchema
    return jsonify(EvidenceSourceSchema.model_validate(source).model_dump()), 200
