"""
CARspective — Taxonomy REST API Blueprints (/api/v1/vehicles/*)
Pydantic v2 request and response serialization with RFC 7807 structured errors.
"""

from flask import Blueprint, request, jsonify
from pydantic import ValidationError
from server.infrastructure.database import get_db
from server.domain.taxonomy.service import TaxonomyService
from server.domain.evidence.service import EvidenceService
from server.domain.knowledge.service import KnowledgeService
from server.domain.discovery.service import DiscoverySearchService
from server.domain.discovery.models import DiscoveryFilterParams
from server.domain.workspace.service import VehicleWorkspaceService
from server.schemas.taxonomy import CanonicalResolutionRequest

taxonomy_bp = Blueprint("taxonomy_v1", __name__, url_prefix="/api/v1/vehicles")

def error_response(status_code: int, title: str, detail: str):
    return jsonify({
        "type": "about:blank",
        "title": title,
        "status": status_code,
        "detail": detail
    }), status_code

# 0. Intelligent Vehicle Discovery & Search Endpoints (Phase 12)
@taxonomy_bp.route("/search", methods=["GET"])
def search_vehicles():
    db = next(get_db())
    discovery_service = DiscoverySearchService(db)

    q = request.args.get("q", "")
    brand = request.args.get("brand") or request.args.get("make") or request.args.get("manufacturer")
    model = request.args.get("model")
    year = request.args.get("year", type=int)
    generation = request.args.get("generation")
    variant = request.args.get("variant")
    fuel = request.args.get("fuel_type") or request.args.get("fuel")
    transmission = request.args.get("transmission_type") or request.args.get("transmission")
    body_type = request.args.get("body_type")
    budget_min = request.args.get("budget_min", type=float)
    budget_max = request.args.get("budget_max", type=float)
    seating_capacity = request.args.get("seating_capacity", type=int)
    limit = request.args.get("limit", default=20, type=int)
    offset = request.args.get("offset", default=0, type=int)
    fmt = request.args.get("format", "standard")

    params = DiscoveryFilterParams(
        q=q,
        manufacturer=brand,
        model=model,
        year=year,
        generation=generation,
        variant=variant,
        fuel_type=fuel,
        transmission=transmission,
        body_type=body_type,
        budget_min=budget_min,
        budget_max=budget_max,
        seating_capacity=seating_capacity,
        limit=limit,
        offset=offset
    )

    response = discovery_service.search(params)

    if fmt == "legacy":
        legacy_results = [
            {
                "canonical_id": c.canonical_vehicle_id,
                "canonical_vehicle_id": c.canonical_vehicle_id,
                "title": c.title,
                "make": c.manufacturer,
                "model": c.model,
                "generation": c.generation,
                "year": c.model_year,
                "variant": c.variant or "Standard",
                "fuel_type": c.fuel_type or "Petrol",
                "transmission": c.transmission or "Manual",
                "body_type": c.body_type or "Hatchback",
                "coverage_tier": c.coverage_tier,
                "match_score": c.match_score
            }
            for c in response.results
        ]
        return jsonify(legacy_results), 200

    return jsonify(response.model_dump()), 200

@taxonomy_bp.route("/autocomplete", methods=["GET"])
def autocomplete_vehicles():
    db = next(get_db())
    discovery_service = DiscoverySearchService(db)
    q = request.args.get("q", "")
    limit = request.args.get("limit", default=8, type=int)
    res = discovery_service.autocomplete(query=q, limit=limit)
    return jsonify(res.model_dump()), 200

# 1. Manufacturer & Canonical Vehicle Profile Endpoints
@taxonomy_bp.route("/manufacturers", methods=["GET"])
def list_manufacturers():
    db = next(get_db())
    service = TaxonomyService(db)
    items = service.list_manufacturers()
    return jsonify([i.model_dump() for i in items]), 200

@taxonomy_bp.route("/profile/<path:canonical_id>", methods=["GET"])
def get_vehicle_profile_explicit(canonical_id: str):
    db = next(get_db())
    knowledge_service = KnowledgeService(db)
    profile = knowledge_service.get_vehicle_profile(canonical_id)
    if not profile:
        return error_response(404, "Vehicle Profile Not Found", f"No verified vehicle profile matching canonical ID '{canonical_id}'.")
    return jsonify(profile.model_dump()), 200

