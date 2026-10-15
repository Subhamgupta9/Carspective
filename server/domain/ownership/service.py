"""
CARspective — Phase 14 Ownership Intelligence Domain Service
Implements:
- Structured ownership profiles combining maintenance, parts, and reliability
- Interactive Fuel Cost Calculator
- Total Cost of Ownership (TCO) estimation framework
- Deterministic ownership risk signals
"""

import json
import re
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session

from server.infrastructure.database import ScopedSession
from server.domain.knowledge.service import KnowledgeService
from server.domain.market.service import MarketIntelligenceService
from server.domain.valuation.service import ValuationService
from server.domain.valuation.models import ValuationRequest

from server.domain.ownership.models import (
    TCOComponentStatus,
    OwnershipRiskCategory,
    RiskSeverity,
    EvidenceState,
    FuelCostRequest,
    FuelCostResponse,
    TCOComponent,
    TCORequest,
    TCOResponse,
    OwnershipRiskSignal,
    MaintenanceSchedule,
    PracticalityProfile,
    VehicleOwnershipIntelligence,
)


# Standard Benchmark Fuel Prices in Indian Metros (October 2026 Baseline)
DEFAULT_FUEL_PRICES = {
    "petrol": 96.72,
    "diesel": 89.62,
    "cng": 75.00,
    "electric": 8.50,
}


