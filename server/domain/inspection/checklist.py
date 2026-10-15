"""
CARspective — Canonical Inspection Checklist Catalog (Version 2.0.0)
Comprehensive, evidence-based master registry of used-car inspection items
covering all 7 canonical categories:
1. Documentation (10 items)
2. Exterior (8 items)
3. Engine & Powertrain (9 items)
4. Underbody & Structure (6 items)
5. Interior (6 items)
6. Safety (5 items)
7. Test Drive (5 items)

Architectural Extension & Governance:
- Phase 7 Canonical Baseline: 45 items across 7 categories
- Catalog Version 2.0.0 Extension: 49 standardized items
- Formal Extension Items:
  1. DOC_VIN_CHASSIS_STAMPING (Documentation): Metal VIN stamping integrity
  2. EXT_REPAINT_OVERSPRAY_EVIDENCE (Exterior): Paint overspray on trim/seals
  3. ENG_DIESEL_DPF_GLOW_PLUG (Engine & Powertrain): Modern BS6 DPF / turbo health
  4. UND_EXHAUST_SYSTEM_CAT_CONV (Underbody & Structure): Catalytic converter & exhaust piping
- Personalization Invariant:
  Phase 15 decision personalization NEVER adds or removes items.
  It strictly reprioritizes and reorders the canonical catalog.
"""

from typing import List, Dict, Any
from server.domain.inspection.models import (
    ChecklistItem,
    InspectionCategory,
    ImportanceLevel,
    RiskSeverity,
    EvidenceState,
)

INSPECTION_CATALOG_VERSION: str = "2.0.0"
PHASE7_CANONICAL_BASELINE_COUNT: int = 45
CURRENT_CANONICAL_CATALOG_COUNT: int = 49

