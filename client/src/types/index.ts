/**
 * CARspective — Complete Frontend Domain Types
 * Matches the authoritative backend schemas across all 8 domain engines.
 */

// ==========================================
// 1. Evidence & Provenance Types
// ==========================================

export type EvidenceState =
  | 'VERIFIED'
  | 'SUPPORTED'
  | 'EMPIRICAL'
  | 'MODEL_ESTIMATE'
  | 'USER_STATED'
  | 'INSUFFICIENT_DATA'
  | 'UNVERIFIED'
  | 'DEPRECATED';

export type ConfidenceState =
  | 'HIGH_CONFIDENCE'
  | 'MODERATE_CONFIDENCE'
  | 'LIMITED_CONFIDENCE'
  | 'INSUFFICIENT_DATA';

export interface EvidenceBadgeProps {
  state: EvidenceState;
  showIcon?: boolean;
  size?: 'sm' | 'md';
}

// ==========================================
// 2. Canonical Vehicle Taxonomy Types
// ==========================================

export interface Manufacturer {
  id: string;
  name: string;
  slug: string;
  country?: string;
  is_active: boolean;
}

export interface VehicleModel {
  id: string;
  name: string;
  slug: string;
  manufacturer_slug: string;
  body_type?: string;
}

export interface VehicleGeneration {
  id: string;
  name: string;
  slug: string;
  start_year: number;
  end_year?: number;
  variants?: VehicleVariant[];
}

export interface VehicleVariant {
  id: string;
  name: string;
  slug: string;
  fuel_type: string;
  transmission_type: string;
  engine_displacement_cc?: number;
  power_ps?: number;
  torque_nm?: number;
}

export interface CanonicalResolutionRequest {
  brand: string;
  model: string;
  year?: number;
  variant?: string;
  fuel_type?: string;
  transmission_type?: string;
}

export interface CanonicalResolutionCandidate {
  canonical_id: string;
  confidence: number;
  match_type: string;
  manufacturer: string;
  model: string;
  generation?: string;
  year?: number;
  variant?: string;
  fuel_type?: string;
  transmission?: string;
}

export interface CanonicalResolutionResponse {
  resolved: boolean;
  status: 'EXACT_MATCH' | 'AMBIGUOUS' | 'UNRESOLVED';
  canonical_id?: string;
  primary_match?: CanonicalResolutionCandidate;
  candidates?: CanonicalResolutionCandidate[];
  disambiguation_prompt?: string;
  alternatives?: CanonicalResolutionCandidate[];
}

// ==========================================
// 3. Valuation Types (Phase 3)
// ==========================================

export interface FairMarketRange {
  lower_bound: number;
  upper_bound: number;
  confidence_interval_percent: number;
  multiplier: number;
}

export interface ValuationRequest {
  brand: string;
  model: string;
  manufacturing_year: number;
  km_driven: number;
  fuel_type?: string;
  transmission_type?: string;
  city?: string;
  bodytype?: string;
  number_of_owners?: number;
  variant?: string;
  asking_price?: number; // ISOLATED: Ignored by valuation engine
}

export interface ValuationResponse {
  canonical_vehicle_id?: string;
  vehicle_resolution_status: string;
  estimated_fair_market_value?: number;
  expected_fair_market_range?: FairMarketRange;
  confidence_state: ConfidenceState;
  evidence_quality: string;
  market_evidence?: {
    comparable_count?: number;
    median_historical_ask?: number;
    price_spread_percent?: number;
    [key: string]: any;
  };
  model_metadata: {
    algorithm: string;
    version: string;
    dataset_reference: string;
    target_semantic_concept: string;
    [key: string]: any;
  };
  valuation_timestamp: string;
  limitations: string[];
}

// ==========================================
// 4. Deal Analyzer Types (Phase 4)
// ==========================================

export type DealQuality =
  | 'GREAT_DEAL'
  | 'FAIR_DEAL'
  | 'OVERPRICED'
  | 'UNUSUALLY_LOW_ASKING_PRICE'
  | 'INSUFFICIENT_DATA';

export interface DealAnalysisRequest {
  brand: string;
  model: string;
  manufacturing_year: number;
  km_driven: number;
  asking_price: number;
  number_of_owners?: number;
  fuel_type?: string;
  transmission_type?: string;
  city?: string;
  bodytype?: string;
  variant?: string;
  condition_notes?: string;
  service_history_status?: string;
  accident_history_status?: string;
  insurance_status?: string;
  tyre_condition?: string;
}

export interface PriceDeviation {
  absolute_difference: number;
  relative_difference_percent: number;
  user_facing_summary: string;
  evidence_state: string;
}

export interface FairRangePosition {
  position_ratio?: number;
  category: 'BELOW_RANGE' | 'INSIDE_RANGE' | 'ABOVE_RANGE' | 'UNAVAILABLE';
  explanation: string;
}

export interface AnomalyStatus {
  is_anomaly: boolean;
  anomaly_type: string;
  anomaly_metric: string;
  anomaly_score?: number;
  advisory?: string;
}

export interface NegotiationGuidance {
  target_price?: number;
  target_price_formatted?: string;
  target_range_low?: number;
  target_range_high?: number;
  target_range_formatted?: string;
  negotiation_strength: 'STRONG' | 'MODERATE' | 'LIMITED';
  walk_away_signal: boolean;
  walk_away_rationale?: string;
  rationale: string;
  safety_disclaimer: string;
}