@taxonomy_bp.route("/<make_slug>", methods=["GET"])
def get_manufacturer(make_slug: str):
    db = next(get_db())
    # If a full canonical vehicle ID is supplied (e.g. make::model::gen), route to vehicle profile
    if "::" in make_slug:
        knowledge_service = KnowledgeService(db)
        profile = knowledge_service.get_vehicle_profile(make_slug)
        if not profile:
            return error_response(404, "Vehicle Profile Not Found", f"No vehicle profile matching canonical ID '{make_slug}'.")
        return jsonify(profile.model_dump()), 200

    service = TaxonomyService(db)
    m = service.get_manufacturer(make_slug)
    if not m:
        return error_response(404, "Manufacturer Not Found", f"No manufacturer matching slug '{make_slug}'.")
    return jsonify(m.model_dump()), 200

# 2. Model Endpoints
@taxonomy_bp.route("/<make_slug>/models", methods=["GET"])
def list_models(make_slug: str):
    db = next(get_db())
    service = TaxonomyService(db)
    m = service.get_manufacturer(make_slug)
    if not m:
        return error_response(404, "Manufacturer Not Found", f"No manufacturer matching slug '{make_slug}'.")
    models = service.list_models_by_manufacturer(make_slug)
    return jsonify([mod.model_dump() for mod in models]), 200

@taxonomy_bp.route("/<make_slug>/<model_slug>", methods=["GET"])
def get_model(make_slug: str, model_slug: str):
    db = next(get_db())
    service = TaxonomyService(db)
    mod = service.get_model(make_slug, model_slug)
    if not mod:
        return error_response(404, "Model Not Found", f"No model matching '{model_slug}' under manufacturer '{make_slug}'.")
    return jsonify(mod.model_dump()), 200

# 3. Generation & Hierarchy Endpoints
@taxonomy_bp.route("/<make_slug>/<model_slug>/generations", methods=["GET"])
def list_generations(make_slug: str, model_slug: str):
    db = next(get_db())
    service = TaxonomyService(db)
    mod = service.get_model(make_slug, model_slug)
    if not mod:
        return error_response(404, "Model Not Found", f"No model matching '{model_slug}' under manufacturer '{make_slug}'.")
    return jsonify([g.model_dump() for g in mod.generations]), 200

@taxonomy_bp.route("/<make_slug>/<model_slug>/<gen_slug>/variants", methods=["GET"])
def list_variants(make_slug: str, model_slug: str, gen_slug: str):
    db = next(get_db())
    service = TaxonomyService(db)
    mod = service.get_model(make_slug, model_slug)
    if not mod:
        return error_response(404, "Model Not Found", f"No model matching '{model_slug}'.")
    gen = next((g for g in mod.generations if g.slug == gen_slug), None)
    if not gen:
        return error_response(404, "Generation Not Found", f"No generation matching '{gen_slug}'.")
    return jsonify([v.model_dump() for v in gen.variants]), 200

# 4. Canonical Resolution Endpoints
@taxonomy_bp.route("/resolve", methods=["GET", "POST"])
def resolve_vehicle():
    db = next(get_db())
    service = TaxonomyService(db)
    
    if request.method == "POST":
        payload = request.get_json(silent=True) or {}
    else:
        payload = {
            "brand": request.args.get("brand", ""),
            "model": request.args.get("model", ""),
            "year": request.args.get("year", type=int),
            "variant": request.args.get("variant"),
            "fuel_type": request.args.get("fuel_type") or request.args.get("fuel"),
            "transmission_type": request.args.get("transmission_type") or request.args.get("transmission"),
        }

    try:
        req_schema = CanonicalResolutionRequest(**payload)
    except ValidationError as e:
        return jsonify({
            "type": "about:blank",
            "title": "Validation Error",
            "status": 422,
            "detail": "Request payload failed validation schema.",
            "errors": e.errors()
        }), 422

    res = service.resolve_vehicle(req_schema)
    return jsonify(res.model_dump()), 200

