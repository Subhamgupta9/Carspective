"""
CARspective — Vehicle Knowledge Domain Service
Coordinates comprehensive vehicle intelligence retrieval, multi-parameter search,
variant-aware feature resolution, safety scope isolation, and evidence freshness assessment.
"""

import json
from typing import List, Optional, Dict, Any
from datetime import date, datetime, timezone
from sqlalchemy.orm import Session

from server.repositories.taxonomy_repository import TaxonomyRepository
from server.repositories.knowledge_repository import KnowledgeRepository
from server.repositories.evidence_repository import EvidenceRepository
from server.domain.taxonomy.resolver import CanonicalResolver
from server.schemas.taxonomy import CanonicalResolutionRequest
from server.schemas.knowledge import (
    VehicleKnowledgeProfileSchema,
    VehicleSpecificationSchema,
    VehicleDimensionsSchema,
    VehicleSafetyRatingSchema,
    VariantFeatureSchema,
    OwnershipProfileSchema,
    ReliabilityIssueSchema,
    VehicleProConSchema,
    ReviewSynthesisSchema,
    SourceMetadataSchema,
)

class KnowledgeService:
    def __init__(self, session: Optional[Session] = None):
        self._session = session
        self.taxonomy_repo = TaxonomyRepository(session=session)
        self.knowledge_repo = KnowledgeRepository(session=session)
        self.evidence_repo = EvidenceRepository(session=session)
        self.resolver = CanonicalResolver(self.taxonomy_repo)

    @property
    def session(self) -> Session:
        if self._session is not None:
            return self._session
        from server.infrastructure.database import ScopedSession
        return ScopedSession()

    @session.setter
    def session(self, value: Optional[Session]) -> None:
        self._session = value
        self.taxonomy_repo.session = value
        self.knowledge_repo.session = value
        self.evidence_repo.session = value

    def _format_source(self, source) -> Optional[SourceMetadataSchema]:
        if not source:
            return None
        today = date.today()
        is_stale = False
        if source.valid_until and today > source.valid_until:
            is_stale = True

        review_due_str = None
        if source.published_at:
            # Review due 3 years from publication for safety/specs
            from datetime import timedelta
            review_due = source.published_at + timedelta(days=365 * 3)
            review_due_str = review_due.isoformat()
            if today > review_due:
                is_stale = True

        return SourceMetadataSchema(
            source_id=source.id,
            organization_name=source.organization_name,
            organization_type=source.organization_type.value if hasattr(source.organization_type, "value") else str(source.organization_type),
            source_url=source.source_url,
            reference_document=source.reference_document,
            published_at=source.published_at.isoformat() if source.published_at else None,
            retrieved_at=source.retrieved_at.isoformat() if source.retrieved_at else None,
            valid_until=source.valid_until.isoformat() if source.valid_until else None,
            review_due=review_due_str,
            is_stale=is_stale,
            confidence_score=source.confidence_score,
            verification_status=source.verification_status.value if hasattr(source.verification_status, "value") else str(source.verification_status),
        )

    def get_vehicle_profile(self, canonical_id: str) -> Optional[VehicleKnowledgeProfileSchema]:
        """
        Retrieves the unified canonical vehicle intelligence profile.
        Never fabricates missing fields; returns clean None or empty collections with epistemic honesty.
        """
        parts = canonical_id.split("::")
        make_slug = parts[0] if len(parts) >= 1 else ""
        model_slug = parts[1] if len(parts) >= 2 else ""
        gen_slug = parts[2] if len(parts) >= 3 else ""
        year = int(parts[3]) if len(parts) >= 4 and parts[3].isdigit() else None
        variant_slug = parts[4] if len(parts) >= 5 else ""

        # Validate make and model existence
        m = self.taxonomy_repo.get_manufacturer_by_slug(make_slug)
        mod = self.taxonomy_repo.get_model_by_slug(make_slug, model_slug) if m else None

        if not m or not mod:
            m_res, mod_res = self.taxonomy_repo.resolve_make_model_from_slug(canonical_id)
            if m_res and mod_res:
                m, mod = m_res, mod_res
                make_slug, model_slug = m.slug, mod.slug

        if not m or not mod:
            return None

        # Resolve generation
        gen_obj = None
        if gen_slug:
            gen_obj = next((g for g in mod.generations if g.slug == gen_slug), None)
        elif year:
            gen_obj = next((g for g in mod.generations if g.year_start <= year and (not g.year_end or g.year_end >= year)), None)
        elif len(mod.generations) > 0:
            gen_obj = mod.generations[-1] # default to latest generation if unspecified

        target_id = f"{make_slug}::{model_slug}::{gen_obj.slug}" if (gen_obj and len(parts) < 3) else canonical_id

        # Resolve variant
        var_obj = None
        if gen_obj and variant_slug:
            var_obj = next((v for v in gen_obj.variants if v.slug == variant_slug), None)

        # 1. Specifications
        specs_list = self.knowledge_repo.get_specifications_for_vehicle(target_id)
        spec_schema = None
        if specs_list:
            s = specs_list[0]
            spec_schema = VehicleSpecificationSchema(
                engine_type=s.engine_type,
                displacement_cc=s.displacement_cc,
                cylinders=s.cylinders,
                valves_per_cylinder=s.valves_per_cylinder,
                aspiration=s.aspiration,
                max_power_bhp=s.max_power_bhp,
                max_power_rpm=s.max_power_rpm,
                max_torque_nm=s.max_torque_nm,
                max_torque_rpm=s.max_torque_rpm,
                transmission=s.transmission,
                drivetrain=s.drivetrain,
                fuel_type=s.fuel_type,
                arai_mileage_kmpl=s.arai_mileage_kmpl,
                fuel_tank_capacity_l=s.fuel_tank_capacity_l,
                emission_norm=s.emission_norm,
                battery_capacity_kwh=s.battery_capacity_kwh,
                electric_range_km=s.electric_range_km,
                motor_output_ps=s.motor_output_ps,
                evidence_state=s.evidence_state.value if hasattr(s.evidence_state, "value") else str(s.evidence_state),
                source=self._format_source(s.source)
            )

        # 2. Dimensions
        dim_obj = self.knowledge_repo.get_dimensions_for_vehicle(target_id)
        dim_schema = None
        if dim_obj:
            dim_schema = VehicleDimensionsSchema(
                length_mm=dim_obj.length_mm,
                width_mm=dim_obj.width_mm,
                height_mm=dim_obj.height_mm,
                wheelbase_mm=dim_obj.wheelbase_mm,
                ground_clearance_mm=dim_obj.ground_clearance_mm,
                boot_capacity_l=dim_obj.boot_capacity_l,
                seating_capacity=dim_obj.seating_capacity,
                kerb_weight_kg=dim_obj.kerb_weight_kg,
                turning_radius_m=dim_obj.turning_radius_m,
                evidence_state=dim_obj.evidence_state.value if hasattr(dim_obj.evidence_state, "value") else str(dim_obj.evidence_state),
                source=self._format_source(dim_obj.source)
            )

        # 3. Safety Rating
        safety_obj = self.knowledge_repo.get_safety_rating_for_vehicle(target_id)
        safety_schema = None
        if safety_obj:
            safety_schema = VehicleSafetyRatingSchema(
                organization=safety_obj.organization,
                test_year=safety_obj.test_year,
                adult_stars=safety_obj.adult_stars,
                adult_score=safety_obj.adult_score,
                child_stars=safety_obj.child_stars,
                child_score=safety_obj.child_score,
                bodyshell_integrity=safety_obj.bodyshell_integrity,
                standard_safety_equipment=safety_obj.standard_safety_equipment,
                test_protocol=safety_obj.test_protocol,
                evidence_state=safety_obj.evidence_state.value if hasattr(safety_obj.evidence_state, "value") else str(safety_obj.evidence_state),
                source=self._format_source(safety_obj.source)
            )

        # 4. Features (Variant-aware)
        feature_schemas = []
        if var_obj:
            features = self.knowledge_repo.get_features_for_variant(var_obj.id)
            for f in features:
                feature_schemas.append(
                    VariantFeatureSchema(
                        feature_key=f.feature_key,
                        feature_name=f.feature_key.replace("_", " ").title(),
                        category="EQUIPMENT",
                        availability=f.availability,
                        details=f.details,
                        variant_name=var_obj.name,
                        evidence_state=f.evidence_state.value if hasattr(f.evidence_state, "value") else str(f.evidence_state),
                        source=self._format_source(f.source)
                    )
                )
        elif gen_obj:
            features = self.knowledge_repo.get_features_for_generation(gen_obj.id)
            for f in features:
                feature_schemas.append(
                    VariantFeatureSchema(
                        feature_key=f.feature_key,
                        feature_name=f.feature_key.replace("_", " ").title(),
                        category="EQUIPMENT",
                        availability=f.availability,
                        details=f.details,
                        variant_name=f.variant.name if f.variant else None,
                        evidence_state=f.evidence_state.value if hasattr(f.evidence_state, "value") else str(f.evidence_state),
                        source=self._format_source(f.source)
                    )
                )

        # 5. Ownership Profile
        own_obj = self.knowledge_repo.get_ownership_profile_for_vehicle(target_id)
        own_schema = None
        if own_obj:
            strengths = json.loads(own_obj.ownership_strengths) if own_obj.ownership_strengths else []
            concerns = json.loads(own_obj.ownership_concerns) if own_obj.ownership_concerns else []
            own_schema = OwnershipProfileSchema(
                service_interval_km=own_obj.service_interval_km,
                service_interval_months=own_obj.service_interval_months,
                typical_annual_maintenance_inr=own_obj.typical_annual_maintenance_inr,
                parts_availability=own_obj.parts_availability,
                maintenance_complexity=own_obj.maintenance_complexity,
                real_world_city_mileage_kmpl=own_obj.real_world_city_mileage_kmpl,
                real_world_highway_mileage_kmpl=own_obj.real_world_highway_mileage_kmpl,
                ownership_strengths=strengths,
                ownership_concerns=concerns,
                evidence_state=own_obj.evidence_state.value if hasattr(own_obj.evidence_state, "value") else str(own_obj.evidence_state),
                source=self._format_source(own_obj.source)
            )

        # 6. Reliability Issues
        issues = self.knowledge_repo.get_reliability_issues_for_vehicle(target_id)
        issue_schemas = [
            ReliabilityIssueSchema(
                issue_key=iss.issue_key,
                category=iss.category,
                title=iss.title,
                description=iss.description,
                severity=iss.severity,
                affected_years=iss.affected_years,
                affected_powertrains=iss.affected_powertrains,
                verification_status=iss.verification_status,
                evidence_state=iss.evidence_state.value if hasattr(iss.evidence_state, "value") else str(iss.evidence_state),
                source=self._format_source(iss.source)
            )
            for iss in issues
        ]

        # 7. Pros & Cons
        pros_cons = self.knowledge_repo.get_pros_cons_for_vehicle(target_id)
        pros = [
            VehicleProConSchema(
                is_pro=True,
                statement=pc.statement,
                category=pc.category,
                source_type=pc.source_type,
                evidence_state=pc.evidence_state.value if hasattr(pc.evidence_state, "value") else str(pc.evidence_state),
                source=self._format_source(pc.source)
            )
            for pc in pros_cons if pc.is_pro
        ]
        cons = [
            VehicleProConSchema(
                is_pro=False,
                statement=pc.statement,
                category=pc.category,
                source_type=pc.source_type,
                evidence_state=pc.evidence_state.value if hasattr(pc.evidence_state, "value") else str(pc.evidence_state),
                source=self._format_source(pc.source)
            )
            for pc in pros_cons if not pc.is_pro
        ]

        # 8. Review Synthesis
        rev_obj = self.knowledge_repo.get_review_synthesis_for_vehicle(target_id)
        rev_schema = None
        if rev_obj:
            rev_schema = ReviewSynthesisSchema(
                what_owners_say=rev_obj.what_owners_say if rev_obj.has_owner_evidence else "Review evidence unavailable.",
                what_experts_say=rev_obj.what_experts_say if rev_obj.has_expert_evidence else "Review evidence unavailable.",
                carspective_analysis=rev_obj.carspective_analysis,
                has_owner_evidence=rev_obj.has_owner_evidence,
                has_expert_evidence=rev_obj.has_expert_evidence,
                evidence_state=rev_obj.evidence_state.value if hasattr(rev_obj.evidence_state, "value") else str(rev_obj.evidence_state),
                source=self._format_source(rev_obj.source)
            )

        # Freshness summary
        freshness = {
            "last_verified": datetime.now(timezone.utc).date().isoformat(),
            "has_stale_data": any([
                spec_schema.source.is_stale if spec_schema and spec_schema.source else False,
                dim_schema.source.is_stale if dim_schema and dim_schema.source else False,
                safety_schema.source.is_stale if safety_schema and safety_schema.source else False,
            ]),
            "evidence_coverage": {
                "specifications": "SUPPORTED" if spec_schema else "UNAVAILABLE",
                "dimensions": "SUPPORTED" if dim_schema else "UNAVAILABLE",
                "safety": safety_schema.evidence_state if safety_schema else "INSUFFICIENT_DATA",
                "features": "VARIANT_SCOPED" if feature_schemas else "UNAVAILABLE",
                "ownership": "SUPPORTED" if own_schema else "UNAVAILABLE",
                "reliability": f"{len(issue_schemas)} ADVISORIES" if issue_schemas else "0 ADVISORIES",
            }
        }

        return VehicleKnowledgeProfileSchema(
            canonical_vehicle_id=canonical_id,
            make=m.name,
            model=mod.name,
            generation_name=gen_obj.name if gen_obj else None,
            year=year,
            variant_name=var_obj.name if var_obj else None,
            body_type=mod.body_type,
            segment=mod.segment,
            coverage_tier=mod.coverage_tier,
            specifications=spec_schema,
            dimensions=dim_schema,
            safety=safety_schema,
            features=feature_schemas,
            ownership=own_schema,
            reliability_issues=issue_schemas,
            pros=pros,
            cons=cons,
            reviews=rev_schema,
            freshness_summary=freshness
        )

    def get_comparison_specifications(self, canonical_id: str) -> Optional[Dict[str, Any]]:
        """
        Targeted retrieval of specifications, dimensions, and safety ratings for vehicle comparison.
        Avoids querying features, ownership, reliability, pros/cons, and review tables.
        Returns dict with keys: 'specifications', 'dimensions', 'safety' containing either
        their corresponding schema objects or None if unavailable.
        """
        if not canonical_id:
            return None

        parts = canonical_id.split("::")
        if len(parts) >= 3:
            target_id = canonical_id
        else:
            make_slug = parts[0] if len(parts) >= 1 else ""
            model_slug = parts[1] if len(parts) >= 2 else ""
            m = self.taxonomy_repo.get_manufacturer_by_slug(make_slug)
            mod = self.taxonomy_repo.get_model_by_slug(make_slug, model_slug) if m else None
            gen_obj = mod.generations[-1] if (mod and len(mod.generations) > 0) else None
            target_id = f"{make_slug}::{model_slug}::{gen_obj.slug}" if gen_obj else canonical_id

        # 1. Specifications (only 1 table queried)
        specs_list = self.knowledge_repo.get_specifications_for_vehicle(target_id)
        spec_schema = None
        if specs_list:
            s = specs_list[0]
            spec_schema = VehicleSpecificationSchema(
                engine_type=s.engine_type,
                displacement_cc=s.displacement_cc,
                cylinders=s.cylinders,
                valves_per_cylinder=s.valves_per_cylinder,
                aspiration=s.aspiration,
                max_power_bhp=s.max_power_bhp,
                max_power_rpm=s.max_power_rpm,
                max_torque_nm=s.max_torque_nm,
                max_torque_rpm=s.max_torque_rpm,
                transmission=s.transmission,
                drivetrain=s.drivetrain,
                fuel_type=s.fuel_type,
                arai_mileage_kmpl=s.arai_mileage_kmpl,
                fuel_tank_capacity_l=s.fuel_tank_capacity_l,
                emission_norm=s.emission_norm,
                battery_capacity_kwh=s.battery_capacity_kwh,
                electric_range_km=s.electric_range_km,
                motor_output_ps=s.motor_output_ps,
                evidence_state=s.evidence_state.value if hasattr(s.evidence_state, "value") else str(s.evidence_state),
                source=self._format_source(s.source)
            )

        # 2. Dimensions (only 1 table queried)
        dim_obj = self.knowledge_repo.get_dimensions_for_vehicle(target_id)
        dim_schema = None
        if dim_obj:
            dim_schema = VehicleDimensionsSchema(
                length_mm=dim_obj.length_mm,
                width_mm=dim_obj.width_mm,
                height_mm=dim_obj.height_mm,
                wheelbase_mm=dim_obj.wheelbase_mm,
                ground_clearance_mm=dim_obj.ground_clearance_mm,
                boot_capacity_l=dim_obj.boot_capacity_l,
                seating_capacity=dim_obj.seating_capacity,
                kerb_weight_kg=dim_obj.kerb_weight_kg,
                turning_radius_m=dim_obj.turning_radius_m,
                evidence_state=dim_obj.evidence_state.value if hasattr(dim_obj.evidence_state, "value") else str(dim_obj.evidence_state),
                source=self._format_source(dim_obj.source)
            )

        # 3. Safety Rating (only 1 table queried)
        safety_obj = self.knowledge_repo.get_safety_rating_for_vehicle(target_id)
        safety_schema = None
        if safety_obj:
            safety_schema = VehicleSafetyRatingSchema(
                organization=safety_obj.organization,
                test_year=safety_obj.test_year,
                adult_stars=safety_obj.adult_stars,
                adult_score=safety_obj.adult_score,
                child_stars=safety_obj.child_stars,
                child_score=safety_obj.child_score,
                bodyshell_integrity=safety_obj.bodyshell_integrity,
                standard_safety_equipment=safety_obj.standard_safety_equipment,
                test_protocol=safety_obj.test_protocol,
                evidence_state=safety_obj.evidence_state.value if hasattr(safety_obj.evidence_state, "value") else str(safety_obj.evidence_state),
                source=self._format_source(safety_obj.source)
            )

        return {
            "specifications": spec_schema,
            "dimensions": dim_schema,
            "safety": safety_schema,
        }

    def search_vehicles(
        self,
        query: str = "",
        brand: Optional[str] = None,
        model: Optional[str] = None,
        year: Optional[int] = None,
        fuel: Optional[str] = None,
        transmission: Optional[str] = None,
        limit: int = 20,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search canonical vehicles using multi-parameter matching and fuzzy token resolution.
        """
        results = []
        if use_cache:
            manufacturers = self.taxonomy_repo.get_taxonomy_hierarchy_snapshot()
        else:
            manufacturers = self.taxonomy_repo.list_manufacturers(eager_hierarchy=True)

        q_lower = query.lower().strip() if query else ""
        brand_lower = brand.lower().strip() if brand else ""
        model_lower = model.lower().strip() if model else ""
        fuel_lower = fuel.lower().strip() if fuel else ""
        trans_lower = transmission.lower().strip() if transmission else ""

        extracted_year = None
        if q_lower:
            for tok in q_lower.split():
                if tok.isdigit() and len(tok) == 4 and 1990 <= int(tok) <= 2030:
                    extracted_year = int(tok)
                    break
        effective_year = year or extracted_year

        for m in manufacturers:
            # Check brand filter
            if brand_lower and brand_lower not in m.name.lower() and brand_lower not in m.slug:
                continue

            for mod in m.models:
                # Check model filter
                if model_lower and model_lower not in mod.name.lower() and model_lower not in mod.slug:
                    continue

                for gen in mod.generations:
                    # Year filter
                    if effective_year:
                        if effective_year < gen.year_start or (gen.year_end and effective_year > gen.year_end):
                            continue

                    for var in gen.variants:
                        for pt in var.powertrains:
                            if fuel_lower and fuel_lower not in pt.fuel_type.lower():
                                continue
                            if trans_lower and trans_lower not in pt.transmission_type.lower():
                                continue

                            display_year = effective_year or gen.year_start
                            canonical_id = f"{m.slug}::{mod.slug}::{gen.slug}::{display_year}::{var.slug}::{pt.slug}"
                            title = f"{m.name} {mod.name} {var.name} ({display_year})"

                            # Query string search across make, model, variant, fuel
                            if q_lower:
                                search_text = f"{title} {pt.fuel_type} {pt.transmission_type} {mod.body_type}".lower()
                                q_tokens = q_lower.split()
                                if not all(token in search_text for token in q_tokens):
                                    continue

                            results.append({
                                "canonical_vehicle_id": canonical_id,
                                "title": title,
                                "make": m.name,
                                "model": mod.name,
                                "generation": gen.name,
                                "year": display_year,
                                "variant": var.name,
                                "fuel_type": pt.fuel_type,
                                "transmission": pt.transmission_type,
                                "body_type": mod.body_type,
                                "coverage_tier": mod.coverage_tier,
                            })

                            if len(results) >= limit:
                                return results

        return results