export interface RiskSignal {
  category: 'PRICE_RISK' | 'DOCUMENTATION_RISK' | 'CONDITION_RISK' | 'DATA_RISK';
  code: string;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  evidence_state: string;
  title: string;
  explanation: string;
  recommended_action: string;
}

export interface DealAnalysisResponse {
  canonical_vehicle_id?: string;
  vehicle_summary: string;
  asking_price: number;
  asking_price_formatted: string;
  asking_price_evidence_state: string;
  valuation: {
    estimated_fair_market_value?: number;
    estimated_fair_market_value_formatted?: string;
    expected_fair_market_lower?: number;
    expected_fair_market_upper?: number;
    confidence_state: string;
    evidence_quality: string;
    model_version: string;
    target_semantic_concept: string;
  };
  deal_quality: DealQuality;
  deal_quality_label: string;
  price_deviation: PriceDeviation;
  range_position: FairRangePosition;
  anomaly_status: AnomalyStatus;
  negotiation: NegotiationGuidance;
  risk_signals: RiskSignal[];
  explanation: string;
  limitations: string[];
  computation_latency_ms?: number;
  analysis_timestamp: string;
}

// ==========================================
// 5. CARspective Score & Recommendation (Phase 5)
// ==========================================

export interface DimensionScore {
  dimension_name: string;
  score?: number;
  score_formatted: string;
  evidence_state: EvidenceState;
  confidence: string;
  contributing_factors: string[];
  sources: string[];
  limitations: string[];
}

export interface ScoreResponse {
  canonical_vehicle_id?: string;
  vehicle_summary: string;
  overall_score?: number;
  overall_score_formatted: string;
  evidence_quality: 'HIGH' | 'MODERATE' | 'LIMITED' | 'INSUFFICIENT_DATA';
  dimensions: DimensionScore[];
  explanation: {
    strong_areas: string[];
    watch_areas: string[];
    summary: string;
  };
  limitations: string[];
  score_timestamp: string;
}

export interface UserProfile {
  budget_max?: number;
  budget_flexible?: boolean;
  monthly_km?: number;
  primary_usage?: string;
  family_size?: number;
  fuel_preference?: string;
  transmission_preference?: string;
  safety_priority?: string;
  mileage_priority?: string;
  performance_priority?: string;
  maintenance_priority?: string;
  resale_priority?: string;
  ownership_horizon_years?: number;
}

export interface ListingContext {
  asking_price?: number;
  km_driven?: number;
  condition_notes?: string;
  service_history_status?: string;
  accident_history_status?: string;
  insurance_status?: string;
  tyre_condition?: string;
}

export type RecommendationVerdict =
  | 'STRONG CONSIDERATION'
  | 'CONSIDER'
  | 'PROCEED WITH CAUTION'
  | 'NOT RECOMMENDED';

export interface MarketAlternative {
  brand: string;
  model: string;
  manufacturing_year: number;
  typical_price_inr: number;
  typical_price_formatted: string;
  carspective_score: number;
  rationale: string;
  advantage_over_target: string;
}

export interface UserFitScore {
  overall_fit: number;
  budget_fit: number;
  usage_fit: number;
  family_fit: number;
  powertrain_fit: number;
  priority_alignment: number;
  fit_summary: string;
  evidence_state: string;
}

export interface RecommendationResponse {
  canonical_vehicle_id?: string;
  vehicle_summary: string;
  verdict: RecommendationVerdict;
  verdict_label: string;
  carspective_score?: number;
  carspective_score_quality: string;
  deal_quality?: string;
  user_fit: UserFitScore;
  risk_summary: Record<string, any>;
  explanation: {
    strongest_positive_factor: string;
    biggest_tradeoff: string;
    deal_consideration: string;
    user_fit_consideration: string;
    evidence_limitation?: string;
    detailed_rationale: string;
  };
  alternatives: MarketAlternative[];
  limitations: string[];
  analysis_timestamp: string;
}

// ==========================================
// 6. Comparison Types (Phase 6)
// ==========================================

export interface ComparisonVehicleInput {
  brand: string;
  model: string;
  manufacturing_year?: number;
  fuel_type?: string;
  transmission_type?: string;
  variant?: string;
  asking_price?: number;
  km_driven?: number;
}

export interface CategoryComparisonResult {
  category: string;
  winner_id: string | null;
  winner_name: string | null;
  status: 'WINNER' | 'TIE' | 'INSUFFICIENT_DATA' | 'NOT_APPLICABLE';
  summary: string;
  evidence_state: string;
  key_differences: string[];
}

export interface VehicleTradeoff {
  vehicle_id: string;
  vehicle_name: string;
  key_strengths: string[];
  key_weaknesses: string[];
  best_for_scenarios: string[];
}

export interface ComparisonResponse {
  comparison_id: string;
  vehicles: Array<{
    vehicle_id: string;
    canonical_id: string;
    display_name: string;
    brand: string;
    model: string;
    year?: number;
    score?: ScoreResponse;
    valuation?: ValuationResponse;
    deal?: DealAnalysisResponse;
  }>;
  overall_result: {
    winner_id: string | null;
    winner_name: string | null;
    result_type: 'CLEAR_WINNER' | 'CLOSE_DECISION' | 'INSUFFICIENT_DATA';
    summary: string;
    rationale: string;
  };
  category_comparisons: Record<string, CategoryComparisonResult>;
  tradeoffs: VehicleTradeoff[];
  research_summary: {
    recommendation: string;
    considerations: string[];
  };
  limitations: string[];
}

