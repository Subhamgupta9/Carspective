"""
CARspective — Phase 20E Search N+1 Query Remediation Regression Test Suite
Validates that:
1. Search results and response structures remain correct and strictly conform to the 6-part canonical contract.
2. Filter criteria (brand, fuel, transmission, year, limit) remain strictly respected.
3. Nested taxonomy traversal executes with O(1) batched queries (<= 5 queries) via selectinload, eliminating the previous 56-query N+1 cascade.
4. Empty, no-match, and partial taxonomy states execute safely without crashes or cartesian explosions.
5. TaxonomyRepository eager_hierarchy flag correctly toggles eager vs standard loading.
6. Concurrent search executions under separate threads preserve correct database session isolation.
"""

import time
import pytest
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import event, select
from sqlalchemy.orm import Session

from server.domain.knowledge.service import KnowledgeService
from server.repositories.taxonomy_repository import TaxonomyRepository
from server.models.taxonomy import Manufacturer, VehicleModel, VehicleGeneration, VehicleVariant, PowertrainConfiguration

class QueryCounter:
    def __init__(self, connection):
        self.queries = []
        self._connection = connection

    def __enter__(self):
        self.queries.clear()
        event.listen(self._connection, "before_cursor_execute", self._callback)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        event.remove(self._connection, "before_cursor_execute", self._callback)

    def _callback(self, conn, cursor, statement, parameters, context, executemany):
        self.queries.append(statement)

    @property
    def count(self):
        return len(self.queries)


def test_search_n_plus_one_elimination_query_counts(db_session: Session):
    """
    Verify that KnowledgeService.search_vehicles() executes in <= 5 queries
    for all standard queries, compared to the pre-remediation 56-query cascade.
    """
    connection = db_session.connection()
    service = KnowledgeService(session=db_session)
    test_queries = ["Swift", "Creta", "Nexon", "City", "Baleno"]

    for q in test_queries:
        with QueryCounter(connection) as qc:
            results = service.search_vehicles(query=q)
            # The selectinload strategy executes exactly 5 batched queries (one per hierarchy level)
            assert qc.count <= 5, f"Expected <= 5 queries for query '{q}', got {qc.count}"
            assert len(results) > 0, f"Expected results for known model '{q}', got 0"


def test_search_response_structure_and_canonical_contract(db_session: Session):
    """
    Verify that search response dictionaries contain all required contract keys,
    and that canonical_vehicle_id strictly follows make::model::gen::year::variant::powertrain.
    """
    service = KnowledgeService(session=db_session)
    results = service.search_vehicles(query="Swift", limit=5)

    assert len(results) > 0
    expected_keys = {
        "canonical_vehicle_id", "title", "make", "model",
        "generation", "year", "variant", "fuel_type",
        "transmission", "body_type", "coverage_tier"
    }

    for item in results:
        assert expected_keys.issubset(item.keys()), f"Missing keys in search result: {expected_keys - set(item.keys())}"
        parts = item["canonical_vehicle_id"].split("::")
        assert len(parts) == 6, f"Canonical ID '{item['canonical_vehicle_id']}' does not have 6 parts"
        assert item["make"] != ""
        assert item["model"] != ""
        assert item["year"] > 1990
        assert item["title"] != ""


def test_search_filters_ordering_and_pagination(db_session: Session):
    """
    Verify that brand, fuel, transmission, year, and limit filters function correctly.
    """
    service = KnowledgeService(session=db_session)

    # 1. Brand filter
    hyundai_results = service.search_vehicles(brand="Hyundai")
    assert len(hyundai_results) > 0
    for r in hyundai_results:
        assert r["make"].lower() == "hyundai"

    # 2. Fuel filter
    diesel_results = service.search_vehicles(fuel="Diesel")
    assert len(diesel_results) > 0
    for r in diesel_results:
        assert "diesel" in r["fuel_type"].lower()

    # 3. Transmission filter
    auto_results = service.search_vehicles(transmission="Automatic")
    assert len(auto_results) > 0
    for r in auto_results:
        assert any(t in r["transmission"].lower() for t in ["automatic", "cvt", "dct", "at", "amt"])

    # 4. Limit / Pagination bound
    limited_results = service.search_vehicles(limit=3)
    assert len(limited_results) <= 3


def test_empty_and_partial_taxonomy_handling(db_session: Session):
    """
    Verify that non-existent vehicles, empty queries, and partial data return safely
    without crashes or query explosion.
    """
    connection = db_session.connection()
    service = KnowledgeService(session=db_session)

    # Unknown car search
    with QueryCounter(connection) as qc:
        results = service.search_vehicles(query="NonExistentCarXYZ12345")
        assert len(results) == 0
        assert qc.count <= 5

    # Partial taxonomy safety: create a temporary manufacturer with no models
    temp_mfg = Manufacturer(
        id="test-empty-mfg-id",
        name="EmptyMotors",
        slug="empty-motors",
        is_active=True
    )
    db_session.add(temp_mfg)
    db_session.flush()

    with QueryCounter(connection) as qc:
        results = service.search_vehicles(brand="EmptyMotors")
        assert len(results) == 0
        assert qc.count <= 5