# 5. Provenance & Evidence Lookup for Vehicle
@taxonomy_bp.route("/provenance/<path:canonical_id>", methods=["GET"])
@taxonomy_bp.route("/<path:canonical_id>/evidence", methods=["GET"])
def get_vehicle_provenance(canonical_id: str):
    db = next(get_db())
    evidence_service = EvidenceService(db)
    category = request.args.get("category")
    prov = evidence_service.get_provenance_for_vehicle(canonical_id, category=category)
    return jsonify(prov.model_dump()), 200

# 6. Detailed Knowledge Sub-Resource Endpoints
@taxonomy_bp.route("/<path:canonical_id>/specifications", methods=["GET"])
def get_vehicle_specifications(canonical_id: str):
    db = next(get_db())
    knowledge_service = KnowledgeService(db)
    profile = knowledge_service.get_vehicle_profile(canonical_id)
    if not profile:
        return error_response(404, "Vehicle Not Found", f"No verified vehicle profile matching '{canonical_id}'.")
    return jsonify({
        "canonical_vehicle_id": canonical_id,
        "specifications": profile.specifications.model_dump() if profile.specifications else None,
        "dimensions": profile.dimensions.model_dump() if profile.dimensions else None,
    }), 200

@taxonomy_bp.route("/<path:canonical_id>/safety", methods=["GET"])
def get_vehicle_safety(canonical_id: str):
    db = next(get_db())
    knowledge_service = KnowledgeService(db)
    profile = knowledge_service.get_vehicle_profile(canonical_id)
    if not profile:
        return error_response(404, "Vehicle Not Found", f"No verified vehicle profile matching '{canonical_id}'.")
    return jsonify({
        "canonical_vehicle_id": canonical_id,
        "safety": profile.safety.model_dump() if profile.safety else None,
    }), 200

@taxonomy_bp.route("/<path:canonical_id>/features", methods=["GET"])
def get_vehicle_features(canonical_id: str):
    db = next(get_db())
    knowledge_service = KnowledgeService(db)
    profile = knowledge_service.get_vehicle_profile(canonical_id)
    if not profile:
        return error_response(404, "Vehicle Not Found", f"No verified vehicle profile matching '{canonical_id}'.")
    return jsonify({
        "canonical_vehicle_id": canonical_id,
        "features": [f.model_dump() for f in profile.features],
    }), 200

@taxonomy_bp.route("/<path:canonical_id>/ownership", methods=["GET"])
def get_vehicle_ownership(canonical_id: str):
    db = next(get_db())
    knowledge_service = KnowledgeService(db)
    profile = knowledge_service.get_vehicle_profile(canonical_id)
    if not profile:
        return error_response(404, "Vehicle Not Found", f"No verified vehicle profile matching '{canonical_id}'.")
    return jsonify({
        "canonical_vehicle_id": canonical_id,
        "ownership": profile.ownership.model_dump() if profile.ownership else None,
        "reliability_issues": [iss.model_dump() for iss in profile.reliability_issues],
        "pros": [p.model_dump() for p in profile.pros],
        "cons": [c.model_dump() for c in profile.cons],
        "reviews": profile.reviews.model_dump() if profile.reviews else None,
    }), 200

# 7. Unified Vehicle Intelligence Workspace Endpoint (Phase 13)
@taxonomy_bp.route("/workspace/<path:canonical_id>", methods=["GET"])
def get_vehicle_workspace(canonical_id: str):
    db = next(get_db())
    workspace_service = VehicleWorkspaceService(session=db)
    asking_price = request.args.get("asking_price", type=float)
    km_driven = request.args.get("km_driven", type=float)

    workspace = workspace_service.get_vehicle_workspace(
        canonical_id,
        asking_price=asking_price,
        km_driven=km_driven,
    )
    if not workspace:
        return error_response(404, "Vehicle Not Found", f"No verified vehicle taxonomy matching '{canonical_id}'.")
    return jsonify(workspace.model_dump()), 200