// ==========================================
// 7. Inspection Intelligence Types (Phase 7)
// ==========================================

export type InspectionStatus = 'PASS' | 'ATTENTION' | 'FAIL' | 'UNKNOWN' | 'NOT_APPLICABLE';

export interface InspectionChecklistItem {
  item_id: string;
  category: string;
  title: string;
  importance: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  what_to_look_for: string;
  status: InspectionStatus;
  evidence_state: EvidenceState;
  source: string;
  verification_action: string;
  notes?: string;
}

export interface InspectionCategoryGroup {
  category: string;
  items: InspectionChecklistItem[];
  pass_count: number;
  attention_count: number;
  fail_count: number;
  unknown_count: number;
}

export interface InspectionEvaluationResponse {
  canonical_vehicle_id: string;
  vehicle_summary: string;
  categories: InspectionCategoryGroup[];
  total_items: number;
  completed_items: number;
  pass_count: number;
  attention_count: number;
  fail_count: number;
  unknown_count: number;
  critical_findings: string[];
  high_risk_findings: string[];
  purchase_readiness:
    | 'READY_FOR_NEXT_STEP'
    | 'VERIFY_BEFORE_NEGOTIATING'
    | 'INSUFFICIENT_EVIDENCE'
    | 'PROFESSIONAL_INSPECTION_RECOMMENDED';
  readiness_summary: string;
  professional_inspection_recommended: boolean;
  evaluation_timestamp: string;
}

// ==========================================
// 8. Grounded AI Assistant Types (Phase 8)
// ==========================================

export interface AssistantEvidenceItem {
  id: string;
  claim: string;
  value?: any;
  source: string;
  evidence_state: string;
  domain: string;
  confidence?: string;
  applicability?: string;
  notes?: string;
  // Legacy aliases
  title?: string;
  summary?: string;
  source_domain?: string;
}

export interface AssistantEvidenceCitation extends AssistantEvidenceItem {}

export interface AssistantVehicleInput {
  brand: string;
  model: string;
  manufacturing_year?: number;
  variant?: string;
  fuel_type?: string;
  transmission_type?: string;
  city?: string;
  km_driven?: number;
  number_of_owners?: number;
  canonical_vehicle_id?: string;
}

export interface AssistantListingInput {
  asking_price?: number;
  negotiable?: boolean;
  seller_type?: string;
}

export interface AssistantContextVehicle {
  canonical_id?: string;
  brand: string;
  model: string;
  year?: number;
  asking_price?: number;
  km_driven?: number;
}

export interface AssistantRequest {
  message: string;
  vehicle?: AssistantVehicleInput;
  listing?: AssistantListingInput;
  compared_vehicles?: AssistantVehicleInput[];
  session_id?: string;
  // Legacy compatibility fields
  query?: string;
  context_vehicle?: AssistantContextVehicle;
  comparison_vehicles?: AssistantContextVehicle[];
}

export interface AssistantResponse {
  session_id: string;
  answer: string;
  intent: string;
  referenced_domains: string[];
  evidence_refs: string[];
  evidence_bundle: AssistantEvidenceItem[];
  suggested_next_actions: string[];
  uncertainty?: string;
  disclaimer?: string;
  session_context_updates?: Record<string, any>;
  // Legacy and computed aliases
  citations?: AssistantEvidenceItem[];
  source_domains_queried?: string[];
  limitations_noted?: string[];
  turn_timestamp?: string;
}

// ==========================================
// 9. Feedback Types (Phase 9)
// ==========================================

export interface FeedbackSubmission {
  feature: 'valuation' | 'deal' | 'score' | 'recommendation' | 'comparison' | 'inspection' | 'assistant';
  useful: boolean;
  expected_price?: number;
  comment?: string;
  vehicle_context?: string;
}

// ==========================================
// 10. Real Vehicle Knowledge Types (Phase 11)
// ==========================================

export interface SourceMetadata {
  source_id: string;
  organization_name: string;
  organization_type: string;
  source_url?: string;
  reference_document?: string;
  published_at?: string;
  retrieved_at?: string;
  valid_until?: string;
  review_due?: string;
  is_stale: boolean;
  confidence_score: number;
  verification_status: string;
}

export interface VehicleSpecification {
  engine_type?: string;
  displacement_cc?: number;
  cylinders?: number;
  valves_per_cylinder?: number;
  aspiration?: string;
  max_power_bhp?: number;
  max_power_rpm?: number;
  max_torque_nm?: number;
  max_torque_rpm?: number;
  transmission?: string;
  drivetrain?: string;
  fuel_type?: string;
  arai_mileage_kmpl?: number;
  fuel_tank_capacity_l?: number;
  emission_norm?: string;
  battery_capacity_kwh?: number;
  electric_range_km?: number;
  motor_output_ps?: number;
  evidence_state: EvidenceState;
  source?: SourceMetadata;
}

export interface VehicleDimensions {
  length_mm?: number;
  width_mm?: number;
  height_mm?: number;
  wheelbase_mm?: number;
  ground_clearance_mm?: number;
  boot_capacity_l?: number;
  seating_capacity?: number;
  kerb_weight_kg?: number;
  turning_radius_m?: number;
  evidence_state: EvidenceState;
  source?: SourceMetadata;
}

