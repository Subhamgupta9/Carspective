"""
CARspective — Governed Source Registry
Maintains auditable, verified metadata for all external and internal data sources.
Prevents illegitimate claims of authority and tracks source lifecycle.
"""

from typing import Dict, List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from .models import (
    GovernedSource,
    SourceType,
    ReliabilityClassification,
)
from server.models.evidence import EvidenceSource, OrganizationType

# Static seed registry of all known authoritative, empirical, and expert sources
CANONICAL_SOURCES: Dict[str, GovernedSource] = {
    "src-gncap-2018-nexon": GovernedSource(
        source_id="src-gncap-2018-nexon",
        source_name="Global NCAP Tata Nexon 2018 Crash Test",
        source_type=SourceType.SAFETY_ORGANIZATION,
        publisher_organization="Global NCAP (Towards Zero Foundation)",
        source_url="https://www.globalncap.org/results/tata-nexon",
        reference_document="Global NCAP Test Report: Tata Nexon",
        jurisdiction="GLOBAL",
        coverage="Tata Nexon 1st Gen Crashworthiness & Structural Integrity",
        collection_method="LABORATORY_CRASH_TEST",
        first_seen="2018-12-07T00:00:00Z",
        last_seen="2026-10-08T00:00:00Z",
        freshness_policy_id="POLICY_SAFETY_CRASH_TEST",
        reliability_classification=ReliabilityClassification.AUTHORITATIVE,
        license_status="PUBLIC_DOMAIN",
        is_active=True
    ),
    "src-gncap-2022-creta": GovernedSource(
        source_id="src-gncap-2022-creta",
        source_name="Global NCAP Hyundai Creta 2022 Crash Test",
        source_type=SourceType.SAFETY_ORGANIZATION,
        publisher_organization="Global NCAP (Towards Zero Foundation)",
        source_url="https://www.globalncap.org/results/hyundai-creta",
        reference_document="Global NCAP Test Report: Hyundai Creta",
        jurisdiction="GLOBAL",
        coverage="Hyundai Creta 2nd Gen Adult/Child Protection",
        collection_method="LABORATORY_CRASH_TEST",
        first_seen="2022-04-12T00:00:00Z",
        last_seen="2026-10-08T00:00:00Z",
        freshness_policy_id="POLICY_SAFETY_CRASH_TEST",
        reliability_classification=ReliabilityClassification.AUTHORITATIVE,
        license_status="PUBLIC_DOMAIN",
        is_active=True
    ),
    "src-gncap-2018-swift": GovernedSource(
        source_id="src-gncap-2018-swift",
        source_name="Global NCAP Maruti Swift 2018 Crash Test",
        source_type=SourceType.SAFETY_ORGANIZATION,
        publisher_organization="Global NCAP (Towards Zero Foundation)",
        source_url="https://www.globalncap.org/results/maruti-swift",
        reference_document="Global NCAP Test Report: Maruti Swift",
        jurisdiction="GLOBAL",
        coverage="Maruti Swift 3rd Gen Crash Test Safety Assessment",
        collection_method="LABORATORY_CRASH_TEST",
        first_seen="2018-10-10T00:00:00Z",
        last_seen="2026-10-08T00:00:00Z",
        freshness_policy_id="POLICY_SAFETY_CRASH_TEST",
        reliability_classification=ReliabilityClassification.AUTHORITATIVE,
        license_status="PUBLIC_DOMAIN",
        is_active=True
    ),
    "src-gncap-2020-thar": GovernedSource(
        source_id="src-gncap-2020-thar",
        source_name="Global NCAP Mahindra Thar 2020 Crash Test",
        source_type=SourceType.SAFETY_ORGANIZATION,
        publisher_organization="Global NCAP (Towards Zero Foundation)",
        source_url="https://www.globalncap.org/results/mahindra-thar",
        reference_document="Global NCAP Test Report: Mahindra Thar",
        jurisdiction="GLOBAL",
        coverage="Mahindra Thar 2nd Gen Safety Rating & Integrity",
        collection_method="LABORATORY_CRASH_TEST",
        first_seen="2020-11-26T00:00:00Z",
        last_seen="2026-10-08T00:00:00Z",
        freshness_policy_id="POLICY_SAFETY_CRASH_TEST",
        reliability_classification=ReliabilityClassification.AUTHORITATIVE,
        license_status="PUBLIC_DOMAIN",
        is_active=True
    ),
    "src-empirical-listings-57480": GovernedSource(
        source_id="src-empirical-listings-57480",
        source_name="CARspective Empirical Used Car Market Dataset",
        source_type=SourceType.INTERNAL_EMPIRICAL_DATASET,
        publisher_organization="CARspective Research & Analytics Engine",
        source_url="internal://data/raw/indian_used_cars_raw_57480.csv",
        reference_document="Empirical Observation Dataset: 57,480 Indian Used Car Listings (2018-2024)",
        jurisdiction="IN",
        coverage="57,480 historical Indian used-car asking price listing observations across Tier 1, 2, and 3 market segments",
        collection_method="EMPIRICAL_LISTING_AUDIT",
        first_seen="2018-01-01T00:00:00Z",
        last_seen="2024-12-31T23:59:59Z",
        freshness_policy_id="POLICY_HISTORICAL_LISTINGS",
        reliability_classification=ReliabilityClassification.EMPIRICAL_OBSERVATION,
        license_status="PROPRIETARY_RESEARCH",
        is_active=True
    ),
    "src-oem-maruti-swift-2018": GovernedSource(
        source_id="src-oem-maruti-swift-2018",
        source_name="Maruti Suzuki Technical Brochure — Swift 2018",
        source_type=SourceType.MANUFACTURER,
        publisher_organization="Maruti Suzuki India Ltd",
        source_url="https://www.marutisuzuki.com/swift/brochure",
        reference_document="Official Spec Sheet: Maruti Swift K12M / DDiS 190 (2018)",
        jurisdiction="IN",
        coverage="Maruti Swift Gen 3 Dimensions, Powertrains, and Equipment",
        collection_method="OFFICIAL_OEM_DOCUMENT",
        first_seen="2018-02-08T00:00:00Z",
        last_seen="2026-10-08T00:00:00Z",
        freshness_policy_id="POLICY_OEM_SPECIFICATIONS",
        reliability_classification=ReliabilityClassification.AUTHORITATIVE,
        license_status="PUBLIC_DOMAIN",
        is_active=True
    ),
    "src-oem-hyundai-creta-2020": GovernedSource(
        source_id="src-oem-hyundai-creta-2020",
        source_name="Hyundai Creta Official Technical Specifications (2020)",
        source_type=SourceType.MANUFACTURER,
        publisher_organization="Hyundai Motor India Ltd",
        source_url="https://www.hyundai.com/in/creta",
        reference_document="Official Spec Sheet: Hyundai Creta (SU2i 2020)",
        jurisdiction="IN",
        coverage="Hyundai Creta Gen 2 Engines, Transmissions, and Dimensions",
        collection_method="OFFICIAL_OEM_DOCUMENT",
        first_seen="2020-03-16T00:00:00Z",
        last_seen="2026-10-08T00:00:00Z",
        freshness_policy_id="POLICY_OEM_SPECIFICATIONS",
        reliability_classification=ReliabilityClassification.AUTHORITATIVE,
        license_status="PUBLIC_DOMAIN",
        is_active=True
    ),
    "src-oem-tata-nexon-2017": GovernedSource(
        source_id="src-oem-tata-nexon-2017",
        source_name="Tata Nexon Technical Specification Document (2017)",
        source_type=SourceType.MANUFACTURER,
        publisher_organization="Tata Motors Passenger Vehicles Ltd",
        source_url="https://cars.tatamotors.com/nexon",
        reference_document="Official Spec Sheet: Tata Nexon Revotron / Revotorq (2017)",
        jurisdiction="IN",
        coverage="Tata Nexon Gen 1 Specifications, Ground Clearance, and Capacities",
        collection_method="OFFICIAL_OEM_DOCUMENT",
        first_seen="2017-09-21T00:00:00Z",
        last_seen="2026-10-08T00:00:00Z",
        freshness_policy_id="POLICY_OEM_SPECIFICATIONS",
        reliability_classification=ReliabilityClassification.AUTHORITATIVE,
        license_status="PUBLIC_DOMAIN",
        is_active=True
    ),
    "src-oem-honda-city-2020": GovernedSource(
        source_id="src-oem-honda-city-2020",
        source_name="Honda City 5th Gen Official Brochure (2020)",
        source_type=SourceType.MANUFACTURER,
        publisher_organization="Honda Cars India Ltd",
        source_url="https://www.hondacarindia.com/all-new-city",
        reference_document="Official Spec Sheet: Honda City 5th Gen (2020)",
        jurisdiction="IN",
        coverage="Honda City Gen 5 i-VTEC / i-DTEC Technical Architecture",
        collection_method="OFFICIAL_OEM_DOCUMENT",
        first_seen="2020-07-15T00:00:00Z",
        last_seen="2026-10-08T00:00:00Z",
        freshness_policy_id="POLICY_OEM_SPECIFICATIONS",
        reliability_classification=ReliabilityClassification.AUTHORITATIVE,
        license_status="PUBLIC_DOMAIN",
        is_active=True
    ),
    "src-oem-mahindra-thar-2020": GovernedSource(
        source_id="src-oem-mahindra-thar-2020",
        source_name="Mahindra Thar Technical Manual (2020)",
        source_type=SourceType.MANUFACTURER,
        publisher_organization="Mahindra & Mahindra Ltd",
        source_url="https://auto.mahindra.com/suv/thar",
        reference_document="Official Spec Sheet: Mahindra Thar 2nd Gen (2020)",
        jurisdiction="IN",
        coverage="Mahindra Thar Gen 2 4x4 Specifications, Angles, and Dimensions",
        collection_method="OFFICIAL_OEM_DOCUMENT",
        first_seen="2020-10-02T00:00:00Z",
        last_seen="2026-10-08T00:00:00Z",
        freshness_policy_id="POLICY_OEM_SPECIFICATIONS",
        reliability_classification=ReliabilityClassification.AUTHORITATIVE,
        license_status="PUBLIC_DOMAIN",
        is_active=True
    ),
    "src-arai-cert-database": GovernedSource(
        source_id="src-arai-cert-database",
        source_name="ARAI Fuel Economy & Emission Homologation Registry",
        source_type=SourceType.GOVERNMENT_AUTHORITY,
        publisher_organization="Automotive Research Association of India (ARAI)",
        source_url="https://www.araiindia.com/certification",
        reference_document="CMVR Rule 115 Homologation Certificate Archive",
        jurisdiction="IN",
        coverage="Standardized Rule 115 Indian Driving Cycle (IDC) Mileage Ratings",
        collection_method="REGULATORY_FILING",
        first_seen="2015-01-01T00:00:00Z",
        last_seen="2026-10-08T00:00:00Z",
        freshness_policy_id="POLICY_REGULATORY_ARAI",
        reliability_classification=ReliabilityClassification.REGULATORY_BENCHMARK,
        license_status="PUBLIC_DOMAIN",
        is_active=True
    ),
    "src-industry-service-audit": GovernedSource(
        source_id="src-industry-service-audit",
        source_name="Automotive Technical Service Advisory Board — Reliability Audit",
        source_type=SourceType.EXPERT_SOURCE,
        publisher_organization="Automotive Technical Service Advisory Board",
        source_url="internal://advisory/service-bulletins/audit-2024",
        reference_document="Independent Workshop Maintenance & Defect Frequency Study (2024)",
        jurisdiction="IN",
        coverage="Real-world Indian ownership defect rates, part failure modes, and annual service costs",
        collection_method="EXPERT_AUDIT",
        first_seen="2024-01-15T00:00:00Z",
        last_seen="2026-10-08T00:00:00Z",
        freshness_policy_id="POLICY_OWNERSHIP_AUDIT",
        reliability_classification=ReliabilityClassification.INDUSTRY_AUDIT,
        license_status="PROPRIETARY_RESEARCH",
        is_active=True
    ),
    # Explicitly registered deprecated source for lifecycle testing
    "src-legacy-classifieds-v0": GovernedSource(
        source_id="src-legacy-classifieds-v0",
        source_name="Legacy Classifieds Web Crawl v0 (Deprecated)",
        source_type=SourceType.MARKET_LISTING_SOURCE,
        publisher_organization="Legacy Unverified Scraping Collector",
        source_url=None,
        reference_document="Unverified Classifieds Archive 2015",
        jurisdiction="IN",
        coverage="Unchecked consumer web listings (2015)",
        collection_method="UNCHECKED_SCRAPE",
        first_seen="2015-01-01T00:00:00Z",
        last_seen="2016-01-01T00:00:00Z",
        freshness_policy_id="POLICY_MARKET_OBSERVATIONS",
        reliability_classification=ReliabilityClassification.UNVERIFIED,
        license_status="UNKNOWN",
        is_active=False,
        deprecated_at="2020-01-01T00:00:00Z"
    ),
    "src-current-market-aggregator-2026": GovernedSource(
        source_id="src-current-market-aggregator-2026",
        source_name="Multi-Metro Used Vehicle Live Market Aggregator (2026)",
        source_type=SourceType.MARKET_LISTING_SOURCE,
        publisher_organization="Governed National Used Vehicle Listing Aggregator",
        source_url="https://market-feed.carspective.internal/api/v1/listings/2026-q3",
        reference_document="Governed Current Secondary Market Observation Snapshot (2026-Q3)",
        jurisdiction="IN",
        coverage="Current active seller asking price observations across Delhi NCR, Mumbai, Bengaluru, Hyderabad, and Pune",
        collection_method="STRUCTURED_API_SNAPSHOT",
        first_seen="2026-07-01T00:00:00Z",
        last_seen="2026-10-08T00:00:00Z",
        freshness_policy_id="POLICY_CURRENT_MARKET_OBSERVATIONS",
        reliability_classification=ReliabilityClassification.EMPIRICAL_OBSERVATION,
        license_status="COMMERCIAL_API_LICENSE",
        is_active=True
    ),
    "src-current-certified-dealer-network-2026": GovernedSource(
        source_id="src-current-certified-dealer-network-2026",
        source_name="Certified Dealer Network Live Inventory Feed (2026)",
        source_type=SourceType.MARKET_LISTING_SOURCE,
        publisher_organization="National Certified Used Car Dealership Consortium",
        source_url="https://certified-dealers.carspective.internal/feed/active",
        reference_document="Certified Dealer Direct Inventory Registry",
        jurisdiction="IN",
        coverage="Certified multi-point inspected dealer used car inventory asking prices",
        collection_method="DEALER_FEED_INTEGRATION",
        first_seen="2026-07-01T00:00:00Z",
        last_seen="2026-10-08T00:00:00Z",
        freshness_policy_id="POLICY_CURRENT_MARKET_OBSERVATIONS",
        reliability_classification=ReliabilityClassification.EMPIRICAL_OBSERVATION,
        license_status="PARTNER_INTEGRATION",
        is_active=True
    ),
    "src-current-metro-classifieds-2026": GovernedSource(
        source_id="src-current-metro-classifieds-2026",
        source_name="Metro Classifieds Direct Listings Feed (2026)",
        source_type=SourceType.MARKET_LISTING_SOURCE,
        publisher_organization="Metro Regional Classifieds Platform",
        source_url="https://classifieds.carspective.internal/listings/metro",
        reference_document="Metro Regional Direct Consumer & Dealer Classifieds",
        jurisdiction="IN",
        coverage="Consumer direct and regional dealer listings in top 5 Indian metros",
        collection_method="CLASSIFIEDS_FEED",
        first_seen="2026-07-01T00:00:00Z",
        last_seen="2026-10-08T00:00:00Z",
        freshness_policy_id="POLICY_CURRENT_MARKET_OBSERVATIONS",
        reliability_classification=ReliabilityClassification.EMPIRICAL_OBSERVATION,
        license_status="PUBLIC_INDEX",
        is_active=True
    ),
}