CANONICAL_CHECKLIST_CATALOG: List[ChecklistItem] = [
    # ────────────────────────────────────────────────────────────────
    # A. DOCUMENTATION (10 Items)
    # ────────────────────────────────────────────────────────────────
    ChecklistItem(
        item_id="DOC_RC_VERIFICATION",
        category=InspectionCategory.DOCUMENTATION,
        title="Registration Certificate (RC) Authenticity & Details",
        purpose="Confirms legal vehicle registration, ownership identity, hypothecation status, and state jurisdiction.",
        importance=ImportanceLevel.CRITICAL,
        applicable_to="ALL",
        inspection_method="Examine physical smart card or digital Parivahan mParivahan/DigiLocker record. Verify chassis and engine numbers character-by-character.",
        expected_observation="Original RC present; details match Parivahan database exactly; no tampered fonts or altered micro-chips.",
        warning_signs=[
            "Duplicate RC without credible FIR / police lost-report",
            "Mismatch between physical vehicle chassis stamping and RC text",
            "Expired registration or unauthorized commercial-to-private conversion"
        ],
        verification_action="Cross-verify live registration status on VAHAN / Parivahan national vehicle register portal.",
        evidence_required="Original Registration Certificate smart card / DigiLocker official document",
        evidence_state=EvidenceState.SUPPORTED,
        severity_if_failed=RiskSeverity.CRITICAL,
        professional_inspection_required=False,
        notes="A vehicle with compromised or disputed title cannot be legally transferred."
    ),
    ChecklistItem(
        item_id="DOC_VIN_CHASSIS_STAMPING",
        category=InspectionCategory.DOCUMENTATION,
        title="Chassis / VIN Physical Stamping Integrity",
        purpose="Guarantees the physical vehicle corresponds to the documentation and has not undergone identity theft or front-clip replacement.",
        importance=ImportanceLevel.CRITICAL,
        applicable_to="ALL",
        inspection_method="Locate primary VIN stamped into metal on firewall or under front passenger seat. Check VIN plate on dashboard/B-pillar.",
        expected_observation="Clean, factory-stamped characters with uniform font, spacing, and depth; surrounding metal bears original paint and factory sealant.",
        warning_signs=[
            "Grinding marks, uneven character spacing, or restamped fonts",
            "Welding seams or cut lines surrounding the VIN stamping plate",
            "Corrosion concealing VIN numbers or missing OEM VIN rivet plate"
        ],
        verification_action="Physically inspect stamped numbers; compare directly against RC and insurance certificate.",
        evidence_required="Direct physical inspection of vehicle metal chassis stamping",
        evidence_state=EvidenceState.VERIFIED,
        severity_if_failed=RiskSeverity.CRITICAL,
        professional_inspection_required=True,
        notes="Altered chassis stampings indicate total-loss reconstruction or stolen vehicle cloning."
    ),
    ChecklistItem(
        item_id="DOC_ENGINE_NUMBER_STAMPING",
        category=InspectionCategory.DOCUMENTATION,
        title="Engine Block Serial Number Verification",
        purpose="Verifies the original engine remains fitted or any replacement was legally endorsed onto the RC.",
        importance=ImportanceLevel.HIGH,
        applicable_to="ALL",
        inspection_method="Locate engine number engraved on engine block mating face. Clean grease with rag if necessary and compare against RC.",
        expected_observation="Original engine number intact and matching RC document perfectly.",
        warning_signs=[
            "Engine number does not match RC",
            "Grinding marks on engine serial boss",
            "Unendorsed engine swap from salvage vehicle"
        ],
        verification_action="Check engine number engraving against RC; if changed, request RTO endorsement invoice.",
        evidence_required="Physical engine block engraving inspection",
        evidence_state=EvidenceState.SUPPORTED,
        severity_if_failed=RiskSeverity.HIGH,
        professional_inspection_required=False,
        notes="Mismatched engine numbers can cause RTO registration transfer rejection and insurance claim repudiation."
    ),
    ChecklistItem(
        item_id="DOC_INSURANCE_VALIDITY",
        category=InspectionCategory.DOCUMENTATION,
        title="Insurance Policy Validity & Coverage Tier",
        purpose="Ensures ongoing liability coverage and protects against uninsured transit risks.",
        importance=ImportanceLevel.HIGH,
        applicable_to="ALL",
        inspection_method="Examine insurance certificate validity dates, coverage type (Comprehensive vs Third Party), and Insured Declared Value (IDV).",
        expected_observation="Active comprehensive policy with IDV corresponding to current fair market value.",
        warning_signs=[
            "Expired insurance policy",
            "Only third-party policy active for a high-value or late-model vehicle",
            "Significant gap in insurance renewal history"
        ],
        verification_action="Verify policy status on insurance company customer portal or IIB (Insurance Information Bureau).",
        evidence_required="Active Insurance Certificate policy schedule",
        evidence_state=EvidenceState.SUPPORTED,
        severity_if_failed=RiskSeverity.MEDIUM,
        professional_inspection_required=False,
        notes="Expired insurance requires mandatory re-inspection by insurer before policy transfer."
    ),
    ChecklistItem(
        item_id="DOC_INSURANCE_CLAIM_HISTORY",
        category=InspectionCategory.DOCUMENTATION,
        title="No Claim Bonus (NCB) & Insurance Claim History",
        purpose="Uncovers past accident repair claims that may not be disclosed by the seller.",
        importance=ImportanceLevel.CRITICAL,
        applicable_to="ALL",
        inspection_method="Inspect NCB percentage on current insurance policy. An older vehicle with 0% NCB often indicates a recent accident claim.",
        expected_observation="NCB tracks predictably with vehicle age (20% year 2, up to 50% year 6) if no claims made.",
        warning_signs=[
            "0% NCB on a 4-year-old vehicle without documented rationale",
            "Frequent insurance policy carrier switching to obscure past claims",
            "Seller denies accidents despite recent claim history"
        ],
        verification_action="Request insurer claims history statement or verify claims track via insurer policy portal.",
        evidence_required="Insurance policy NCB schedule / claims report",
        evidence_state=EvidenceState.EMPIRICAL,
        severity_if_failed=RiskSeverity.HIGH,
        professional_inspection_required=True,
        notes="A 0% NCB on an older vehicle is an empirical signal warranting thorough structural accident inspection."
    ),
    ChecklistItem(
        item_id="DOC_SERVICE_HISTORY_RECORDS",
        category=InspectionCategory.DOCUMENTATION,
        title="Authorized Service Records & Mileage Continuity",
        purpose="Confirms scheduled maintenance adherence and provides tamper-proof mileage benchmarks.",
        importance=ImportanceLevel.CRITICAL,
        applicable_to="ALL",
        inspection_method="Review authorized dealer stamped service booklet and itemized tax invoices showing date, mileage, and parts replaced.",
        expected_observation="Regular service intervals (e.g. every 10,000 km or 1 year) with chronological mileage progression.",
        warning_signs=[
            "Complete absence of service records or sudden gap in records for last 30,000+ km",
            "Mileage on last service invoice higher than current odometer display (tampering)",
            "Routine periodic services missed or major timing belt/fluid intervals ignored"
        ],
        verification_action="Cross-check vehicle service history directly with the authorized OEM dealer network database.",
        evidence_required="Itemized authorized service workshop invoices and digital service record",
        evidence_state=EvidenceState.VERIFIED,
        severity_if_failed=RiskSeverity.HIGH,
        professional_inspection_required=False,
        notes="Authorized service history is the single most reliable predictor of long-term powertrain durability."
    ),
    ChecklistItem(
        item_id="DOC_OWNERSHIP_CHAIN",
        category=InspectionCategory.DOCUMENTATION,
        title="Ownership Count & Seller Identity Continuity",
        purpose="Confirms true owner count and ensures the seller has legal title to convey the vehicle.",
        importance=ImportanceLevel.HIGH,
        applicable_to="ALL",
        inspection_method="Check owner number serial on RC (1, 2, 3...). Verify seller photo ID matches RC registered name.",
        expected_observation="Owner number matches listing claim; seller is registered owner or authorized dealer with valid POA.",
        warning_signs=[
            "Vehicle registered to 3rd or 4th owner while advertised as single-owner",
            "Seller is an individual third-party without title or signed Form 29/30 from registered owner",
            "Company-owned commercial/fleet vehicle represented as private personal car"
        ],
        verification_action="Verify owner sequence number on VAHAN and confirm seller identity document.",
        evidence_required="Government ID of seller matching RC registered owner name",
        evidence_state=EvidenceState.SUPPORTED,
        severity_if_failed=RiskSeverity.HIGH,
        professional_inspection_required=False,
        notes="Purchasing from an intermediary without signed transfer forms risks ownership transfer disputes."
    ),
    ChecklistItem(
        item_id="DOC_NOC_HYPOTHECATION",
        category=InspectionCategory.DOCUMENTATION,
        title="Bank Loan Hypothecation & NOC Status",
        purpose="Confirms vehicle is free of outstanding bank loan encumbrances or finance liens.",
        importance=ImportanceLevel.CRITICAL,
        applicable_to="ALL",
        inspection_method="Inspect RC for 'Hypothecated to [Bank]'. If hypothecated, require original Bank NOC and Form 35.",
        expected_observation="RC shows no hypothecation, or seller provides valid original Bank NOC and Form 35 for loan removal.",
        warning_signs=[
            "Hypothecation on RC with no bank clearance NOC",
            "Expired bank NOC (bank NOCs typically valid for 90 days)",
            "Seller requests payment before paying off pending auto loan"
        ],
        verification_action="Verify loan clearance letter with lending institution before releasing final funds.",
        evidence_required="Original Bank No Objection Certificate (NOC) and RTO Form 35",
        evidence_state=EvidenceState.SUPPORTED,
        severity_if_failed=RiskSeverity.CRITICAL,
        professional_inspection_required=False,
        notes="A vehicle with an active loan encumbrance cannot be transferred by RTO until the lien is legally removed."
    ),
    ChecklistItem(
        item_id="DOC_PUC_CERTIFICATE",
        category=InspectionCategory.DOCUMENTATION,
        title="Pollution Under Control (PUC) Certificate",
        purpose="Validates statutory emission compliance and provides recent third-party date/mileage evidence.",
        importance=ImportanceLevel.LOW,
        applicable_to="ALL",
        inspection_method="Review latest online PUC certificate QR code on Parivahan portal.",
        expected_observation="Valid PUC certificate with emission levels comfortably within BS4/BS6 threshold limits.",
        warning_signs=[
            "Expired PUC certificate",
            "Unusually high CO or hydrocarbon emission readings indicating catalytic converter failure",
            "Mileage on recent PUC conflicts with current odometer"
        ],
        verification_action="Scan PUC QR code to verify live certificate on Parivahan portal.",
        evidence_required="Valid PUC Certificate with Parivahan portal record",
        evidence_state=EvidenceState.SUPPORTED,
        severity_if_failed=RiskSeverity.LOW,
        professional_inspection_required=False,
        notes="Minor compliance document, but abnormal emission levels point to engine sensor or catalytic failure."
    ),
    ChecklistItem(
        item_id="DOC_ODOMETER_CONSISTENCY",
        category=InspectionCategory.DOCUMENTATION,
        title="Multi-Source Odometer Reading Consistency",
        purpose="Detects fraudulent digital or analogue odometer rollback and meter tampering.",
        importance=ImportanceLevel.CRITICAL,
        applicable_to="ALL",
        inspection_method="Compare current instrument cluster reading against service records, insurance renewals, and PUC logs.",
        expected_observation="Odometer reading is strictly greater than all historical records and displays consistent annual accumulation (8,000–15,000 km/year).",
        warning_signs=[
            "Service record from 2 years ago shows 75,000 km, but current odometer reads 45,000 km",
            "Tool marks or scratches on instrument cluster glass/bezel indicating disassembly",
            "Heavy steering, pedal, and seat bolster wear that contradicts an unusually low claimed mileage"
        ],
        verification_action="Request dealer service printout showing recorded mileage at every workshop visit.",
        evidence_required="Authorized workshop chronological service log",
        evidence_state=EvidenceState.VERIFIED,
        severity_if_failed=RiskSeverity.CRITICAL,
        professional_inspection_required=True,
        notes="Odometer tampering is a criminal fraud that invalidates all pricing and maintenance assumptions."
    ),

    # ────────────────────────────────────────────────────────────────
    # B. EXTERIOR (8 Items)
    # ────────────────────────────────────────────────────────────────
    ChecklistItem(
        item_id="EXT_PANEL_GAPS_ALIGNMENT",
        category=InspectionCategory.EXTERIOR,
        title="Body Panel Gap Uniformity & Alignment",
        purpose="Detects structural collision impacts, frame misalignment, or aftermarket panel replacement.",
        importance=ImportanceLevel.CRITICAL,
        applicable_to="ALL",
        inspection_method="Run a finger or plastic gauge along panel gaps (hood-to-fender, door-to-pillar, boot-to-quarter-panel) on both left and right sides.",
        expected_observation="Uniform, consistent gaps (typically 3–5 mm) identical on left and right sides of the vehicle.",
        warning_signs=[
            "Uneven gaps that widen or pinch shut along the seam",
            "Hood or trunk sitting higher on one side than the other",
            "Doors requiring extra force to latch flush into door frame"
        ],
        verification_action="Measure gaps on both sides; inspect panel mounting bolts for stripped paint or socket wrench marks.",
        evidence_required="Visual and physical gap measurement inspection",
        evidence_state=EvidenceState.SUPPORTED,
        severity_if_failed=RiskSeverity.HIGH,
        professional_inspection_required=True,
        notes="Irregular panel gaps strongly indicate poorly repaired collision damage."
    ),
    ChecklistItem(
        item_id="EXT_PAINT_CONSISTENCY_MISMATCH",
        category=InspectionCategory.EXTERIOR,
        title="Paint Color Consistency & Texture (Orange Peel)",
        purpose="Identifies repainted body panels resulting from accidents, side swipes, or rust repairs.",
        importance=ImportanceLevel.HIGH,
        applicable_to="ALL",
        inspection_method="Inspect the vehicle in direct natural daylight from various angles. Check for slight color shade variations or excessive wavy texture (orange peel).",
        expected_observation="Consistent gloss, smooth reflection, and exact color match across all contiguous metal and plastic panels.",
        warning_signs=[
            "Noticeable color shade discrepancy between door and adjacent fender",
            "Dull, cloudy, or coarse orange peel texture on one panel compared to others",
            "Paint thickness gauge readings exceeding 200–250 microns (factory is typically 90–140 microns)"
        ],
        verification_action="Use a digital coating thickness gauge or examine panel reflections under sunlight.",
        evidence_required="Physical paint thickness and visual color inspection",
        evidence_state=EvidenceState.SUPPORTED,
        severity_if_failed=RiskSeverity.MEDIUM,
        professional_inspection_required=False,
        notes="Repaint on a bumper is common urban cosmetic maintenance; repaint on roof, A-pillar, or quarter panel signals major collision."
    ),
    ChecklistItem(
        item_id="EXT_REPAINT_OVERSPRAY_EVIDENCE",
        category=InspectionCategory.EXTERIOR,
        title="Paint Overspray on Rubber Seals & Trim",
        purpose="Definitive physical evidence of non-factory body shop repainting.",
        importance=ImportanceLevel.HIGH,
        applicable_to="ALL",
        inspection_method="Inspect window weatherstripping, rubber door seals, wheel well liners, and headlamp edges for paint residue.",
        expected_observation="Rubber beading and plastic moldings are completely clean of paint; crisp unmasked edges.",
        warning_signs=[
            "Paint residue or overspray mist on black rubber window seals",
            "Clear coat tape lines visible when opening doors and inspecting inner jambs",
            "Overspray inside engine bay or on headlight housing plastics"
        ],
        verification_action="Peel back door seal edges slightly to inspect for masking tape lines.",
        evidence_required="Close-up physical inspection of rubber trim and apertures",
        evidence_state=EvidenceState.SUPPORTED,
        severity_if_failed=RiskSeverity.MEDIUM,
        professional_inspection_required=False,
        notes="Overspray proves the panel was repainted, confirming repairs occurred."
    ),
    ChecklistItem(
        item_id="EXT_DENTS_SCRATCHES_CORROSION",
        category=InspectionCategory.EXTERIOR,
        title="Body Dents, Deep Scratches & Surface Rust",
        purpose="Assesses cosmetic degradation and potential sheet-metal corrosion progression.",
        importance=ImportanceLevel.MEDIUM,
        applicable_to="ALL",
        inspection_method="Walk around vehicle inspecting rocker panels, lower door sills, wheel arch lips, and boot lid.",
        expected_observation="Normal minor stone chips commensurate with age; no bare metal rust bubbles or perforated metal.",
        warning_signs=[
            "Bubbling paint on door bottom edges or wheel arches indicating rust from inside",
            "Deep metal-exposing gouges left untreated and corroding",
            "Major denting along structural rocker sill beneath doors"
        ],
        verification_action="Inspect under wheel arches and along lower sill pinch welds.",
        evidence_required="Direct physical inspection of exterior panels",
        evidence_state=EvidenceState.SUPPORTED,
        severity_if_failed=RiskSeverity.MEDIUM,
        professional_inspection_required=False,
        notes="Surface scratches are minor cosmetic issues; bubbling rust along rocker sills is costly to remediate."
    ),
    ChecklistItem(
        item_id="EXT_STRUCTURAL_GLASS_OEM",
        category=InspectionCategory.EXTERIOR,
        title="Windshield & Window Glass OEM Markings",
        purpose="Verifies whether vehicle suffered major impact causing windshield or side glass breakage.",
        importance=ImportanceLevel.HIGH,
        applicable_to="ALL",
        inspection_method="Check OEM manufacturer logo and manufacturing year/month codes etched in bottom corner of all windows.",
        expected_observation="All glass panels bear identical OEM markings (e.g. Asahi, Saint-Gobain, Fuyao) and match vehicle manufacture year.",
        warning_signs=[
            "Front windshield or side glass bears non-OEM aftermarket brand",
            "Glass date code newer than vehicle model year (e.g. 2023 glass on 2019 vehicle)",
            "Messy polyurethane sealant around windshield perimeter indicating replacement"
        ],
        verification_action="Check etched manufacturing codes on front windshield, 4 door glasses, and rear quarter glasses.",
        evidence_required="Direct visual inspection of OEM glass markings",
        evidence_state=EvidenceState.VERIFIED,
        severity_if_failed=RiskSeverity.HIGH,
        professional_inspection_required=True,
        notes="A replaced front windshield is common from stone chips; replaced side or rear quarter glass strongly implies collision or break-in."
    ),
    ChecklistItem(
        item_id="EXT_LIGHTING_ASSEMBLY_FIT",
        category=InspectionCategory.EXTERIOR,
        title="Headlamps & Tail Lamps Alignment & Markings",
        purpose="Detects front-end or rear-end impact repairs where lighting was replaced.",
        importance=ImportanceLevel.MEDIUM,
        applicable_to="ALL",
        inspection_method="Check headlight and taillight alignment, lens clarity, and OEM logos molded into lens plastic.",
        expected_observation="Both headlamps have identical clarity and aging; OEM manufacturer logos match on left and right.",
        warning_signs=[
            "One brand new crystal-clear headlight while the other is aged and yellowed",
            "Broken mounting plastic tabs repaired with epoxy/glue inside engine bay",
            "Moisture condensation droplets trapped inside lamp housing"
        ],
        verification_action="Inspect headlight mounting tabs inside engine compartment for cracks or non-factory bolts.",
        evidence_required="Visual inspection of lighting assemblies and inner brackets",
        evidence_state=EvidenceState.SUPPORTED,
        severity_if_failed=RiskSeverity.MEDIUM,
        professional_inspection_required=False,
        notes="One new headlight almost always points to a front corner collision repair."
    ),
    ChecklistItem(
        item_id="EXT_TYRE_TREAD_UNEVEN_WEAR",
        category=InspectionCategory.EXTERIOR,
        title="Tyre Tread Depth, Age & Uneven Wear Patterns",
        purpose="Assesses tyre replacement expenditure and detects severe suspension/alignment or chassis geometry defects.",
        importance=ImportanceLevel.HIGH,
        applicable_to="ALL",
        inspection_method="Measure tread depth across all 4 tyres using depth gauge or coin. Read 4-digit DOT date code (e.g. 2421 = 24th week of 2021).",
        expected_observation="Minimum 3 mm tread across entire width; even wear across inner, center, and outer shoulders; age under 5 years.",
        warning_signs=[
            "Heavy wear on inner or outer shoulder only (feathering/camber wear from bent suspension)",
            "Tyres older than 6 years with visible sidewall dry rot cracking",
            "Bulges, cuts, or cords visible on sidewalls (immediate blowout hazard)"
        ],
        verification_action="Inspect tread wear indicators and sidewall manufacturing DOT code on all 4 tyres plus spare.",
        evidence_required="Direct measurement of tread depth and DOT date inspection",
        evidence_state=EvidenceState.SUPPORTED,
        severity_if_failed=RiskSeverity.HIGH,
        professional_inspection_required=True,
        notes="Uneven tyre wear that cannot be fixed by wheel alignment indicates bent suspension arms or structural twist."
    ),
    ChecklistItem(
        item_id="EXT_WHEEL_RIMS_CONDITION",
        category=InspectionCategory.EXTERIOR,
        title="Alloy Wheel Rims Bends, Cracks & Curb Rash",
        purpose="Checks for high-speed pothole impact damage that compromises high-speed safety.",
        importance=ImportanceLevel.MEDIUM,
        applicable_to="ALL",
        inspection_method="Inspect inner and outer lips of all 4 alloy rims. Check for welded repairs or bent rim barrels.",
        expected_observation="Round rims free of welded crack repairs or flat spots; minor cosmetic curb rash is acceptable.",
        warning_signs=[
            "Visible dent or bend on inner rim lip from pothole strike",
            "Welding marks on alloy spoke or barrel (compromised structural alloy)",
            "Excessive balancing weights (more than 60–80g) indicating severely unbalanced rim"
        ],
        verification_action="Inspect rim perimeter visually and feel inner barrel for flat spots.",
        evidence_required="Visual inspection of rim inner and outer lips",
        evidence_state=EvidenceState.SUPPORTED,
        severity_if_failed=RiskSeverity.MEDIUM,
        professional_inspection_required=False,
        notes="Welded alloy wheels are unsafe for highway use and must be replaced immediately."
    ),

    # ────────────────────────────────────────────────────────────────
    # C. ENGINE & POWERTRAIN (9 Items)
    # ────────────────────────────────────────────────────────────────
    ChecklistItem(
        item_id="ENG_COLD_START_CRANKING",
        category=InspectionCategory.ENGINE_AND_POWERTRAIN,
        title="Cold Start Cranking, Idle & Starter Performance",
        purpose="Detects weak battery, failing starter motor, low cylinder compression, or cold fueling issues.",
        importance=ImportanceLevel.HIGH,
        applicable_to="ALL",
        inspection_method="Touch engine valve cover to verify engine is truly cold before starting. Turn key and observe cranking speed and firing time.",
        expected_observation="Engine cranks briskly and fires within 1–2 seconds; RPM settles smoothly to fast idle without extended cranking.",
        warning_signs=[
            "Seller pre-warmed engine before inspection (engine warm to touch on arrival)",
            "Sluggish cranking indicating dying battery or failing starter",
            "Loud grinding or squealing noise during cranking",
            "Engine fails to fire on first attempt"
        ],
        verification_action="Insist on inspecting vehicle after sitting cold for several hours.",
        evidence_required="Auditory and visual observation of cold engine start",
        evidence_state=EvidenceState.SUPPORTED,
        severity_if_failed=RiskSeverity.HIGH,
        professional_inspection_required=True,
        notes="A pre-warmed engine often conceals cold-start smoke, timing chain rattle, or severe idle instability."
    ),
    ChecklistItem(
        item_id="ENG_IDLE_STABILITY_VIBRATION",
        category=InspectionCategory.ENGINE_AND_POWERTRAIN,
        title="Idle Stability, Misfire & Engine Mount Dampening",
        purpose="Detects cylinder misfires, dirty throttle bodies, vacuum leaks, or collapsed hydraulic engine mounts.",
        importance=ImportanceLevel.HIGH,
        applicable_to="ALL",
        inspection_method="Allow engine to idle without touching throttle. Observe tachometer needle stability and feel vibrations on steering wheel.",
        expected_observation="Smooth idle at 700–850 RPM; tachometer needle stationary; minimal vibration through steering wheel.",
        warning_signs=[
            "Tachometer needle hunts up and down erratically",
            "Shuddering or rhythmic misfire shake felt in cabin",
            "Violent engine rock when turning engine on or off (collapsed engine mounts)"
        ],
        verification_action="Observe engine block physically while running; check if engine shakes excessively.",
        evidence_required="Visual and sensory idle evaluation",
        evidence_state=EvidenceState.SUPPORTED,
        severity_if_failed=RiskSeverity.HIGH,
        professional_inspection_required=True,
        notes="Persistent idle hunting indicates vacuum leak, faulty idle air control, or intermittent ignition misfire."
    ),
    ChecklistItem(
        item_id="ENG_FLUID_LEAKS_INSPECTION",
        category=InspectionCategory.ENGINE_AND_POWERTRAIN,
        title="Engine Oil, Coolant & Fluid Leaks",
        purpose="Detects failing gaskets, cracked hoses, leaking radiators, or weeping steering/brake hydraulics.",
        importance=ImportanceLevel.HIGH,
        applicable_to="ALL",
        inspection_method="Inspect valve cover perimeter, timing cover, oil filter housing, radiator hoses, and ground beneath engine.",
        expected_observation="Dry engine surfaces with light surface dust; no wet, glistening oil pools or colored coolant crust.",
        warning_signs=[
            "Wet oil accumulation around cylinder head gasket or timing cover",
            "Green/pink crusty residue around water pump, radiator tanks, or hose clamps",
            "Active fluid dripping onto ground after 5 minutes of idling"
        ],
        verification_action="Shine flashlight down sides of engine block and under front bumper.",
        evidence_required="Visual inspection with flashlight of engine bay and underbelly",
        evidence_state=EvidenceState.SUPPORTED,
        severity_if_failed=RiskSeverity.HIGH,
        professional_inspection_required=True,
        notes="Engine bay that has been freshly steam-cleaned immediately prior to inspection often hides active oil leaks."
    ),
    ChecklistItem(
        item_id="ENG_EXHAUST_SMOKE_COLOR",
        category=InspectionCategory.ENGINE_AND_POWERTRAIN,
        title="Exhaust Smoke Color Under Throttle (Blue / White / Black)",
        purpose="Directly detects oil consumption, blown head gasket, or severe fuel mixture problems.",
        importance=ImportanceLevel.CRITICAL,
        applicable_to="ALL",
        inspection_method="Have an assistant rev warm engine to 3,000 RPM in neutral while you observe exhaust pipe tailpipe exit.",
        expected_observation="Faint transparent exhaust (or light water vapor on cold days); no colored smoke under throttle blip.",
        warning_signs=[
            "Blue smoke with burnt oil smell: worn piston rings, valve stem seals, or blown turbocharger oil seal",
            "Thick sweet-smelling white smoke: coolant leaking into combustion chamber from blown head gasket or cracked block",
            "Dense black smoke: severe unburnt fuel, clogged air filter, or failing diesel fuel injectors"
        ],
        verification_action="Check tailpipe under revving; smell exhaust gas for burnt oil or sweet coolant odor.",
        evidence_required="Visual tailpipe smoke inspection under load",
        evidence_state=EvidenceState.VERIFIED,
        severity_if_failed=RiskSeverity.CRITICAL,
        professional_inspection_required=True,
        notes="Blue or dense white smoke indicates catastrophic internal engine wear requiring expensive overhaul."
    ),
    ChecklistItem(
        item_id="ENG_OIL_CAP_BLOWBY",
        category=InspectionCategory.ENGINE_AND_POWERTRAIN,
        title="Engine Oil Cap Sludge & Crankcase Blow-By",
        purpose="Detects blown cylinder head gaskets and severe piston ring blow-by.",
        importance=ImportanceLevel.CRITICAL,
        applicable_to="ALL",
        inspection_method="Unscrew engine oil filler cap with engine off. Inspect underside. Restart engine and check for smoke puffing out.",
        expected_observation="Clean golden or dark oil coating; no mayonnaise-like emulsion; no violent smoke puffing under idle.",
        warning_signs=[
            "Milky, coffee-colored sludge ('mayonnaise') beneath cap indicating coolant mixing with oil",
            "Dense smoke puffing out of oil filler neck like a chimney (excessive crankcase blow-by)",
            "Oil dipstick shows frothy, milky oil or metal flake particles"
        ],
        verification_action="Examine oil cap underside and dipstick; check crankcase ventilation pressure.",
        evidence_required="Physical inspection of engine oil cap and dipstick",
        evidence_state=EvidenceState.VERIFIED,
        severity_if_failed=RiskSeverity.CRITICAL,
        professional_inspection_required=True,
        notes="Milky oil cap residue is a classic indicator of head gasket failure or engine flood water contamination."
    ),
    ChecklistItem(
        item_id="ENG_WARNING_LAMPS_DIAGNOSTIC",
        category=InspectionCategory.ENGINE_AND_POWERTRAIN,
        title="Warning Lamp Check (MIL / Check Engine / Oil / Battery)",
        purpose="Verifies instrument cluster warning lamps illuminate on bulb check and extinguish properly after engine start.",
        importance=ImportanceLevel.CRITICAL,
        applicable_to="ALL",
        inspection_method="Turn ignition key to Position 2 (ON) without cranking. Verify Check Engine, Oil Pressure, Battery, Airbag, ABS lamps illuminate. Start engine.",
        expected_observation="All warning lamps illuminate brightly on bulb check, then all extinguish within 3 seconds of engine starting.",
        warning_signs=[
            "Check Engine light stays on after engine starts",
            "Warning lamp never illuminates on key-turn (bulb removed or masked with black tape to conceal active fault)",
            "Oil pressure lamp flickers or stays illuminated while idling"
        ],
        verification_action="Verify bulb check sequence; perform OBD-II diagnostic fault code scan if possible.",
        evidence_required="Instrument cluster warning lamp sequence observation",
        evidence_state=EvidenceState.VERIFIED,
        severity_if_failed=RiskSeverity.CRITICAL,
        professional_inspection_required=True,
        notes="A Check Engine light masked or disconnected by an unscrupulous seller hides active diagnostic fault codes."
    ),
    ChecklistItem(
        item_id="TRANS_MANUAL_CLUTCH_BITE",
        category=InspectionCategory.ENGINE_AND_POWERTRAIN,
        title="Manual Transmission Clutch Bite Point & Slippage",
        purpose="Evaluates clutch friction disc wear, pressure plate health, and release bearing noise.",
        importance=ImportanceLevel.HIGH,
        applicable_to="MANUAL",
        inspection_method="Engage 1st gear on level ground. Release pedal slowly. On road, accelerate in 3rd gear from 2,000 RPM under load.",
        expected_observation="Smooth, progressive clutch engagement midway through pedal travel; instant acceleration response without RPM flair.",
        warning_signs=[
            "Clutch engagement occurs at the very top of pedal release travel",
            "Engine RPM flares up during acceleration without corresponding vehicle speed increase (clutch slipping)",
            "Chirping or whirring noise that disappears when clutch pedal is depressed (failing release bearing)",
            "Extremely heavy, stiff clutch pedal requiring excessive leg effort"
        ],
        verification_action="Test clutch bite point and acceleration in high gear under load.",
        evidence_required="Physical clutch engagement and load testing",
        evidence_state=EvidenceState.SUPPORTED,
        severity_if_failed=RiskSeverity.HIGH,
        professional_inspection_required=True,
        notes="A slipping clutch will require imminent clutch kit and flywheel resurfacing replacement."
    ),
    ChecklistItem(
        item_id="TRANS_AUTOMATIC_SHIFT_QUALITY",
        category=InspectionCategory.ENGINE_AND_POWERTRAIN,
        title="Automatic Transmission Engagement, Shudder & Slips",
        purpose="Detects expensive mechatronics failure, worn wet/dry clutch packs, or valve body fluid degradation.",
        importance=ImportanceLevel.CRITICAL,
        applicable_to="AUTOMATIC",
        inspection_method="Shift stationary vehicle through P -> R -> N -> D with foot brake applied. Drive through all gears up to highway speed.",
        expected_observation="Smooth engagement into D and R within 1 second; imperceptible shifts; smooth low-speed creep behavior.",
        warning_signs=[
            "Hard jolt or loud 'thud' when shifting from Park into Reverse or Drive",
            "Severe shudder or shuddering hesitation when taking off from standstill (common in dry-clutch DCT/DSG)",
            "Transmission flares RPM during upshift or gets stuck in 'limp home' mode (single gear)"
        ],
        verification_action="Test drive through all gears; perform forward/reverse shift cycles several times warm and cold.",
        evidence_required="Operational shift quality testing under varying speeds",
        evidence_state=EvidenceState.VERIFIED,
        severity_if_failed=RiskSeverity.CRITICAL,
        professional_inspection_required=True,
        notes="Automatic and dual-clutch transmission replacements are among the most expensive repairs in modern vehicles."
    ),
    ChecklistItem(
        item_id="ENG_DIESEL_DPF_GLOW_PLUG",
        category=InspectionCategory.ENGINE_AND_POWERTRAIN,
        title="Diesel Fuel System, DPF & Turbocharger Health",
        purpose="Assesses diesel-specific high-pressure common rail injection, glow plug start, and DPF soot saturation.",
        importance=ImportanceLevel.HIGH,
        applicable_to="DIESEL",
        inspection_method="Check glow plug lamp cycle on ignition. Listen for excessive injector clatter. Check for DPF warning messages.",
        expected_observation="Glow plug lamp extinguishes quickly; smooth diesel combustion without excessive metallic tapping; clean exhaust.",
        warning_signs=[
            "Glow plug warning lamp flashes while driving",
            "Loud, harsh metallic ticking under acceleration (failing piezoelectric diesel injector)",
            "DPF warning light on instrument cluster or high frequency of automatic soot burns"
        ],
        verification_action="Inspect instrument cluster for DPF warnings; check exhaust tailpipe for excessive oily soot accumulation.",
        evidence_required="Diesel system diagnostic and visual inspection",
        evidence_state=EvidenceState.SUPPORTED,
        severity_if_failed=RiskSeverity.HIGH,
        professional_inspection_required=True,
        notes="Modern BS6 diesel DPF and SCR AdBlue systems require expensive replacement if clogged by chronic short city trips."
    ),

    # ────────────────────────────────────────────────────────────────
    # D. UNDERBODY & STRUCTURE (6 Items)
    # ────────────────────────────────────────────────────────────────
    ChecklistItem(
        item_id="UND_CHASSIS_RAIL_CRUMPLE_ZONES",
        category=InspectionCategory.UNDERBODY_AND_STRUCTURE,
        title="Chassis Rail Straightness & Crumple Zone Integrity",
        purpose="Uncovers catastrophic front collision damage that compromises structural passenger shell safety.",
        importance=ImportanceLevel.CRITICAL,
        applicable_to="ALL",
        inspection_method="Inspect inner engine bay front chassis legs (aprons) extending forward toward bumper. Check for wrinkles or kinks.",
        expected_observation="Straight, symmetrical chassis legs; factory accordion-pleated crumple zones are completely undeformed.",
        warning_signs=[
            "Kinks, ripples, or hammered metal on front longitudinal chassis rails",
            "Non-factory weld seams cutting across chassis rails",
            "Chassis leg repainted with rough matte aerosol paint to conceal repair"
        ],
        verification_action="Shine torch down past engine belts and radiator support to inspect chassis rail metal.",
        evidence_required="Direct physical structural chassis inspection",
        evidence_state=EvidenceState.VERIFIED,
        severity_if_failed=RiskSeverity.CRITICAL,
        professional_inspection_required=True,
        notes="A vehicle with compromised chassis crumple zones will not protect occupants in a subsequent crash."
    ),
    ChecklistItem(
        item_id="UND_FACTORY_SPOT_WELDS",
        category=InspectionCategory.UNDERBODY_AND_STRUCTURE,
        title="Factory Spot Welds vs Repair Seams (Strut Towers & Boot Floor)",
        purpose="Detects structural sectioning, clipped front/rear ends, or major quarter panel structural replacement.",
        importance=ImportanceLevel.CRITICAL,
        applicable_to="ALL",
        inspection_method="Pull back boot carpet and examine spare wheel well floor. Inspect front strut suspension towers inside engine bay.",
        expected_observation="Original round robot-made spot weld dimples spaced evenly (every 25–40 mm); original factory seam sealer mastic.",
        warning_signs=[
            "Irregular, messy manual spot welds or brazing joints",
            "Cracked or smeared seam sealer mastic on strut towers or boot floor",
            "Wrinkled spare wheel tub metal or thick body filler beneath boot carpet"
        ],
        verification_action="Lift boot spare tyre and carpet to inspect bare metal floor pan; check engine bay inner strut towers.",
        evidence_required="Physical inspection of structural weld seams and sealer",
        evidence_state=EvidenceState.VERIFIED,
        severity_if_failed=RiskSeverity.CRITICAL,
        professional_inspection_required=True,
        notes="Messy welds or distorted metal in the spare wheel well prove the vehicle was rear-ended severely."
    ),
    ChecklistItem(
        item_id="UND_FLOOR_PAN_CORROSION_SCRAPES",
        category=InspectionCategory.UNDERBODY_AND_STRUCTURE,
        title="Underbody Floor Pan Scrapes & Structural Corrosion",
        purpose="Evaluates severe underbody impacts from rocks/speed bumps and structural rust perforation.",
        importance=ImportanceLevel.HIGH,
        applicable_to="ALL",
        inspection_method="Crouch or place vehicle on workshop lift. Inspect full length of floor pan, fuel tank shield, and crossmembers.",
        expected_observation="Intact rubberized underbody coating; no deep dents on floor pan or structural crossmembers; no flaky rust.",
        warning_signs=[
            "Perforating rust or crumbling metal on floor pan or sill pinch welds",
            "Deep denting that has crushed fuel lines, brake lines, or floor pan",
            "Fresh thick black tar coating applied locally to conceal rusted metal"
        ],
        verification_action="Inspect vehicle from underneath on service ramp or hoist.",
        evidence_required="Underbody inspection on ramp or pit",
        evidence_state=EvidenceState.SUPPORTED,
        severity_if_failed=RiskSeverity.HIGH,
        professional_inspection_required=True,
        notes="Rusted or crushed floor pans weaken torsional rigidity and can allow exhaust fumes or water into the cabin."
    ),
    ChecklistItem(
        item_id="UND_SUSPENSION_STRUTS_BUSHINGS",
        category=InspectionCategory.UNDERBODY_AND_STRUCTURE,
        title="Suspension Shock Absorbers, Springs & Rubber Bushings",
        purpose="Identifies worn shock absorbers, broken coil springs, and cracked rubber control arm bushings.",
        importance=ImportanceLevel.HIGH,
        applicable_to="ALL",
        inspection_method="Inspect shock absorber bodies for oily fluid leakage. Check rubber suspension arm bushings with flashlight.",
        expected_observation="Shock bodies are dry and free of oily film; rubber bushings are supple without deep tears or crumbling.",
        warning_signs=[
            "Oil coating shock absorber body indicating blown internal hydraulic seal",
            "Torn, cracked, or off-center lower control arm rubber bushings",
            "Vehicle bounces more than 1.5 times when pushed down vigorously on a corner"
        ],
        verification_action="Push down hard on each vehicle corner (bounce test); visually inspect damper cylinders for fluid weeping.",
        evidence_required="Visual damper inspection and rebound bounce test",
        evidence_state=EvidenceState.SUPPORTED,
        severity_if_failed=RiskSeverity.MEDIUM,
        professional_inspection_required=False,
        notes="Blown shocks increase braking distances by up to 20% and cause erratic emergency lane-change stability."
    ),
    ChecklistItem(
        item_id="UND_SUBFRAME_STEERING_RACK",
        category=InspectionCategory.UNDERBODY_AND_STRUCTURE,
        title="Subframe Mounting & Steering Rack Boot Seals",
        purpose="Detects loose steering components, leaking power steering racks, or torn CV axle boots.",
        importance=ImportanceLevel.HIGH,
        applicable_to="ALL",
        inspection_method="Look behind front wheels. Inspect accordion rubber boots on steering rack tie rods and CV axle drive shafts.",
        expected_observation="Rubber boots intact and dry; no grease slung around wheel well; tight subframe mounting bolts.",
        warning_signs=[
            "Torn accordion rubber boot with grease slung across brake calipers and suspension",
            "Power steering fluid weeping from steering rack end seals",
            "Excessive mechanical play when shaking front road wheels"
        ],
        verification_action="Turn steering lock-to-lock while observing tie rod boots; check for grease splatter.",
        evidence_required="Under-wheel visual and mechanical play inspection",
        evidence_state=EvidenceState.SUPPORTED,
        severity_if_failed=RiskSeverity.HIGH,
        professional_inspection_required=True,
        notes="A torn CV boot allows road grit to destroy the axle joint within 1,000 km, leading to complete drive failure."
    ),
    ChecklistItem(
        item_id="UND_EXHAUST_SYSTEM_CAT_CONV",
        category=InspectionCategory.UNDERBODY_AND_STRUCTURE,
        title="Exhaust System Piping, Catalytic Converter & Heat Shields",
        purpose="Ensures emissions catalytic converter is present and exhaust piping has no dangerous leaks.",
        importance=ImportanceLevel.MEDIUM,
        applicable_to="ALL",
        inspection_method="Inspect exhaust pipe from manifold down to rear muffler. Verify original catalytic converter is fitted.",
        expected_observation="Solid exhaust piping securely suspended on rubber hangers; intact heat shields above exhaust line.",
        warning_signs=[
            "Catalytic converter cut out and replaced with straight pipe (common scrap-metal theft)",
            "Loud sputtering exhaust hiss or blowing sound indicating perforated pipe",
            "Rattling loose heat shields vibrating against exhaust pipe"
        ],
        verification_action="Inspect catalytic converter housing under vehicle; listen for exhaust leaks while engine revs.",
        evidence_required="Underbody visual inspection of exhaust line",
        evidence_state=EvidenceState.SUPPORTED,
        severity_if_failed=RiskSeverity.MEDIUM,
        professional_inspection_required=False,
        notes="A missing or gutted catalytic converter will cause PUC failure and cannot be registered in BS6 metro zones."
    ),

    # ────────────────────────────────────────────────────────────────
    # E. INTERIOR (6 Items)
    # ────────────────────────────────────────────────────────────────
    ChecklistItem(
        item_id="INT_ODOMETER_PEDAL_WEAR_RATIO",
        category=InspectionCategory.INTERIOR,
        title="Interior Wear Consistency vs Stated Odometer",
        purpose="Identifies odometer fraud by comparing wear on contact points (pedals, steering, seat bolster) with claimed km.",
        importance=ImportanceLevel.HIGH,
        applicable_to="ALL",
        inspection_method="Examine rubber pads on clutch/brake pedals, steering wheel leather grain, gear shifter markings, and driver seat bolster.",
        expected_observation="Wear levels logically match odometer (e.g. 30,000 km car shows crisp steering texture and minimal pedal rubber wear).",
        warning_signs=[
            "Brake/clutch pedal rubber worn down to bare metal on a car claiming 35,000 km",
            "Brand new replacement aftermarket pedal covers fitted to hide severe wear",
            "Driver seat bolster collapsed or foam torn while odometer claims low mileage"
        ],
        verification_action="Assess tactile and visual wear on driver touchpoints against claimed odometer figure.",
        evidence_required="Physical interior contact point wear audit",
        evidence_state=EvidenceState.SUPPORTED,
        severity_if_failed=RiskSeverity.HIGH,
        professional_inspection_required=False,
        notes="High wear on contact points paired with low indicated mileage is a classic indicator of odometer tampering."
    ),
    ChecklistItem(
        item_id="INT_ELECTRICALS_SWITCHGEAR",
        category=InspectionCategory.INTERIOR,
        title="Switchgear, Power Windows & Central Locking",
        purpose="Tests cabin electrical switchgear, window regulators, and central locking actuators.",
        importance=ImportanceLevel.MEDIUM,
        applicable_to="ALL",
        inspection_method="Operate all 4 power window switches up and down fully. Test central locking from driver door and key fob. Test horn, wipers, washers.",
        expected_observation="All power windows glide smoothly without sticking; central lock locks/unlocks all doors simultaneously; wipers and horn work.",
        warning_signs=[
            "Power window moves slowly or requires hand assistance to close",
            "Central locking fails to lock one or more doors (faulty door lock actuator)",
            "Intermittent wiper failure or windshield washer spray not functioning"
        ],
        verification_action="Systematically cycle every dashboard switch, stalk, and window switch.",
        evidence_required="Functional cabin electrical test",
        evidence_state=EvidenceState.SUPPORTED,
        severity_if_failed=RiskSeverity.LOW,
        professional_inspection_required=False,
        notes="Power window regulator and central lock motor replacements cost ₹3,000–8,000 per door."
    ),
    ChecklistItem(
        item_id="INT_HVAC_AIR_CONDITIONING",
        category=InspectionCategory.INTERIOR,
        title="Air Conditioning Cooling Performance & Heater Core",
        purpose="Verifies AC compressor, condenser cooling, refrigerant charge, and heater matrix health.",
        importance=ImportanceLevel.HIGH,
        applicable_to="ALL",
        inspection_method="Turn AC to lowest temp setting and max blower speed. Wait 3 minutes. Feel air from center vents with thermometer or hand.",
        expected_observation="AC blows crisp, icy air (vent output under 10°C); compressor clutch engages smoothly without engine stalling; heater blows hot air.",
        warning_signs=[
            "AC blows ambient or lukewarm air (refrigerant leak or seized compressor)",
            "Damp musty smell when AC turns on (mildew on evaporator coil)",
            "Sweet antifreeze smell in cabin when heater is turned on (leaking heater core)"
        ],
        verification_action="Measure vent air temperature drop after 3 minutes of engine idling with AC on.",
        evidence_required="Functional climate control temperature evaluation",
        evidence_state=EvidenceState.SUPPORTED,
        severity_if_failed=RiskSeverity.MEDIUM,
        professional_inspection_required=False,
        notes="A leaking AC evaporator core often requires complete dashboard removal costing ₹15,000–30,000 in labor."
    ),
    ChecklistItem(
        item_id="INT_FLOOD_DAMAGE_WATERLINES",
        category=InspectionCategory.INTERIOR,
        title="Flood Damage & Submersion Indicators",
        purpose="Detects flood-submerged vehicles prone to catastrophic ongoing electrical, sensor, and corrosion failures.",
        importance=ImportanceLevel.CRITICAL,
        applicable_to="ALL",
        inspection_method="Inspect seat frame mounting brackets, under-dash metal brackets, lower seatbelt webbing, and spare tyre well for waterlines/silt.",
        expected_observation="Clean, dry carpets; uncorroded gold/silver zinc plating on seat rails; clean electrical connectors under dash.",
        warning_signs=[
            "Rust or corrosion on raw metal springs or mounting rails beneath seats",
            "Fine silt or mud residue trapped behind dashboard wiring harnesses or in seatbelt mechanisms",
            "Persistent damp, moldy, or excessive artificial air freshener odor masking flood mildew",
            "Seatbelt pulled out completely reveals a distinct waterline discoloration mark"
        ],
        verification_action="Pull front seatbelts out to maximum extension; look under front seats with flashlight for unpainted metal rust.",
        evidence_required="Physical flood indicator inspection under dashboard and seats",
        evidence_state=EvidenceState.VERIFIED,
        severity_if_failed=RiskSeverity.CRITICAL,
        professional_inspection_required=True,
        notes="Flood-damaged vehicles suffer chronic electronic sensor failures, airbag malfunctions, and ECU corrosion."
    ),
    ChecklistItem(
        item_id="INT_DASHBOARD_CABIN_TRIM",
        category=InspectionCategory.INTERIOR,
        title="Dashboard Assembly, Glovebox & Cabin Rattles",
        purpose="Checks for dashboard removal (often needed after airbag deployment or heater core failure) and trim fit.",
        importance=ImportanceLevel.LOW,
        applicable_to="ALL",
        inspection_method="Check dashboard fit against windshield and A-pillar trims. Press on center console and glovebox.",
        expected_observation="Snug, factory-fitted dashboard without misaligned clip seams or broken vent louvers.",
        warning_signs=[
            "Dashboard panel gap loose or squeaking excessively",
            "Screw covers missing or showing pry marks on dashboard trim",
            "Broken AC vent adjuster louvers or jammed glovebox latch"
        ],
        verification_action="Inspect dashboard seam alignment and test all storage compartment latches.",
        evidence_required="Visual and tactile cabin trim inspection",
        evidence_state=EvidenceState.SUPPORTED,
        severity_if_failed=RiskSeverity.LOW,
        professional_inspection_required=False,
        notes="Pry marks around the passenger dashboard often indicate previous passenger airbag module replacement."
    ),
    ChecklistItem(
        item_id="INT_SEATS_UPHOLSTERY_FOLDING",
        category=InspectionCategory.INTERIOR,
        title="Seat Upholstery, Adjusters & 60:40 Split Folding",
        purpose="Evaluates seating adjustment mechanisms, recline levers, and rear seat folding flexibility.",
        importance=ImportanceLevel.LOW,
        applicable_to="ALL",
        inspection_method="Test driver seat height and backrest adjusters. Fold rear seats forward and re-latch.",
        expected_observation="Smooth seat sliding and locking; intact seat upholstery without deep burns or tears; rear seats fold and latch cleanly.",
        warning_signs=[
            "Driver seat backrest adjuster mechanism broken or loose on its track",
            "Rear seat folding latch stuck or broken, preventing boot cargo expansion",
            "Severely torn or stained fabric/leatherette upholstery"
        ],
        verification_action="Test all seat adjusters and fold rear split seats.",
        evidence_required="Functional seat mechanism test",
        evidence_state=EvidenceState.SUPPORTED,
        severity_if_failed=RiskSeverity.LOW,
        professional_inspection_required=False,
        notes="Broken seat height adjusters can be expensive to source as complete seat frames are often required."
    ),

    # ────────────────────────────────────────────────────────────────
    # F. SAFETY (5 Items)
    # ────────────────────────────────────────────────────────────────
    ChecklistItem(
        item_id="SAF_AIRBAG_LAMP_CYCLE",
        category=InspectionCategory.SAFETY,
        title="Airbag (SRS) Warning Indicator Ignition Cycle",
        purpose="Guarantees airbag system is operational and has not been bypassed with resistors after accident deployment.",
        importance=ImportanceLevel.CRITICAL,
        applicable_to="ALL",
        inspection_method="Watch instrument cluster closely on Key ON. Airbag light must illuminate, stay on for 3–5 seconds, then turn off INDEPENDENTLY of other lights.",
        expected_observation="Airbag SRS lamp illuminates on ignition, performs internal self-check, and turns off independently after 3–5 seconds.",
        warning_signs=[
            "Airbag light turns off at the exact same millisecond as oil/battery lamp (wired together to bypass deployed airbag)",
            "Airbag warning light stays permanently illuminated while engine runs",
            "Airbag light never turns on at all on bulb check (bulb disconnected or covered)",
            "Steering wheel center horn pad or passenger dashboard feels soft, glued, or uneven (deployed airbag cover repaired)"
        ],
        verification_action="Perform ignition cycle twice to monitor airbag lamp timing; inspect steering wheel and passenger dash seam.",
        evidence_required="Instrument cluster airbag self-test timing observation",
        evidence_state=EvidenceState.VERIFIED,
        severity_if_failed=RiskSeverity.CRITICAL,
        professional_inspection_required=True,
        notes="Unscrupulous repairers wire the airbag lamp to the oil light to conceal deployed, missing airbags."
    ),
    ChecklistItem(
        item_id="SAF_ABS_ESC_LAMP_SEQUENCE",
        category=InspectionCategory.SAFETY,
        title="Anti-Lock Braking (ABS) & ESC Indicator Sequence",
        purpose="Ensures emergency anti-skid and ABS wheel speed sensors are functional.",
        importance=ImportanceLevel.CRITICAL,
        applicable_to="ALL",
        inspection_method="Turn key to Position 2. Check ABS lamp turns on and extinguishes after startup.",
        expected_observation="ABS lamp lights up on bulb check and turns off smoothly; no ABS warning while driving.",
        warning_signs=[
            "ABS or Traction Control warning light stays on while driving",
            "ABS lamp never lights up during ignition bulb check",
            "Brake pedal pulses violently at low urban speeds under light braking (faulty wheel speed sensor tone ring)"
        ],
        verification_action="Verify ABS lamp timing; perform emergency braking stop on clear surface during test drive.",
        evidence_required="ABS lamp operational cycle observation",
        evidence_state=EvidenceState.VERIFIED,
        severity_if_failed=RiskSeverity.HIGH,
        professional_inspection_required=True,
        notes="A faulty ABS hydraulic pump or wheel sensor disables anti-lock braking, causing skidding in emergencies."
    ),
    ChecklistItem(
        item_id="SAF_SEATBELTS_PRETENSIONERS",
        category=InspectionCategory.SAFETY,
        title="Seatbelt Webbing, Retraction & Pretensioner Locks",
        purpose="Ensures primary occupant restraint system functions in a crash and pretensioners haven't fired.",
        importance=ImportanceLevel.CRITICAL,
        applicable_to="ALL",
        inspection_method="Pull all seatbelts out completely. Inspect webbing for cuts or fraying. Give sharp, sudden jerk to verify inertia reel locks instantly.",
        expected_observation="Seatbelts pull smoothly, lock immediately upon rapid yank, and retract cleanly back into B-pillar.",
        warning_signs=[
            "Seatbelt fails to lock when yanked quickly",
            "Seatbelt pretensioner buckle casing shows deployed plastic or fired pyrotechnic wire",
            "Webbing frayed, cut, or refuses to retract smoothly into pillar"
        ],
        verification_action="Yank all front and rear seatbelts sharply to test inertia lock; inspect lower buckle pretensioners.",
        evidence_required="Physical seatbelt inertia lock and webbing inspection",
        evidence_state=EvidenceState.VERIFIED,
        severity_if_failed=RiskSeverity.CRITICAL,
        professional_inspection_required=True,
        notes="Seatbelts are the most vital life-saving safety equipment in the vehicle; frayed webbing will snap under collision loads."
    ),
    ChecklistItem(
        item_id="SAF_BRAKE_PEDAL_FEEL",
        category=InspectionCategory.SAFETY,
        title="Brake Pedal Firmness, Travel & Vacuum Booster Check",
        purpose="Detects master cylinder internal leaks, air in hydraulic brake lines, or failing vacuum brake booster.",
        importance=ImportanceLevel.CRITICAL,
        applicable_to="ALL",
        inspection_method="With engine off, pump brake pedal 5 times until hard. Hold pressure and start engine. Pedal should drop slightly under foot.",
        expected_observation="Pedal becomes hard with engine off; drops smoothly 1–2 cm on engine start as vacuum assists; stays firm under sustained pressure.",
        warning_signs=[
            "Pedal slowly sinks all the way to floor under steady foot pressure (internal master cylinder seal leak)",
            "Pedal feels spongy or requires pumping to build braking pressure (air in hydraulic lines or boiling moisture)",
            "Pedal remains rock-hard with engine running (failed vacuum booster or severed vacuum hose)"
        ],
        verification_action="Perform vacuum booster drop test; hold firm pedal pressure for 30 seconds to check for creeping.",
        evidence_required="Physical brake hydraulic and vacuum booster test",
        evidence_state=EvidenceState.VERIFIED,
        severity_if_failed=RiskSeverity.CRITICAL,
        professional_inspection_required=True,
        notes="A brake pedal that sinks to the floor indicates sudden brake loss risk in traffic."
    ),
    ChecklistItem(
        item_id="SAF_BRAKE_DISC_PAD_THICKNESS",
        category=InspectionCategory.SAFETY,
        title="Brake Disc Rotor Grooving & Friction Pad Thickness",
        purpose="Assesses remaining brake life and detects warped or scored brake rotors.",
        importance=ImportanceLevel.HIGH,
        applicable_to="ALL",
        inspection_method="Look through front alloy wheel spokes at front brake discs. Check outer edge lip and pad friction material thickness.",
        expected_observation="Rotor surface is smooth without deep circular gouges; lip is minimal (<1.5 mm); pad friction material is at least 4 mm thick.",
        warning_signs=[
            "Deep circular grooves or blue heat discoloration on brake disc surface",
            "Significant lip on outer edge of disc indicating rotor is at minimum discard thickness",
            "Brake pads worn down to steel backing plate (metal-on-metal grinding sound)"
        ],
        verification_action="Inspect disc surface through wheel spokes or behind wheel with flashlight.",
        evidence_required="Visual brake rotor and pad thickness inspection",
        evidence_state=EvidenceState.SUPPORTED,
        severity_if_failed=RiskSeverity.MEDIUM,
        professional_inspection_required=False,
        notes="Worn discs and pads require immediate replacement before safe driving."
    ),

    # ────────────────────────────────────────────────────────────────
    # G. TEST DRIVE (5 Items)
    # ────────────────────────────────────────────────────────────────
    ChecklistItem(
        item_id="DRV_STEERING_CENTERING_PULL",
        category=InspectionCategory.TEST_DRIVE,
        title="Steering Centering, Pull & High-Speed Tracking",
        purpose="Detects wheel alignment errors, uneven tyre pressure, suspension damage, or twisted chassis frame.",
        importance=ImportanceLevel.HIGH,
        applicable_to="ALL",
        inspection_method="On a straight, flat, level road at 50–60 km/h, briefly loosen grip on steering wheel. Observe whether vehicle tracks straight.",
        expected_observation="Vehicle maintains straight path; steering wheel is centered when driving straight; smooth self-centering after turns.",
        warning_signs=[
            "Vehicle immediately drifts or pulls sharply toward left or right",
            "Steering wheel is turned at an angle (crooked) while vehicle travels in a straight line",
            "Steering feels excessively heavy or fails to self-center after a 90-degree turn"
        ],
        verification_action="Drive on straight road; release steering pressure briefly to evaluate straight-line tracking.",
        evidence_required="Dynamic straight-line test drive evaluation",
        evidence_state=EvidenceState.SUPPORTED,
        severity_if_failed=RiskSeverity.HIGH,
        professional_inspection_required=True,
        notes="A strong pull to one side that persists after wheel alignment indicates bent suspension or chassis damage."
    ),
    ChecklistItem(
        item_id="DRV_BRAKING_STABILITY_JUDDER",
        category=InspectionCategory.TEST_DRIVE,
        title="Braking Stability, Straight-Line Tracking & Judder",
        purpose="Detects warped brake discs, seized brake calipers, or dynamic suspension bushing deflection under load.",
        importance=ImportanceLevel.CRITICAL,
        applicable_to="ALL",
        inspection_method="At 60 km/h on an empty road, brake firmly down to 10 km/h. Feel for pulsations in brake pedal and steering wheel vibration.",
        expected_observation="Vehicle decelerates in a straight line without pulling sideways; pedal remains firm without judder or vibration.",
        warning_signs=[
            "Steering wheel shakes or vibrates vigorously during moderate braking (warped front brake discs)",
            "Vehicle yanks to one side under hard braking (seized brake caliper or fluid imbalance)",
            "Loud grinding or squealing noises during brake application"
        ],
        verification_action="Perform firm controlled braking from 60 km/h on safe clear road.",
        evidence_required="Dynamic braking test drive evaluation",
        evidence_state=EvidenceState.VERIFIED,
        severity_if_failed=RiskSeverity.HIGH,
        professional_inspection_required=True,
        notes="Warped brake discs produce dangerous steering shudder during high-speed highway braking."
    ),
    ChecklistItem(
        item_id="DRV_SUSPENSION_NOISE_BUMPS",
        category=InspectionCategory.TEST_DRIVE,
        title="Suspension Noise, Damping & Speed Breaker Behavior",
        purpose="Identifies worn stabilizer bar links, broken shock absorbers, or worn steering ball joints over bumps.",
        importance=ImportanceLevel.HIGH,
        applicable_to="ALL",
        inspection_method="Drive vehicle over rough road surface, cobblestones, and speed breakers at 20–30 km/h. Listen for clunks or rattles.",
        expected_observation="Dampened, solid thud over bumps; no metallic clunking, rattling, or secondary uncontrolled body bouncing.",
        warning_signs=[
            "Metallic knocking or clunking sounds from front suspension over small bumps (worn link rods or ball joints)",
            "Loud squeaking or groaning sound over speed breakers (dry sway bar or control arm bushings)",
            "Vehicle bottoming out or scraping suspension on modest speed breakers"
        ],
        verification_action="Drive over speed breakers and rough pavement with windows slightly lowered to listen for suspension noises.",
        evidence_required="Dynamic acoustic and damping suspension test",
        evidence_state=EvidenceState.SUPPORTED,
        severity_if_failed=RiskSeverity.MEDIUM,
        professional_inspection_required=True,
        notes="Suspension noises point to worn wear-and-tear components that will require immediate overhaul."
    ),
    ChecklistItem(
        item_id="DRV_TRANSMISSION_CRUISING",
        category=InspectionCategory.TEST_DRIVE,
        title="Highway Cruising, Synchronizers & Gear Shift Feel",
        purpose="Evaluates all forward and reverse gears, syncromesh engagement, and high-speed driveline noise.",
        importance=ImportanceLevel.HIGH,
        applicable_to="ALL",
        inspection_method="Shift through every single gear (including Reverse) during test drive. Cruise at 80 km/h and listen for differential/gearbox whine.",
        expected_observation="Crisp, effortless gear lever movement into all gears; no crunching; quiet transmission at highway cruising speeds.",
        warning_signs=[
            "Gear lever grinds or crunches when downshifting into 2nd gear (worn syncromesh rings)",
            "Gear pops out of gear back into neutral when lifting off throttle under engine braking",
            "High-pitched whining or groaning noise at cruising speed that changes with throttle input"
        ],
        verification_action="Shift through all forward gears and reverse; accelerate and decelerate to evaluate driveline backlash.",
        evidence_required="Dynamic multi-speed transmission evaluation",
        evidence_state=EvidenceState.SUPPORTED,
        severity_if_failed=RiskSeverity.HIGH,
        professional_inspection_required=True,
        notes="Gear popping out of gear indicates internal transmission fork or gear dog wear requiring complete transmission teardown."
    ),
    ChecklistItem(
        item_id="DRV_ENGINE_THERMAL_GAUGE",
        category=InspectionCategory.TEST_DRIVE,
        title="Engine Temperature Stability & Cooling Fan Operation",
        purpose="Ensures engine cooling system maintains stable operating temperature without overheating under load.",
        importance=ImportanceLevel.HIGH,
        applicable_to="ALL",
        inspection_method="Monitor temperature gauge or digital readout throughout 15-minute test drive. Let engine idle for 3 minutes after drive.",
        expected_observation="Temperature gauge rises to middle mark and stays locked in place; radiator electric fan kicks in quietly at idle.",
        warning_signs=[
            "Temperature gauge climbs past middle towards RED mark",
            "Temperature warning light illuminates on dashboard",
            "Radiator fan screams loudly or never turns on at all, causing temperature to rise while idling"
        ],
        verification_action="Observe temperature indicator during idling and after spirited test drive.",
        evidence_required="Thermal behavior monitoring across driving cycles",
        evidence_state=EvidenceState.VERIFIED,
        severity_if_failed=RiskSeverity.CRITICAL,
        professional_inspection_required=True,
        notes="Engine overheating will warp cylinder heads and crack engine blocks in minutes."
    ),
]