export interface VehicleSafetyRating {
  organization: string;
  test_year: number;
  adult_stars: number;
  adult_score?: number;
  child_stars?: number;
  child_score?: number;
  bodyshell_integrity?: string;
  standard_safety_equipment?: string;
  test_protocol?: string;
  evidence_state: EvidenceState;
  source?: SourceMetadata;
}

export interface VariantFeature {
  feature_key: string;
  feature_name: string;
  category: string;
  availability: 'STANDARD' | 'OPTIONAL' | 'NOT_AVAILABLE' | 'NOT_VERIFIED';
  details?: string;
  variant_name?: string;
  evidence_state: EvidenceState;
  source?: SourceMetadata;
}

export interface OwnershipProfile {
  service_interval_km?: number;
  service_interval_months?: number;
  typical_annual_maintenance_inr?: string;
  parts_availability: string;
  maintenance_complexity: string;
  real_world_city_mileage_kmpl?: string | number;
  real_world_highway_mileage_kmpl?: string | number;
  ownership_strengths: string[];
  ownership_concerns: string[];
  evidence_state: EvidenceState;
  source?: SourceMetadata;
}

export interface ReliabilityIssue {
  issue_key: string;
  category: string;
  title: string;
  description: string;
  severity: 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL' | 'ADVISORY';
  affected_years?: string;
  affected_powertrains?: string;
  verification_status: string;
  evidence_state: EvidenceState;
  source?: SourceMetadata;
}

export interface VehicleProCon {
  is_pro: boolean;
  statement: string;
  category: string;
  source_type: string;
  evidence_state: EvidenceState;
  source?: SourceMetadata;
}

export interface ReviewSynthesis {
  what_owners_say?: string;
  what_experts_say?: string;
  carspective_analysis: string;
  has_owner_evidence: boolean;
  has_expert_evidence: boolean;
  evidence_state: EvidenceState;
  source?: SourceMetadata;
}

export interface VehicleKnowledgeProfile {
  canonical_vehicle_id: string;
  make: string;
  model: string;
  generation_name?: string;
  year?: number;
  variant_name?: string;
  body_type?: string;
  segment?: string;
  coverage_tier: string;
  specifications?: VehicleSpecification;
  dimensions?: VehicleDimensions;
  safety?: VehicleSafetyRating;
  features: VariantFeature[];
  ownership?: OwnershipProfile;
  reliability_issues: ReliabilityIssue[];
  pros: VehicleProCon[];
  cons: VehicleProCon[];
  reviews?: ReviewSynthesis;
  freshness_summary?: {
    last_verified: string;
    has_stale_data: boolean;
    evidence_coverage: Record<string, string>;
  };
}

// ==========================================
// 10. Phase 12 Intelligent Discovery & Search
// ==========================================

export type SearchResultType =
  | 'EXACT_MATCH'
  | 'HIGH_CONFIDENCE_MATCH'
  | 'AMBIGUOUS'
  | 'NO_MATCH'
  | 'FILTERED_RESULTS'
  | 'INSUFFICIENT_DATA';

export interface MatchReason {
  factor: string;
  score_contribution: number;
  description: string;
}

export interface CandidateClarificationOption {
  generation: string;
  year_range: string;
  suggested_query: string;
}

export interface CandidateClarification {
  clarification_type: string;
  prompt: string;
  options: CandidateClarificationOption[];
}

export interface DiscoveryCandidate {
  canonical_vehicle_id: string;
  title: string;
  manufacturer: string;
  model: string;
  generation: string;
  model_year: number;
  variant?: string;
  powertrain?: string;
  fuel_type?: string;
  transmission?: string;
  body_type?: string;
  seating_capacity?: number;
  coverage_tier: string;
  evidence_state: EvidenceState;
  has_deep_knowledge: boolean;
  match_score: number;
  match_reasons: MatchReason[];
  available_actions: string[];
}

export interface IntentField<T = any> {
  value?: T;
  provenance?: string;
  confidence?: number;
  raw_token?: string;
}

export interface DiscoverySearchIntent {
  raw_query: string;
  normalized_query: string;
  manufacturer?: IntentField<string>;
  model?: IntentField<string>;
  model_year?: IntentField<number>;
  variant?: IntentField<string>;
  fuel_type?: IntentField<string>;
  transmission?: IntentField<string>;
  body_type?: IntentField<string>;
  budget_min?: IntentField<number>;
  budget_max?: IntentField<number>;
  seating_capacity?: IntentField<number>;
  use_case?: IntentField<string>;
}

export interface DiscoverySearchResponse {
  query: string;
  intent: DiscoverySearchIntent;
  result_type: SearchResultType;
  total_count: number;
  results: DiscoveryCandidate[];
  clarification?: CandidateClarification;
  suggestions?: string[];
  provenance: {
    query_normalized: string;
    rules_applied: string[];
    taxonomy_version: string;
    resolution_method: string;
    evidence_sources_checked: number;
  };
}

export interface AutocompleteItem {
  id: string;
  title: string;
  type: string;
  manufacturer?: string;
  model?: string;
  year?: number;
  canonical_vehicle_id?: string;
  subtitle?: string;
}

export interface AutocompleteResponse {
  query: string;
  items: AutocompleteItem[];
}

// ==========================================
// 10. Phase 13 — Vehicle Intelligence Workspace Types
// ==========================================

export type IdentityConfidenceLevel = 'exact' | 'resolved' | 'ambiguous' | 'limited';

export interface SiblingVariantInfo {
  name: string;
  slug: string;
  trim_level?: string;
  powertrains: string[];
  canonical_id: string;
  is_current: boolean;
}

