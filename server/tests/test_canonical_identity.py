"""
CARspective — Canonical Identity & Resolution Tests
Asserts slug generation determinism, case-insensitivity, alias resolution, and ambiguity handling.
"""

from server.utils.slugifier import slugify
from server.repositories.taxonomy_repository import TaxonomyRepository
from server.domain.taxonomy.resolver import CanonicalResolver
from server.schemas.taxonomy import CanonicalResolutionRequest, ResolutionStatus

def test_deterministic_slug_generation():
    """Slug generation must be deterministic, lowercase, and handle symbols."""
    assert slugify("Maruti Suzuki") == "maruti-suzuki"
    assert slugify("Hyundai Creta SX (O)") == "hyundai-creta-sx-o"
    assert slugify("   BMW 3-Series   ") == "bmw-3-series"
    assert slugify("Citroën C3") == "citroen-c3"
    assert slugify("Thar [2020-2025]") == "thar-2020-2025"
    assert slugify("") == ""

def test_case_insensitive_matching(db_session):
    """Resolution must work identically across uppercase, lowercase, and mixed-case inputs."""
    repo = TaxonomyRepository(db_session)
    resolver = CanonicalResolver(repo)

    req1 = CanonicalResolutionRequest(brand="hyundai", model="creta", year=2021)
    req2 = CanonicalResolutionRequest(brand="HYUNDAI", model="CRETA", year=2021)
    req3 = CanonicalResolutionRequest(brand="Hyundai", model="Creta", year=2021)

    res1 = resolver.resolve(req1)
    res2 = resolver.resolve(req2)
    res3 = resolver.resolve(req3)

    assert res1.status in [ResolutionStatus.EXACT_MATCH, ResolutionStatus.PARTIAL_MATCH]
    assert res1.canonical_vehicle_id == res2.canonical_vehicle_id == res3.canonical_vehicle_id

def test_manufacturer_and_model_alias_resolution(db_session):
    """Aliases like 'Maruti' -> 'Maruti Suzuki' and 'Maruti Swift' -> 'Swift' must resolve."""
    repo = TaxonomyRepository(db_session)
    resolver = CanonicalResolver(repo)

    req = CanonicalResolutionRequest(
        brand="Maruti",
        model="Maruti Swift",
        year=2021,
        variant="ZXi",
        fuel_type="Petrol",
        transmission_type="Manual"
    )
    res = resolver.resolve(req)
    assert res.status == ResolutionStatus.EXACT_MATCH
    assert res.canonical_vehicle_id == "maruti-suzuki::swift::gen-3-2018::2021::zxi::1-2-dualjet-5mt"
    assert res.hierarchy["manufacturer"]["name"] == "Maruti Suzuki"
    assert res.hierarchy["model"]["name"] == "Swift"

def test_ambiguous_resolution_when_generation_unspecified(db_session):
    """When a model has multiple generations and no year is provided, it must return AMBIGUOUS_MATCH."""
    repo = TaxonomyRepository(db_session)
    resolver = CanonicalResolver(repo)

    # Honda City has 4th Gen and 5th Gen in seed
    req = CanonicalResolutionRequest(brand="Honda", model="City")
    res = resolver.resolve(req)

    assert res.status == ResolutionStatus.AMBIGUOUS_MATCH
    assert res.ambiguous_candidates is not None
    assert len(res.ambiguous_candidates) >= 2
    assert "Model Year is required" in res.match_notes[-1]

def test_generation_separation_by_model_year(db_session):
    """Year 2017 must resolve to City 4th Gen, Year 2022 must resolve to City 5th Gen."""
    repo = TaxonomyRepository(db_session)
    resolver = CanonicalResolver(repo)

    res_2017 = resolver.resolve(CanonicalResolutionRequest(brand="Honda", model="City", year=2017))
    res_2022 = resolver.resolve(CanonicalResolutionRequest(brand="Honda", model="City", year=2022))

    assert "gen-4-2014" in res_2017.canonical_vehicle_id
    assert "gen-5-2020" in res_2022.canonical_vehicle_id
    assert res_2017.canonical_vehicle_id != res_2022.canonical_vehicle_id

def test_unknown_vehicle_returns_unresolved(db_session):
    """Non-existent vehicles must return UNRESOLVED without fabricating data."""
    repo = TaxonomyRepository(db_session)
    resolver = CanonicalResolver(repo)

    req = CanonicalResolutionRequest(brand="Bugatti", model="Chiron", year=2022)
    res = resolver.resolve(req)

    assert res.status == ResolutionStatus.UNRESOLVED
    assert res.canonical_vehicle_id is None
    assert res.confidence_score == 0.0
