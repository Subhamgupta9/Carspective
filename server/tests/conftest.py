"""
CARspective — Server Pytest Fixtures
In-memory SQLite database and test client fixtures.
"""

import os
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.engine import Engine
from server.models.base import Base
from server.app import create_app
from server.infrastructure.database import ScopedSession
from server.config.settings import normalize_database_url
from scripts.generate_and_load_seeds import build_seed_data, load_seed_to_database


def is_live_database_url(url: str) -> bool:
    """Detect whether a database URL targets the known live production/development SQLite database."""
    if not url:
        return False
    normalized = url.lower().replace("\\", "/")
    return "data/database/carspective.db" in normalized or normalized.endswith("/carspective.db") or "carspective.db" in normalized


@pytest.fixture(scope="session")
def test_engine():
    """
    Create test database engine.
    - Defaults to in-memory SQLite ('sqlite:///:memory:') when TEST_DATABASE_URL is unset.
    - Binds to explicitly configured TEST_DATABASE_URL when set (e.g. ephemeral PostgreSQL in CI).
    - Strictly rejects any test URL pointing to the live application database (carspective.db).
    - Configures dialect-specific settings: SQLite PRAGMA and check_same_thread are never attached to PostgreSQL.
    """
    raw_url = os.getenv("TEST_DATABASE_URL")
    if not raw_url or not raw_url.strip():
        db_url = "sqlite:///:memory:"
    else:
        trimmed = raw_url.strip()
        if is_live_database_url(trimmed):
            raise ValueError(
                f"Unsafe test configuration: TEST_DATABASE_URL ({trimmed}) targets the live database (carspective.db)! "
                "Tests must never run against the live application database."
            )
        db_url = normalize_database_url(trimmed)

    is_sqlite = db_url.startswith("sqlite")

    if is_sqlite:
        engine = create_engine(
            db_url,
            connect_args={"check_same_thread": False},
            future=True,
        )

        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    else:
        # Non-SQLite / PostgreSQL
        engine = create_engine(
            db_url,
            pool_pre_ping=True,
            future=True,
        )

    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(test_engine):
    """Provide a transactional database session for each test function with dialect-appropriate cleanup."""
    connection = test_engine.connect()
    transaction = connection.begin()
    
    SessionLocal = sessionmaker(bind=connection, autocommit=False, autoflush=False, future=True)
    session = SessionLocal()

    # Load initial seed data into test session (skip if database is already seeded)
    from server.models.taxonomy import Manufacturer
    already_seeded = False
    try:
        already_seeded = session.query(Manufacturer).first() is not None
    except Exception:
        already_seeded = False

    if not already_seeded:
        seed = build_seed_data()
        from server.models.evidence import EvidenceSource, OrganizationType, EvidenceState, KnowledgeClaim, HierarchyLevel, ClaimEvidenceMapping
        from server.models.taxonomy import ManufacturerAlias, VehicleModel, ModelAlias, VehicleGeneration, ModelYear, VehicleVariant, PowertrainConfiguration
        from datetime import date

        for s in seed["evidence_sources"]:
            session.add(EvidenceSource(
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
            ))
        session.flush()

        for m_data in seed["manufacturers"]:
            m_obj = Manufacturer(
                name=m_data["name"],
                slug=m_data["slug"],
                country_of_origin=m_data.get("country_of_origin"),
                is_active=True
            )
            session.add(m_obj)
            session.flush()

            for a in m_data.get("aliases", []):
                session.add(ManufacturerAlias(manufacturer_id=m_obj.id, alias=a))

            for mod_data in m_data.get("models", []):
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

                for ma in mod_data.get("aliases", []):
                    session.add(ModelAlias(model_id=mod_obj.id, alias=ma))

                for gen_data in mod_data.get("generations", []):
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

                    for yr in gen_data.get("years", []):
                        session.add(ModelYear(generation_id=gen_obj.id, calendar_year=yr))

                    for var_data in gen_data.get("variants", []):
                        var_obj = VehicleVariant(
                            generation_id=gen_obj.id,
                            name=var_data["name"],
                            slug=var_data["slug"],
                            trim_level=var_data.get("trim_level")
                        )
                        session.add(var_obj)
                        session.flush()

                        for pt_data in var_data.get("powertrains", []):
                            session.add(PowertrainConfiguration(
                                variant_id=var_obj.id,
                                engine_name=pt_data.get("engine_name"),
                                displacement_cc=pt_data.get("displacement_cc"),
                                fuel_type=pt_data["fuel_type"],
                                transmission_type=pt_data["transmission_type"],
                                power_bhp=pt_data.get("power_bhp"),
                                torque_nm=pt_data.get("torque_nm"),
                                arai_mileage_kmpl=pt_data.get("arai_mileage_kmpl"),
                                slug=pt_data.get("slug")
                            ))

        session.flush()

        for c_data in seed.get("knowledge_claims", []):
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

        session.flush()

        # Load Phase 11 expanded vehicle knowledge
        from scripts.seed_vehicle_knowledge import load_expanded_vehicle_knowledge
        load_expanded_vehicle_knowledge(session=session)

    yield session


    session.close()
    try:
        if transaction.is_active:
            transaction.rollback()
    except Exception:
        pass
    connection.close()

@pytest.fixture
def isolated_market_service(db_session):
    """Provide an isolated MarketIntelligenceService bound to test db_session."""
    from server.domain.market.service import MarketIntelligenceService, reset_market_intelligence_service
    from server.api.v1 import market_routes

    orig_market_service = market_routes._MARKET_SERVICE
    test_svc = MarketIntelligenceService(session=db_session)
    market_routes._MARKET_SERVICE = test_svc

    try:
        yield test_svc
    finally:
        market_routes._MARKET_SERVICE = orig_market_service
        reset_market_intelligence_service()


@pytest.fixture
def app_client(db_session):
    """Flask test client with database session patched to test fixture."""
    app = create_app({"TESTING": True})
    
    # Override get_db dependency in routes and infrastructure
    from server.api.v1 import taxonomy_routes, evidence_routes, data_routes, market_routes
    from server.domain.market.service import MarketIntelligenceService, reset_market_intelligence_service
    import server.infrastructure.database as db_infra

    orig_taxonomy_get_db = taxonomy_routes.get_db
    orig_evidence_get_db = evidence_routes.get_db
    orig_data_get_db = getattr(data_routes, "get_db", None)
    orig_infra_get_db = db_infra.get_db
    orig_market_service = market_routes._MARKET_SERVICE

    def test_get_db():
        yield db_session

    taxonomy_routes.get_db = test_get_db
    evidence_routes.get_db = test_get_db
    data_routes.get_db = test_get_db
    db_infra.get_db = test_get_db

    # Route market intelligence operations to the isolated test session
    market_routes._MARKET_SERVICE = MarketIntelligenceService(session=db_session)

    try:
        with app.test_client() as client:
            yield client
    finally:
        taxonomy_routes.get_db = orig_taxonomy_get_db
        evidence_routes.get_db = orig_evidence_get_db
        if orig_data_get_db:
            data_routes.get_db = orig_data_get_db
        db_infra.get_db = orig_infra_get_db
        market_routes._MARKET_SERVICE = orig_market_service
        reset_market_intelligence_service()