export interface SiblingGenInfo {
  name: string;
  slug: string;
  year_start: number;
  year_end?: number;
  canonical_id: string;
  is_current: boolean;
}

export interface IdentityConfidenceInfo {
  level: IdentityConfidenceLevel;
  title: string;
  description: string;
  is_confirmed: boolean;
  needs_user_confirmation: boolean;
  sibling_variants: SiblingVariantInfo[];
  sibling_generations: SiblingGenInfo[];
}

export interface VehicleWorkspaceIdentity {
  canonical_vehicle_id: string;
  brand: string;
  brand_slug: string;
  model: string;
  model_slug: string;
  generation?: string;
  generation_slug?: string;
  year?: number;
  variant?: string;
  variant_slug?: string;
  fuel_type?: string;
  transmission_type?: string;
  drivetrain?: string;
  body_type?: string;
  segment?: string;
  coverage_tier: string;
}

export interface ExecutiveSummary {
  carspective_score?: number;
  score_band: 'EXCELLENT' | 'GOOD' | 'FAIR' | 'CAUTION' | 'UNAVAILABLE';
  estimated_fair_market_value_inr?: number;
  estimated_fair_market_value_lakhs?: number;
  expected_fair_market_range_low_inr?: number;
  expected_fair_market_range_high_inr?: number;
  expected_fair_market_range_low_lakhs?: number;
  expected_fair_market_range_high_lakhs?: number;
  deal_quality?: string;
  recommendation_verdict: string;
  safety_stars?: number;
  safety_agency?: string;
  bodyshell_integrity?: string;
  typical_annual_maintenance_inr?: string;
  maintenance_complexity?: string;
  reliability_watchpoints_count: number;
  one_line_summary: string;
}

export interface WorkspaceInspectionSummary {
  total_applicable_items: number;
  critical_items_count: number;
  top_watchpoints: string[];
  documentation_requirements: string[];
  purchase_readiness: string;
}

export interface VehicleWorkspaceResponse {
  canonical_vehicle_id: string;
  identity: VehicleWorkspaceIdentity;
  identity_confidence: IdentityConfidenceInfo;
  executive_summary: ExecutiveSummary;
  valuation?: ValuationResponse;
  deal_analysis?: DealAnalysisResponse;
  score?: ScoreResponse;
  knowledge?: VehicleKnowledgeProfile;
  recommendation?: RecommendationResponse;
  inspection_summary: WorkspaceInspectionSummary;
  alternatives: MarketAlternative[];
  visual: {
    body_type?: string;
    has_3d_support?: boolean;
    model_path?: string;
  };
  market_profile?: VehicleMarketProfile;
  ownership_intelligence?: VehicleOwnershipIntelligence;
  personalized_decision?: DecisionEvaluationResponse;
  current_market?: CurrentMarketIntelligenceResponse;
  evidence_freshness?: Record<string, any>;
  data_governance?: Record<string, any>;
  limitations: string[];
  computation_latency_ms?: number;
}

// ─── Phase 14 Market Intelligence Types ───

export type LiquidityRating = 'VERY_HIGH' | 'HIGH' | 'MODERATE' | 'LOW' | 'VERY_LOW';
export type SecondarySupplyLevel = 'EXTENSIVE' | 'STRONG' | 'MODERATE' | 'LIMITED' | 'VERY_SCARCE';
export type DemandProxy = 'HIGH_DEMAND' | 'STEADY_DEMAND' | 'MODERATE_DEMAND' | 'SELECTIVE_DEMAND';

export interface MarketPositionSummary {
  secondary_market_tier: string;
  historical_listing_count: number;
  market_share_in_segment_percent: number;
  supply_level: SecondarySupplyLevel;
  liquidity_rating: LiquidityRating;
  estimated_days_to_sell_band: string;
  demand_proxy: DemandProxy;
  active_listings_proxy_count: number;
  median_historical_asking_price_inr?: number;
  p25_asking_price_inr?: number;
  p75_asking_price_inr?: number;
  resale_retention_index: number;
  evidence_notes: string;
}

export interface DepreciationDataPoint {
  age_years: number;
  mean_asking_price_inr: number;
  median_asking_price_inr: number;
  p25_asking_price_inr: number;
  p75_asking_price_inr: number;
  sample_size: number;
  retention_percent_of_year_1: number;
  is_statistically_robust: boolean;
}

export interface DepreciationProfile {
  curve_points: DepreciationDataPoint[];
  typical_annual_depreciation_pct: number;
  three_year_retained_value_pct?: number;
  five_year_retained_value_pct?: number;
  data_sufficiency_status: 'ROBUST' | 'ADEQUATE' | 'INSUFFICIENT_DATA';
  caveat_note: string;
}

export interface SegmentBenchmark {
  segment_name: string;
  segment_median_asking_price_inr: number;
  segment_retention_index_median: number;
  vehicle_vs_segment_price_ratio: number;
  vehicle_price_position_label: string;
  top_competing_models: string[];
}

export interface VehicleMarketProfile {
  canonical_vehicle_id: string;
  model_slug: string;
  market_position: MarketPositionSummary;
  depreciation: DepreciationProfile;
  segment_benchmark: SegmentBenchmark;
  evidence_disclosure: string;
  provenance_notice: string;
}

// ─── Phase 14 Real-World Ownership Intelligence Types ───

export interface RoutineServiceScheduleItem {
  interval_km: number;
  interval_months: number;
  milestone_name: string;
  typical_tasks: string[];
  estimated_cost_inr: number;
  evidence_source: string;
}