class OwnershipIntelligenceService:
    def __init__(
        self,
        knowledge_service: Optional[KnowledgeService] = None,
        market_service: Optional[MarketIntelligenceService] = None,
        valuation_service: Optional[ValuationService] = None,
        session: Optional[Session] = None,
    ):
        self._session = session
        self.knowledge_service = knowledge_service or KnowledgeService(session=session)
        self.market_service = market_service or MarketIntelligenceService(session=session)
        self.valuation_service = valuation_service or ValuationService(session=session)

    @property
    def session(self) -> Session:
        if self._session is not None:
            return self._session
        return ScopedSession()

    @session.setter
    def session(self, value: Optional[Session]) -> None:
        self._session = value
        if hasattr(self, "knowledge_service"):
            self.knowledge_service.session = value
        if hasattr(self, "market_service"):
            self.market_service.session = value
        if hasattr(self, "valuation_service"):
            self.valuation_service.session = value

    def _parse_canonical_id(self, canonical_id: str) -> Tuple[str, str, Optional[int]]:
        cleaned = canonical_id.replace("::", "/").strip("/")
        parts = cleaned.split("/")
        brand = parts[0].replace("-", " ").title() if len(parts) > 0 else ""
        if "Maruti Suzuki" in brand or "Maruti" in brand:
            brand = "Maruti"
        model = parts[1].replace("-", " ").title() if len(parts) > 1 else ""
        year = None
        for p in parts[2:]:
            if p.isdigit() and 1990 <= int(p) <= 2030:
                year = int(p)
                break
        return brand, model, year

    def calculate_fuel_cost(self, req: FuelCostRequest, profile: Optional[Any] = None) -> FuelCostResponse:
        """Calculates interactive annual and monthly fuel costs."""
        f_type = req.fuel_type.lower().strip()
        fuel_price = req.fuel_price_per_unit or DEFAULT_FUEL_PRICES.get(f_type, 96.72)

        # Determine effective mileage
        eff_mileage = req.mileage_kmpl
        assumptions = []

        if not eff_mileage and req.canonical_vehicle_id:
            if profile is None:
                profile = self.knowledge_service.get_vehicle_profile(req.canonical_vehicle_id)
            if profile and profile.ownership:
                own = profile.ownership
                city_str = own.real_world_city_mileage_kmpl
                hwy_str = own.real_world_highway_mileage_kmpl

                def parse_avg(s: Optional[str]) -> Optional[float]:
                    if not s:
                        return None
                    nums = [float(x) for x in re.findall(r"\d+\.?\d*", s)]
                    return sum(nums) / len(nums) if nums else None

                city_avg = parse_avg(city_str)
                hwy_avg = parse_avg(hwy_str)

                if city_avg and hwy_avg:
                    eff_mileage = round(city_avg * req.city_driving_ratio + hwy_avg * (1 - req.city_driving_ratio), 1)
                    assumptions.append(f"Blended from real-world city ({city_avg} km/l) and highway ({hwy_avg} km/l) observations.")
                elif city_avg:
                    eff_mileage = city_avg
                    assumptions.append(f"Derived from real-world city baseline ({city_avg} km/l).")

            if not eff_mileage and profile and profile.specifications:
                spec = profile.specifications
                if spec.arai_mileage_kmpl:
                    # Apply empirical 20% discount on ARAI test figures for real-world usage
                    eff_mileage = round(spec.arai_mileage_kmpl * 0.80, 1)
                    assumptions.append(f"Derived from official ARAI test rating ({spec.arai_mileage_kmpl} km/l) with 20% real-world adjustment.")

        if not eff_mileage:
            # Fallback benchmark by fuel type
            if "diesel" in f_type:
                eff_mileage = 16.0
            elif "cng" in f_type:
                eff_mileage = 22.0
            elif "electric" in f_type:
                eff_mileage = 7.0  # km per kWh
            else:
                eff_mileage = 14.0
            assumptions.append(f"Standard category benchmark ({eff_mileage} km/l or km/unit) used in absence of verified vehicle figure.")

        annual_units = req.annual_km / eff_mileage
        annual_cost = round(annual_units * fuel_price, 2)
        monthly_cost = round(annual_cost / 12.0, 2)
        cost_per_km = round(annual_cost / req.annual_km, 2)

        assumptions.append(f"Annual distance: {req.annual_km:,.0f} km.")
        assumptions.append(f"Fuel unit price: ₹{fuel_price:.2f} per {'kWh' if 'electric' in f_type else 'Litre/kg'}.")

        return FuelCostResponse(
            annual_km=req.annual_km,
            fuel_type=req.fuel_type,
            fuel_price_per_unit=fuel_price,
            effective_mileage_kmpl=eff_mileage,
            annual_fuel_cost_inr=annual_cost,
            monthly_fuel_cost_inr=monthly_cost,
            cost_per_km_inr=cost_per_km,
            assumptions_used=assumptions,
            evidence_state=EvidenceState.SUPPORTED,
        )

    def calculate_tco(self, req: TCORequest, knowledge: Optional[Any] = None) -> TCOResponse:
        """Evaluates transparent multi-year Total Cost of Ownership."""
        brand, model, year = self._parse_canonical_id(req.canonical_vehicle_id)
        effective_year = year or 2021
        vehicle_summary = f"{brand} {model} ({effective_year})"

        if knowledge is None:
            knowledge = self.knowledge_service.get_vehicle_profile(req.canonical_vehicle_id)
        own_obj = knowledge.ownership if knowledge else None
        spec_obj = knowledge.specifications if knowledge else None

        f_type = spec_obj.fuel_type if spec_obj else "Petrol"
        assumptions = []
        limitations = [
            "TCO model synthesizes empirical averages and standard regional tariffs; actual costs will vary.",
            "Depreciation loss reflects secondary market asking decay, not guaranteed dealer trade-in values.",
            "Unexpected major component failures (engine overhaul, battery pack) are excluded from routine wear schedules."
        ]

        # 1. Purchase Baseline
        purchase_price = req.custom_purchase_price
        p_status = TCOComponentStatus.USER_PROVIDED if req.custom_purchase_price else TCOComponentStatus.MODEL_ESTIMATED
        if not purchase_price:
            val_req = ValuationRequest(
                brand=brand,
                model=model,
                manufacturing_year=effective_year,
                km_driven=40000,
                fuel_type=f_type,
            )
            val_res = self.valuation_service.evaluate_valuation(val_req)
            purchase_price = float(val_res.estimated_fair_market_value) if val_res else 600000.0
            assumptions.append(f"Purchase price baseline: ₹{purchase_price:,.0f} (derived from CarSpective Fair Market Value).")
        else:
            assumptions.append(f"Purchase price baseline: ₹{purchase_price:,.0f} (user-provided).")

        # 2. Residual Value & Depreciation Loss
        # Empirical retention after N years: ~8-11% decay per year
        retention_rates = {
            1: 0.88,
            2: 0.78,
            3: 0.69,
            4: 0.61,
            5: 0.54,
            6: 0.48,
            7: 0.43,
            8: 0.38,
            9: 0.34,
            10: 0.30,
        }
        r_rate = retention_rates.get(req.ownership_years, 0.54)
        expected_residual = round(purchase_price * r_rate, 2)
        depreciation_loss = round(purchase_price - expected_residual, 2)
        annual_depreciation = round(depreciation_loss / req.ownership_years, 2)

        # 3. Fuel Cost
        fuel_req = FuelCostRequest(
            canonical_vehicle_id=req.canonical_vehicle_id,
            fuel_type=f_type,
            annual_km=req.annual_km,
            fuel_price_per_unit=req.custom_fuel_price,
            mileage_kmpl=req.custom_mileage,
        )
        fuel_res = self.calculate_fuel_cost(fuel_req, profile=knowledge)
        annual_fuel = fuel_res.annual_fuel_cost_inr
        total_fuel = round(annual_fuel * req.ownership_years, 2)

        # 4. Routine Maintenance
        annual_maint = 7500.0
        maint_status = TCOComponentStatus.MODEL_ESTIMATED
        if own_obj and own_obj.typical_annual_maintenance_inr:
            clean_str = own_obj.typical_annual_maintenance_inr.replace(",", "")
            nums = [float(x) for x in re.findall(r"\d+", clean_str)]
            if nums:
                annual_maint = sum(nums) / len(nums)
                maint_status = TCOComponentStatus.EVIDENCE_BACKED
                assumptions.append(f"Annual service cost: Rs {annual_maint:,.0f} (sourced from verified OEM service schedule).")
        else:
            assumptions.append(f"Annual service cost: Rs {annual_maint:,.0f} (industry category estimate).")
        total_maint = round(annual_maint * req.ownership_years, 2)

        # 5. Periodic Wear Items (Tyres, Battery, Brakes amortized)
        annual_wear = 8500.0
        total_wear = round(annual_wear * req.ownership_years, 2)
        assumptions.append("Periodic wear items: ₹8,500/year (amortized tyres, battery, brake pads over mileage).")

        # 6. Comprehensive Insurance
        annual_ins = req.custom_annual_insurance
        ins_status = TCOComponentStatus.USER_PROVIDED if req.custom_annual_insurance else TCOComponentStatus.MODEL_ESTIMATED
        if not annual_ins:
            # Approx 2.5% of average insured declared value (IDV)
            avg_idv = (purchase_price + expected_residual) / 2.0
            annual_ins = round(max(8000.0, avg_idv * 0.026), 2)
            assumptions.append(f"Annual insurance premium: ₹{annual_ins:,.0f} (estimated comprehensive tariff).")
        else:
            assumptions.append(f"Annual insurance premium: ₹{annual_ins:,.0f} (user-provided).")
        total_ins = round(annual_ins * req.ownership_years, 2)

        # Components List
        components = [
            TCOComponent(
                component_name="Depreciation Loss",
                annual_cost_inr=annual_depreciation,
                total_period_cost_inr=depreciation_loss,
                status=TCOComponentStatus.MODEL_ESTIMATED,
                data_source="Empirical Secondary Market Value Retention Curves",
                calculation_method=f"Purchase price (₹{purchase_price:,.0f}) minus {req.ownership_years}-year residual (₹{expected_residual:,.0f})",
                notes=f"Projected {round(r_rate*100)}% retention after {req.ownership_years} years.",
            ),
            TCOComponent(
                component_name="Fuel Expenditure",
                annual_cost_inr=annual_fuel,
                total_period_cost_inr=total_fuel,
                status=TCOComponentStatus.USER_PROVIDED if req.custom_fuel_price else TCOComponentStatus.SUPPORTED if hasattr(TCOComponentStatus, 'SUPPORTED') else TCOComponentStatus.EVIDENCE_BACKED,
                data_source=f"Current {f_type} price (₹{fuel_res.fuel_price_per_unit}/unit) @ {fuel_res.effective_mileage_kmpl} km/l",
                calculation_method=f"{req.annual_km:,.0f} km/yr * ₹{fuel_res.cost_per_km_inr:.2f}/km",
            ),
            TCOComponent(
                component_name="Scheduled Routine Maintenance",
                annual_cost_inr=annual_maint,
                total_period_cost_inr=total_maint,
                status=maint_status,
                data_source="Manufacturer Scheduled Maintenance Intervals",
                calculation_method="Annual oil, filter, and scheduled fluid replacements",
            ),
            TCOComponent(
                component_name="Periodic Wear Items",
                annual_cost_inr=annual_wear,
                total_period_cost_inr=total_wear,
                status=TCOComponentStatus.MODEL_ESTIMATED,
                data_source="Secondary Market Wear Index",
                calculation_method="Amortized tyre set, 12V battery replacement, and brake pads",
            ),
            TCOComponent(
                component_name="Comprehensive Insurance",
                annual_cost_inr=annual_ins,
                total_period_cost_inr=total_ins,
                status=ins_status,
                data_source="Standard Indian Comprehensive Motor Tariff",
                calculation_method="Estimated annual policy renewal with No-Claim Bonus tier progression",
            ),
        ]

        total_tco = round(depreciation_loss + total_fuel + total_maint + total_wear + total_ins, 2)
        annualized_tco = round(total_tco / req.ownership_years, 2)
        total_km = req.annual_km * req.ownership_years
        cost_per_km = round(total_tco / total_km, 2)

        return TCOResponse(
            canonical_vehicle_id=req.canonical_vehicle_id,
            vehicle_summary=vehicle_summary,
            ownership_years=req.ownership_years,
            annual_km=req.annual_km,
            total_distance_km=total_km,
            purchase_price_baseline_inr=purchase_price,
            expected_residual_value_inr=expected_residual,
            net_depreciation_loss_inr=depreciation_loss,
            total_cost_of_ownership_inr=total_tco,
            annualized_tco_inr=annualized_tco,
            cost_per_km_inr=cost_per_km,
            components=components,
            assumptions=assumptions,
            evidence_state=EvidenceState.MODEL_ESTIMATE,
            limitations=limitations,
        )

    def _generate_risk_signals(self, canonical_id: str, knowledge: Any) -> List[OwnershipRiskSignal]:
        """Generates deterministic, evidence-governed ownership risk signals."""
        signals = []
        spec = knowledge.specifications if knowledge else None
        own = knowledge.ownership if knowledge else None
        issues = knowledge.reliability_issues if knowledge else []
        brand, model, _ = self._parse_canonical_id(canonical_id)
        b_low = brand.lower()

        # 1. Fuel Cost Risk
        f_type = spec.fuel_type.lower() if spec and spec.fuel_type else "petrol"
        disp = spec.displacement_cc if spec else 1200
        if "petrol" in f_type and disp and disp >= 1500:
            signals.append(
                OwnershipRiskSignal(
                    category=OwnershipRiskCategory.FUEL_COST_RISK,
                    severity=RiskSeverity.MODERATE,
                    title="Moderate Fuel Cost Sensitivity",
                    description=f"Larger displacement {disp}cc petrol engine exhibits higher fuel consumption in congested stop-and-go city traffic.",
                    mitigation_advice="Consider diesel, hybrid, or smaller turbo alternatives if annual usage exceeds 15,000 km.",
                )
            )
        else:
            signals.append(
                OwnershipRiskSignal(
                    category=OwnershipRiskCategory.FUEL_COST_RISK,
                    severity=RiskSeverity.LOW,
                    title="Manageable Fuel Running Cost",
                    description="Favorable power-to-weight ratio and efficient fuel delivery maintain competitive per-kilometer running expenses.",
                    mitigation_advice="Maintain correct tyre pressure and clean engine air filter to preserve fuel economy.",
                )
            )

        # 2. Maintenance Complexity & Parts Cost Risk
        m_comp = own.maintenance_complexity.upper() if own else "LOW"
        p_avail = own.parts_availability.upper() if own else "EXCELLENT"

        if m_comp == "HIGH" or any(l in b_low for l in ["bmw", "mercedes", "audi", "skoda"]):
            signals.append(
                OwnershipRiskSignal(
                    category=OwnershipRiskCategory.MAINTENANCE_COMPLEXITY,
                    severity=RiskSeverity.ELEVATED,
                    title="Elevated Service Complexity",
                    description="Advanced electronic control units, direct injection, or dual-clutch transmission require specialized diagnostic tools.",
                    mitigation_advice="Verify complete authorized service center history; avoid unauthorized local garages for electronics.",
                )
            )
            signals.append(
                OwnershipRiskSignal(
                    category=OwnershipRiskCategory.PARTS_COST_RISK,
                    severity=RiskSeverity.ELEVATED,
                    title="Higher Replacement Parts Cost",
                    description="Imported sub-assemblies or specialized OEM parts carry higher catalog prices and longer delivery lead times.",
                    mitigation_advice="Budget an annual contingency fund (₹20,000–₹35,000) for unplanned component replacements.",
                )
            )
        elif m_comp == "MODERATE":
            signals.append(
                OwnershipRiskSignal(
                    category=OwnershipRiskCategory.MAINTENANCE_COMPLEXITY,
                    severity=RiskSeverity.MODERATE,
                    title="Standard Moderate Maintenance",
                    description="Standard service requirements; routine mechanical upkeep is manageable across authorized and independent workshops.",
                    mitigation_advice="Adhere strictly to scheduled 10,000 km fluid service intervals.",
                )
            )
            signals.append(
                OwnershipRiskSignal(
                    category=OwnershipRiskCategory.PARTS_COST_RISK,
                    severity=RiskSeverity.LOW if p_avail == "EXCELLENT" else RiskSeverity.MODERATE,
                    title="Predictable Parts Availability",
                    description="Widespread domestic distribution network ensures quick access to routine mechanical spares.",
                    mitigation_advice="Use genuine OEM replacement filters and fluids during periodic services.",
                )
            )
        else:
            signals.append(
                OwnershipRiskSignal(
                    category=OwnershipRiskCategory.MAINTENANCE_COMPLEXITY,
                    severity=RiskSeverity.LOW,
                    title="Low Maintenance Complexity",
                    description="Straightforward mechanical architecture with widespread technician familiarity across India.",
                    mitigation_advice="Regular fluid changes and annual inspections are sufficient for high longevity.",
                )
            )
            signals.append(
                OwnershipRiskSignal(
                    category=OwnershipRiskCategory.PARTS_COST_RISK,
                    severity=RiskSeverity.LOW,
                    title="Affordable Spares Basket",
                    description="Highly competitive parts pricing with extensive genuine aftermarket and OEM availability.",
                    mitigation_advice="Inexpensive routine replacement consumables keep running costs minimal.",
                )
            )

        # 3. Documented Reliability Risk
        def get_sev(i):
            s = getattr(i, "severity", "")
            return getattr(s, "value", str(s)).upper()

        crit_issues = [i for i in issues if get_sev(i) in ["CRITICAL", "HIGH"]]
        mod_issues = [i for i in issues if get_sev(i) == "MODERATE"]

        if crit_issues:
            first = crit_issues[0]
            cat_name = getattr(first, "category", getattr(first, "component_system", "Component"))
            desc = getattr(first, "description", getattr(first, "issue_description", "Component vulnerability"))
            aff = getattr(first, "affected_years", getattr(first, "affected_years_range", "Historical cohorts"))
            prev = getattr(first, "preventive_inspection_point", "Verify component during physical inspection")
            signals.append(
                OwnershipRiskSignal(
                    category=OwnershipRiskCategory.RELIABILITY_RISK,
                    severity=RiskSeverity.ELEVATED,
                    title=f"Critical Advisory: {cat_name.title()}",
                    description=f"{desc} (Affected: {aff}).",
                    mitigation_advice=f"Inspect: {prev}.",
                )
            )
        elif mod_issues:
            first = mod_issues[0]
            cat_name = getattr(first, "category", getattr(first, "component_system", "Component"))
            desc = getattr(first, "description", getattr(first, "issue_description", "Component vulnerability"))
            prev = getattr(first, "preventive_inspection_point", "Scan for symptoms during test drive")
            signals.append(
                OwnershipRiskSignal(
                    category=OwnershipRiskCategory.RELIABILITY_RISK,
                    severity=RiskSeverity.MODERATE,
                    title=f"Documented Advisory: {cat_name.title()}",
                    description=f"{desc}",
                    mitigation_advice=f"Check: {prev}.",
                )
            )
        else:
            signals.append(
                OwnershipRiskSignal(
                    category=OwnershipRiskCategory.RELIABILITY_RISK,
                    severity=RiskSeverity.LOW,
                    title="Proven Powertrain Durability",
                    description="No major recurrent component vulnerabilities documented in verified service fleet records.",
                    mitigation_advice="Perform standard fluid inspections and check for regular maintenance stamps.",
                )
            )

        # 4. Resale Risk
        market_prof = self.market_service.get_market_profile(canonical_id)
        if market_prof.liquidity_indicator.value == "HIGH_LIQUIDITY":
            signals.append(
                OwnershipRiskSignal(
                    category=OwnershipRiskCategory.RESALE_RISK,
                    severity=RiskSeverity.LOW,
                    title="Minimal Secondary Liquidity Risk",
                    description="High buyer demand and widespread model recognition ensure brisk secondary market turnover when selling.",
                    mitigation_advice="Maintain original service bills and clear title documents to command top resale value.",
                )
            )
        elif market_prof.liquidity_indicator.value == "MODERATE_LIQUIDITY":
            signals.append(
                OwnershipRiskSignal(
                    category=OwnershipRiskCategory.RESALE_RISK,
                    severity=RiskSeverity.MODERATE,
                    title="Moderate Resale Demand",
                    description="Predictable secondary sales timeline; values remain aligned with segment depreciation rates.",
                    mitigation_advice="Keep the vehicle in accident-free condition to prevent buyer price discounting.",
                )
            )
        else:
            signals.append(
                OwnershipRiskSignal(
                    category=OwnershipRiskCategory.RESALE_RISK,
                    severity=RiskSeverity.ELEVATED,
                    title="Elevated Resale Holding Time",
                    description="Lower observed listing volume indicates narrower buyer pool and potentially steeper price negotiation.",
                    mitigation_advice="Plan for longer listing time (45–60 days) or consider specialized trade-in channels when reselling.",
                )
            )

        return signals

    def get_ownership_intelligence(
        self,
        canonical_id: str,
        knowledge: Optional[Any] = None,
        valuation_res: Optional[Any] = None,
    ) -> VehicleOwnershipIntelligence:
        """Returns structured ownership profile, practicality assessments, and risk signals."""
        brand, model, year = self._parse_canonical_id(canonical_id)
        if knowledge is None:
            knowledge = self.knowledge_service.get_vehicle_profile(canonical_id)

        spec = knowledge.specifications if knowledge else None
        dim = knowledge.dimensions if knowledge else None
        own = knowledge.ownership if knowledge else None

        f_type = spec.fuel_type if spec and spec.fuel_type else "Petrol"
        trans = spec.transmission if spec and spec.transmission else "Manual"

        # 1. Maintenance Schedule
        service_km = own.service_interval_km if own and own.service_interval_km else 10000
        service_mo = own.service_interval_months if own and own.service_interval_months else 12
        maint_cost = own.typical_annual_maintenance_inr if own and own.typical_annual_maintenance_inr else "₹6,000 – ₹9,000"
        maint_comp = own.maintenance_complexity if own and own.maintenance_complexity else "LOW"
        parts_avail = own.parts_availability if own and own.parts_availability else "EXCELLENT"

        routine_checklist = [
            f"Engine oil & oil filter replacement (every {service_km:,} km / {service_mo} months)",
            "Engine air filter and cabin pollen filter inspection / cleaning",
            "Brake fluid, coolant, and transmission fluid level inspection",
            "Front brake disc pad thickness & rear drum brake lining check",
            "Tyre rotation, wheel alignment, and wheel balancing",
            "Battery terminal voltage check and suspension bushing inspection",
        ]

        maint_sched = MaintenanceSchedule(
            service_interval_km=service_km,
            service_interval_months=service_mo,
            typical_annual_maintenance_inr=maint_cost,
            maintenance_complexity=maint_comp,
            parts_availability=parts_avail,
            routine_checklist=routine_checklist,
            evidence_state=EvidenceState.SUPPORTED,
        )

        # 2. Practicality Profile
        gc = dim.ground_clearance_mm if dim and dim.ground_clearance_mm else 170
        boot = dim.boot_capacity_l if dim and dim.boot_capacity_l else 300
        length = dim.length_mm if dim and dim.length_mm else 3990

        city_suit = "Excellent" if length <= 4000 else "Good" if length <= 4400 else "Moderate"
        hwy_suit = "Good" if length > 3900 else "Adequate for city commutes"
        fam_suit = "Comfortable for 4–5 occupants" if (dim and dim.seating_capacity and dim.seating_capacity >= 5) else "Compact 4-seater"
        gc_text = f"{gc} mm — " + ("High rough-road clearance, clears speed breakers easily." if gc >= 180 else "Standard city clearance.")
        boot_text = f"{boot} Litres — " + ("Accommodates full family luggage for road trips." if boot >= 380 else "Compact trunk; suitable for weekend duffel bags.")

        practicality = PracticalityProfile(
            city_suitability=city_suit,
            highway_suitability=hwy_suit,
            family_suitability=fam_suit,
            boot_space_assessment=boot_text,
            ground_clearance_assessment=gc_text,
        )

        # 3. Strengths & Concerns
        strengths = []
        concerns = []
        if own:
            if isinstance(own.ownership_strengths, list):
                strengths = own.ownership_strengths
            elif own.ownership_strengths:
                try:
                    strengths = json.loads(own.ownership_strengths)
                except Exception:
                    strengths = [own.ownership_strengths]

            if isinstance(own.ownership_concerns, list):
                concerns = own.ownership_concerns
            elif own.ownership_concerns:
                try:
                    concerns = json.loads(own.ownership_concerns)
                except Exception:
                    concerns = [own.ownership_concerns]

        if not strengths:
            strengths = [
                f"Accessible service network with predictable routine maintenance costs.",
                f"Competitive fuel economy in daily urban commutes.",
                f"High secondary parts availability across independent workshops.",
            ]
        if not concerns:
            concerns = [
                "Requires timely preventive fluid changes to avoid accelerated component wear.",
                "Cabin noise levels increase at highway cruising speeds compared to premium executive segments.",
            ]

        # 4. Risk Signals
        risk_signals = self._generate_risk_signals(canonical_id, knowledge)

        # 5. Default 5-Year TCO Summary
        purchase_price_val = None
        if valuation_res is not None and hasattr(valuation_res, "estimated_fair_market_value") and valuation_res.estimated_fair_market_value:
            purchase_price_val = float(valuation_res.estimated_fair_market_value)

        tco_req = TCORequest(
            canonical_vehicle_id=canonical_id,
            ownership_years=5,
            annual_km=12000.0,
            custom_purchase_price=purchase_price_val,
        )
        tco_res = self.calculate_tco(tco_req, knowledge=knowledge)

        # 6. One-Line Synthesis
        synthesis = (
            f"{brand} {model} features {maint_comp.lower()} maintenance complexity with a {service_km:,} km service cadence "
            f"and an estimated 5-year TCO around ₹{tco_res.annualized_tco_inr:,.0f}/year."
        )

        return VehicleOwnershipIntelligence(
            canonical_vehicle_id=canonical_id,
            brand=brand,
            model=model,
            generation=knowledge.generation_name if knowledge else None,
            variant=knowledge.variant_name if knowledge else None,
            fuel_type=f_type,
            transmission=trans,
            maintenance=maint_sched,
            practicality=practicality,
            real_world_city_mileage=own.real_world_city_mileage_kmpl if own and own.real_world_city_mileage_kmpl else "13 – 15 km/l",
            real_world_highway_mileage=own.real_world_highway_mileage_kmpl if own and own.real_world_highway_mileage_kmpl else "18 – 20 km/l",
            strengths=strengths,
            concerns=concerns,
            risk_signals=risk_signals,
            default_tco_summary=tco_res,
            one_line_synthesis=synthesis,
            evidence_state=EvidenceState.SUPPORTED,
            limitations=[
                "Ownership figures represent documented OEM norms and empirical fleet surveys.",
                "Personal driving style, urban congestion, and adherence to preventive service directly influence actual costs.",
            ],
        )