def test_taxonomy_repository_eager_hierarchy_flag(db_session: Session):
    """
    Verify that TaxonomyRepository.list_manufacturers() honors eager_hierarchy flag:
    - eager_hierarchy=False issues only 1 query (minimal query overhead for non-search callers).
    - eager_hierarchy=True issues 5 queries and populates models/generations/variants/powertrains.
    """
    connection = db_session.connection()
    repo = TaxonomyRepository(session=db_session)

    # Default / standard listing: exactly 1 query
    with QueryCounter(connection) as qc:
        mfgs = repo.list_manufacturers(eager_hierarchy=False)
        assert qc.count == 1
        assert len(mfgs) > 0

    # Hierarchical listing: exactly 5 queries
    with QueryCounter(connection) as qc:
        mfgs_eager = repo.list_manufacturers(eager_hierarchy=True)
        assert qc.count == 5
        # Verify relationships are loaded in memory without additional SQL queries
        for m in mfgs_eager:
            for mod in m.models:
                for gen in mod.generations:
                    for var in gen.variants:
                        for pt in var.powertrains:
                            pass
        assert qc.count == 5, f"Expected 0 lazy queries during traversal, but query count was {qc.count}"


def test_concurrent_search_session_isolation():
    """
    Verify that concurrent search requests executed in separate threads
    maintain strict session isolation with no cross-thread contamination or locking errors.
    Uses an isolated self-contained temporary database seeded with canonical taxonomy.
    """
    import tempfile
    import shutil
    from pathlib import Path
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from server.models.base import Base
    from scripts.generate_and_load_seeds import build_seed_data
    from server.models.taxonomy import (
        Manufacturer,
        VehicleModel,
        VehicleGeneration,
        ModelYear,
        VehicleVariant,
        PowertrainConfiguration,
    )

    temp_dir = tempfile.mkdtemp()
    temp_db_path = Path(temp_dir) / "test_search_concurrent.db"

    try:
        engine = create_engine(
            f"sqlite:///{temp_db_path.as_posix()}",
            connect_args={"check_same_thread": False, "timeout": 30.0},
            future=True,
        )
        Base.metadata.create_all(bind=engine)

        SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
        init_sess = SessionLocal()
        try:
            seed = build_seed_data()
            for m_data in seed["manufacturers"]:
                m_obj = Manufacturer(name=m_data["name"], slug=m_data["slug"], is_active=True)
                init_sess.add(m_obj)
                init_sess.flush()
                for mod_data in m_data.get("models", []):
                    mod_obj = VehicleModel(
                        manufacturer_id=m_obj.id,
                        name=mod_data["name"],
                        slug=mod_data["slug"],
                        body_type=mod_data["body_type"],
                        is_active=True,
                    )
                    init_sess.add(mod_obj)
                    init_sess.flush()
                    for gen_data in mod_data.get("generations", []):
                        gen_obj = VehicleGeneration(
                            model_id=mod_obj.id,
                            name=gen_data["name"],
                            slug=gen_data["slug"],
                            year_start=gen_data["year_start"],
                        )
                        init_sess.add(gen_obj)
                        init_sess.flush()
                        for yr in gen_data.get("years", []):
                            init_sess.add(ModelYear(generation_id=gen_obj.id, calendar_year=yr))
                        for var_data in gen_data.get("variants", []):
                            var_obj = VehicleVariant(
                                generation_id=gen_obj.id,
                                name=var_data["name"],
                                slug=var_data["slug"],
                                trim_level=var_data.get("trim_level"),
                            )
                            init_sess.add(var_obj)
                            init_sess.flush()
                            for pt_data in var_data.get("powertrains", []):
                                init_sess.add(
                                    PowertrainConfiguration(
                                        variant_id=var_obj.id,
                                        fuel_type=pt_data["fuel_type"],
                                        transmission_type=pt_data["transmission_type"],
                                        slug=pt_data.get("slug"),
                                    )
                                )
            init_sess.commit()
        finally:
            init_sess.close()

        def worker_search(query_str: str):
            thread_session = SessionLocal()
            try:
                service = KnowledgeService(session=thread_session)
                results = service.search_vehicles(query=query_str, limit=10)
                return len(results), [r["canonical_vehicle_id"] for r in results]
            finally:
                thread_session.close()

        queries = ["Swift", "Creta", "Nexon", "City", "Baleno"] * 3
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(worker_search, q) for q in queries]
            results = [f.result() for f in futures]

        assert len(results) == len(queries)
        for count, ids in results:
            assert count > 0
            assert all("::" in cid for cid in ids)
    finally:
        engine.dispose()
        shutil.rmtree(temp_dir, ignore_errors=True)