export interface MajorServiceMilestone {
  mileage_km: number;
  description: string;
  critical_replacements: string[];
  estimated_cost_inr: number;
}

export interface MaintenanceIntelligence {
  typical_annual_maintenance_inr: number;
  service_interval_km: number;
  service_interval_months: number;
  maintenance_complexity: string;
  diy_friendliness: string;
  routine_schedule: RoutineServiceScheduleItem[];
  major_milestones: MajorServiceMilestone[];
  parts_availability_index: string;
  independent_garage_familiarity: string;
}

export interface RealWorldFuelProfile {
  arai_claimed_kmpl?: number;
  real_world_city_kmpl?: number;
  real_world_highway_kmpl?: number;
  real_world_combined_kmpl?: number;
  fuel_type: string;
  transmission_type: string;
  annual_fuel_cost_10k_km_inr: number;
  annual_fuel_cost_15k_km_inr: number;
  cost_per_km_inr: number;
}

export type TCOComponentStatus = 'USER_PROVIDED' | 'EVIDENCE_BACKED' | 'MODEL_ESTIMATED';

export interface TCOComponent {
  component_name: string;
  amount_inr: number;
  percentage_of_total: number;
  status: TCOComponentStatus;
  basis_note: string;
}

export interface TCOYearlyBreakdown {
  year: number;
  annual_depreciation_inr: number;
  annual_fuel_inr: number;
  annual_maintenance_inr: number;
  annual_insurance_inr: number;
  cumulative_cost_inr: number;
}

export interface TCOHorizonSummary {
  horizon_years: number;
  total_cost_inr: number;
  cost_per_km_inr: number;
  depreciation_cost_inr: number;
  fuel_cost_inr: number;
  maintenance_cost_inr: number;
  insurance_cost_inr: number;
  statutory_charges_inr: number;
  components: TCOComponent[];
  yearly_progression: TCOYearlyBreakdown[];
}

export interface OwnershipRiskSignal {
  risk_id?: string;
  category?: string;
  title: string;
  severity: 'CRITICAL' | 'HIGH' | 'MODERATE' | 'LOW';
  description?: string;
  mitigation_advice?: string;
  evidence_state?: string;
  component_affected?: string;
  typical_occurrence_km?: number;
  estimated_repair_cost_inr?: number;
  preventative_measure?: string;
  evidence_source?: string;
}

export interface VehicleOwnershipIntelligence {
  canonical_vehicle_id: string;
  model_slug: string;
  maintenance: MaintenanceIntelligence;
  fuel: RealWorldFuelProfile;
  tco_1_year: TCOHorizonSummary;
  tco_3_year: TCOHorizonSummary;
  tco_5_year: TCOHorizonSummary;
  risk_signals: OwnershipRiskSignal[];
  disclaimer: string;
}

export interface FuelCostRequest {
  mileage_kmpl: number;
  monthly_km: number;
  fuel_type?: string;
  fuel_price_per_litre_inr?: number;
}

export interface FuelCostResponse {
  fuel_type: string;
  fuel_price_per_litre_inr: number;
  monthly_km: number;
  mileage_kmpl: number;
  monthly_litres: number;
  monthly_cost_inr: number;
  annual_cost_inr: number;
  cost_per_km_inr: number;
}

export interface TCOCalculationRequest {
  canonical_vehicle_id: string;
  purchase_price_inr?: number;
  annual_km?: number;
  holding_years?: number;
  user_annual_insurance_inr?: number;
  user_annual_maintenance_inr?: number;
  user_fuel_price_per_litre_inr?: number;
}

export interface TCOCalculationResponse {
  canonical_vehicle_id: string;
  holding_years: number;
  annual_km: number;
  purchase_price_inr: number;
  estimated_exit_value_inr: number;
  net_depreciation_inr: number;
  total_fuel_cost_inr: number;
  total_maintenance_cost_inr: number;
  total_insurance_cost_inr: number;
  total_statutory_inr: number;
  total_cost_of_ownership_inr: number;
  cost_per_km_inr: number;
  monthly_cost_of_ownership_inr: number;
  components: TCOComponent[];
  yearly_progression: TCOYearlyBreakdown[];
  evidence_disclosure: string;
}

// ==========================================
// Phase 15 — Personalized Decision Intelligence
// ==========================================

export type ProvenanceState = 'USER_EXPLICIT' | 'USER_INFERRED' | 'SYSTEM_DEFAULT' | 'NOT_SPECIFIED';

export interface RequirementProvenance {
  state: ProvenanceState;
  source_phrase?: string;
  explanation?: string;
}

export type PurchaseType = 'NEW' | 'USED' | 'EITHER' | 'NOT_SPECIFIED';
export type UsageProfile = 'CITY' | 'HIGHWAY' | 'MIXED' | 'NOT_SPECIFIED';
export type PriorityLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' | 'NOT_SPECIFIED';
export type ToleranceLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'NOT_SPECIFIED';
export type HardConstraintStatus = 'PASS' | 'FAIL' | 'UNKNOWN';
export type DecisionQuality = 'HIGH' | 'MODERATE' | 'LIMITED' | 'INSUFFICIENT_DATA';

export interface HardConstraintsConfig {
  strict_budget_ceiling?: boolean;
  strict_transmission?: boolean;
  strict_fuel_type?: boolean;
  strict_min_seating?: boolean;
  strict_body_type?: boolean;
}