class GovernedSourceRegistry:
    """In-memory and database-synchronized governed source registry."""

    def __init__(self, session: Optional[Session] = None):
        self.session = session
        self._sources: Dict[str, GovernedSource] = dict(CANONICAL_SOURCES)

    def get_source(self, source_id: str) -> Optional[GovernedSource]:
        if source_id in self._sources:
            return self._sources[source_id]
        if self.session:
            db_source = self.session.get(EvidenceSource, source_id)
            if db_source:
                return self._from_db_model(db_source)
        return None

    def list_sources(
        self,
        active_only: bool = False,
        source_type: Optional[SourceType] = None
    ) -> List[GovernedSource]:
        res = list(self._sources.values())
        if active_only:
            res = [s for s in res if s.is_active]
        if source_type:
            res = [s for s in res if s.source_type == source_type]
        return sorted(res, key=lambda s: (not s.is_active, s.source_id))

    def register_source(self, source: GovernedSource) -> GovernedSource:
        """
        Registers a new source, enforcing epistemic honesty (non-authoritative sources
        cannot claim AUTHORITATIVE classification).
        """
        # Enforce Section 4: Do NOT claim a source is authoritative unless that status is supported
        if source.reliability_classification == ReliabilityClassification.AUTHORITATIVE:
            if source.source_type not in (SourceType.MANUFACTURER, SourceType.SAFETY_ORGANIZATION, SourceType.GOVERNMENT_AUTHORITY):
                raise ValueError(
                    f"Source type '{source.source_type}' cannot claim AUTHORITATIVE reliability. "
                    "Only MANUFACTURER, SAFETY_ORGANIZATION, and GOVERNMENT_AUTHORITY sources can be AUTHORITATIVE."
                )

        self._sources[source.source_id] = source
        return source

    def deprecate_source(self, source_id: str) -> Optional[GovernedSource]:
        src = self.get_source(source_id)
        if src:
            src.is_active = False
            src.deprecated_at = datetime.now(timezone.utc).isoformat()
            self._sources[source_id] = src
            return src
        return None

    def _from_db_model(self, db_source: EvidenceSource) -> GovernedSource:
        """Adapts legacy EvidenceSource database model to GovernedSource schema."""
        type_mapping = {
            OrganizationType.SAFETY_AGENCY: SourceType.SAFETY_ORGANIZATION,
            OrganizationType.REGULATORY_BODY: SourceType.GOVERNMENT_AUTHORITY,
            OrganizationType.OEM_MANUFACTURER: SourceType.MANUFACTURER,
            OrganizationType.EMPIRICAL_DATASET: SourceType.INTERNAL_EMPIRICAL_DATASET,
            OrganizationType.INDUSTRY_AUDIT: SourceType.EXPERT_SOURCE,
            OrganizationType.OTHER: SourceType.RESEARCH_PUBLICATION,
        }
        source_type = type_mapping.get(db_source.organization_type, SourceType.RESEARCH_PUBLICATION)
        
        rel_class = ReliabilityClassification.AUTHORITATIVE
        if source_type == SourceType.INTERNAL_EMPIRICAL_DATASET:
            rel_class = ReliabilityClassification.EMPIRICAL_OBSERVATION
        elif source_type == SourceType.EXPERT_SOURCE:
            rel_class = ReliabilityClassification.INDUSTRY_AUDIT

        return GovernedSource(
            source_id=db_source.id,
            source_name=f"{db_source.organization_name} Record",
            source_type=source_type,
            publisher_organization=db_source.organization_name,
            source_url=db_source.source_url,
            reference_document=db_source.reference_document,
            jurisdiction="IN",
            coverage=f"Evidence records for {db_source.organization_name}",
            collection_method="CURATED",
            first_seen=(db_source.valid_from.isoformat() if db_source.valid_from else "2018-01-01T00:00:00Z"),
            last_seen=db_source.retrieved_at.isoformat(),
            freshness_policy_id="POLICY_OEM_SPECIFICATIONS",
            reliability_classification=rel_class,
            license_status="PUBLIC_DOMAIN",
            is_active=(db_source.verification_status != "DEPRECATED")
        )