export interface UserRequirementsProfile {
  budget_min_inr?: number;
  budget_max_inr?: number;
  budget_flexible?: boolean;
  monthly_running_budget_max_inr?: number;
  purchase_type?: PurchaseType;
  usage_profile?: UsageProfile;
  annual_km?: number;
  family_size?: number;
  fuel_preferences?: string[];
  transmission_preferences?: string[];
  body_type_preferences?: string[];
  safety_priority?: PriorityLevel;
  reliability_priority?: PriorityLevel;
  maintenance_priority?: PriorityLevel;
  practicality_priority?: PriorityLevel;
  resale_priority?: PriorityLevel;
  performance_priority?: PriorityLevel;
  efficiency_priority?: PriorityLevel;
  value_priority?: PriorityLevel;
  ownership_years?: number;
  maintenance_tolerance?: ToleranceLevel;
  hard_constraints?: HardConstraintsConfig;
  provenance_map?: Record<string, RequirementProvenance>;
}

export interface ConstraintCheckItem {
  constraint_name: string;
  status: HardConstraintStatus;
  required_value: any;
  actual_value: any;
  explanation: string;
}

export interface ConstraintValidationResult {
  overall_status: HardConstraintStatus;
  violations: string[];
  checks: ConstraintCheckItem[];
}

export interface PersonalizedFitBreakdown {
  budget_fit?: number;
  ownership_budget_fit?: number;
  usage_fit?: number;
  family_fit?: number;
  powertrain_fit?: number;
  safety_fit?: number;
  reliability_fit?: number;
  maintenance_fit?: number;
  practicality_fit?: number;
  resale_fit?: number;
  performance_fit?: number;
  ownership_horizon_fit?: number;
  component_weights: Record<string, number>;
  overall_user_fit_score: number;
  decision_quality: DecisionQuality;
  data_limitations: string[];
}

export interface PersonalizedAlternative {
  canonical_vehicle_id: string;
  vehicle_summary: string;
  intrinsic_score?: number;
  user_fit_score: number;
  advantage_over_target: string;
  tradeoff_vs_target: string;
  verdict_label: string;
}

export interface DecisionEvaluationResponse {
  canonical_vehicle_id: string;
  vehicle_summary: string;
  intrinsic_score?: number;
  user_fit_score: number;
  vehicle_fit_score: number;
  deal_fit_score?: number;
  hard_constraint_status: HardConstraintStatus;
  recommendation_verdict: string;
  verdict_label: string;
  fit_breakdown: PersonalizedFitBreakdown;
  why_it_fits: string[];
  why_it_may_not_fit: string[];
  tradeoffs: string[];
  what_to_verify_before_buying: string[];
  alternatives: PersonalizedAlternative[];
  decision_quality: DecisionQuality;
  limitations: string[];
  computation_latency_ms?: number;
}

export interface ShortlistVehicleItem {
  canonical_vehicle_id: string;
  brand: string;
  model: string;
  year?: number;
  variant?: string;
  intrinsic_score?: number;
  user_fit_score: number;
  estimated_fair_market_range?: string;
  ownership_burden_5yr_inr?: number;
  decision_quality: string;
  key_tradeoffs: string[];
  hard_constraint_status: string;
  is_eligible: boolean;
}

export interface ShortlistRankResponse {
  ranked_vehicles: DecisionEvaluationResponse[];
  user_profile_summary: Record<string, any>;
  top_recommendation_id?: string;
  ranking_notes: string[];
  computation_latency_ms?: number;
}

export interface PersonalizedComparisonResponse {
  general_winner_index: number;
  general_winner_rationale: string;
  user_winner_index: number;
  user_winner_rationale: string;
  divergence_explanation?: string;
  vehicles: DecisionEvaluationResponse[];
  computation_latency_ms?: number;
}

export interface PrioritizedChecklistItem {
  item_id: string;
  title: string;
  category: string;
  original_importance: string;
  user_priority_score: number;
  elevation_reason: string;
  how_to_check: string;
  pass_criteria: string;
  fail_criteria: string;
}

export interface PersonalizedInspectionPrioritizationResponse {
  canonical_vehicle_id: string;
  vehicle_summary: string;
  prioritized_checklist: PrioritizedChecklistItem[];
  priority_reasons: string[];
  computation_latency_ms?: number;
}

export interface NaturalLanguageRequirementsResponse {
  parsed_profile: UserRequirementsProfile;
  extracted_fields_count: number;
  clarification_questions: string[];
  provenance_summary: Record<string, string>;
  parser_state?: string;
  computation_latency_ms?: number;
}

// ==========================================
// 12. Data Intelligence & Evidence Pipeline Types (Phase 16)
// ==========================================

export type SourceType =
  | 'MANUFACTURER'
  | 'GOVERNMENT_AUTHORITY'
  | 'SAFETY_ORGANIZATION'
  | 'HISTORICAL_DATASET'
  | 'MARKET_LISTING_SOURCE'
  | 'RESEARCH_PUBLICATION'
  | 'EXPERT_SOURCE'
  | 'INTERNAL_EMPIRICAL_DATASET';

export type ReliabilityClassification =
  | 'AUTHORITATIVE'
  | 'REGULATORY_BENCHMARK'
  | 'EMPIRICAL_OBSERVATION'
  | 'INDUSTRY_AUDIT'
  | 'COMMUNITY_ESTIMATE'
  | 'UNVERIFIED';

export type FreshnessState =
  | 'CURRENT'
  | 'REVIEW_DUE'
  | 'STALE'
  | 'DEPRECATED'
  | 'UNKNOWN';

export interface GovernedSource {
  source_id: string;
  source_name: string;
  source_type: SourceType;
  publisher_organization: string;
  source_url?: string;
  reference_document?: string;
  jurisdiction: string;
  coverage: string;
  collection_method: string;
  first_seen: string;
  last_seen: string;
  freshness_policy_id: string;
  reliability_classification: ReliabilityClassification;
  license_status?: string;
  is_active: boolean;
  deprecated_at?: string;
}

export interface FreshnessEvaluation {
  status: FreshnessState;
  age_days?: number;
  observation_period?: string;
  last_observed?: string;
  review_due_date?: string;
  policy_id: string;
  notes: string;
}

export interface DomainFreshnessSummary {
  domain: string;
  policy_id: string;
  current_count: number;
  review_due_count: number;
  stale_count: number;
  deprecated_count: number;
  unknown_count: number;
  total_items: number;
  dominant_status: FreshnessState;
  evaluation_notes: string;
}

export interface DataQualityReport {
  completeness_score: number;
  validity_score: number;
  uniqueness_score: number;
  canonical_mapping_coverage: number;
  freshness_score: number;
  provenance_coverage: number;
  consistency_score: number;
  overall_quality_score: number;
  status: 'EXCELLENT' | 'GOOD' | 'MARGINAL' | 'POOR';
  total_records: number;
  invalid_records: number;
  duplicate_records: number;
  unmapped_records: number;
  timestamp: string;
}

export interface EvidenceLineageNode {
  claim_id: string;
  canonical_vehicle_id: string;
  attribute_category: string;
  attribute_key: string;
  claim_value: string;
  evidence_state: string;
  freshness: FreshnessEvaluation;
  sources: GovernedSource[];
  applicable_vehicle_scope: string;
  product_surfaces: string[];
  lineage_path: string;
}

// ==========================================
// 17. Phase 17 Current Market Intelligence Types
// ==========================================

export type CurrentSupplyTier = 'VERY_HIGH_SUPPLY' | 'HIGH_SUPPLY' | 'BALANCED' | 'SCARCE' | 'VERY_SCARCE';
export type CurrentObservationType = 'AGGREGATOR_LISTING' | 'CERTIFIED_PRE_OWNED' | 'METRO_CLASSIFIED' | 'DEALER_INVENTORY' | 'PEER_TO_PEER';
export type SellerType = 'INDIVIDUAL' | 'CERTIFIED_DEALER' | 'INDEPENDENT_DEALER' | 'UNKNOWN';
export type ListingStatus = 'ACTIVE' | 'PENDING' | 'DELISTED';
export type DuplicateClassification = 'DISTINCT' | 'EXACT_DUPLICATE' | 'PROBABLE_DUPLICATE';
export type CurrentFreshnessState = 'CURRENT' | 'AGING' | 'STALE' | 'EXPIRED';

export interface CurrentPriceDistribution {
  canonical_vehicle_id: string;
  sample_size: number;
  min_price: number;
  p10_price: number;
  p25_price: number;
  median_price: number;
  p75_price: number;
  p90_price: number;
  max_price: number;
  iqr: number;
  std_dev: number;
  mean_price: number;
}

export interface CurrentMarketSupply {
  canonical_vehicle_id: string;
  total_observations: number;
  active_listings_count: number;
  supply_tier: CurrentSupplyTier;
  regional_distribution: Record<string, number>;
  seller_distribution: Record<string, number>;
  freshness_distribution: Record<string, number>;
}

export interface CurrentRegionalIntelligence {
  region?: string;
  region_name?: string;
  city?: string;
  observation_count: number;
  share_percentage?: number;
  median_asking_price?: number;
  median_asking_price_inr?: number;
  iqr_low_inr?: number;
  iqr_high_inr?: number;
  median_mileage_km?: number;
  coverage_disclaimer?: string;
}

export interface CurrentVsHistoricalComparison {
  canonical_vehicle_id: string;
  historical_sample_size?: number;
  historical_median_asking_price?: number;
  historical_median_asking_price_inr?: number;
  current_sample_size?: number;
  current_median_asking_price?: number;
  current_median_asking_price_inr?: number;
  price_shift_percentage?: number;
  price_trend_direction: 'INCREASING' | 'STABLE' | 'DECREASING' | 'INSUFFICIENT_DATA';
  commentary?: string;
}

export interface CurrentMarketEvidence {
  sources_contributed: string[];
  total_observations: number;
  usable_observations: number;
  duplicate_count: number;
  outlier_count: number;
  geographic_coverage: string[];
  collection_window: string;
  freshness_distribution: Record<string, number>;
  evidence_state: string;
  limitations: string[];
}

export interface CurrentMarketIntelligenceResponse {
  canonical_vehicle_id: string;
  observation_period: string;
  supply: CurrentMarketSupply;
  price_distribution?: CurrentPriceDistribution | null;
  regional_breakdown: CurrentRegionalIntelligence[];
  comparison_with_historical?: CurrentVsHistoricalComparison | null;
  evidence: CurrentMarketEvidence;
  limitations: string[];
}

export interface CurrentMarketIngestionResult {
  batch_id: string;
  source_id: string;
  total_submitted: number;
  accepted: number;
  duplicates_flagged: number;
  outliers_flagged: number;
  execution_time_ms: number;
  status: string;
}


