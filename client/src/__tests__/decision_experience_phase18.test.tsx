import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { DecisionSummaryCard } from '../features/vehicle/workspace/DecisionSummaryCard';
import { AssistantDrawerIntegration } from '../features/vehicle/workspace/AssistantDrawerIntegration';
import { InspectionCalloutSection } from '../features/vehicle/workspace/InspectionCalloutSection';
import { RequirementsEditor } from '../features/decision/RequirementsEditor';
import { PersonalizedDecisionCard } from '../features/decision/PersonalizedDecisionCard';
import { EmptyState } from '../components/common/EmptyState';
import {
  ExecutiveSummary,
  DealAnalysisResponse,
  DecisionEvaluationResponse,
  UserRequirementsProfile,
} from '../types';

// Mock AppContext
const mockOpenAssistant = vi.fn();
vi.mock('../state/AppContext', () => ({
  useApp: () => ({
    openAssistant: mockOpenAssistant,
  }),
}));

const mockSummary: ExecutiveSummary = {
  carspective_score: 82,
  score_band: 'GOOD',
  estimated_fair_market_value_inr: 650000,
  estimated_fair_market_value_lakhs: 6.5,
  expected_fair_market_range_low_inr: 580000,
  expected_fair_market_range_high_inr: 720000,
  expected_fair_market_range_low_lakhs: 5.8,
  expected_fair_market_range_high_lakhs: 7.2,
  deal_quality: 'FAIR_DEAL',
  recommendation_verdict: 'STRONG CONSIDERATION',
  safety_stars: 4,
  safety_agency: 'Global NCAP',
  bodyshell_integrity: 'Stable',
  typical_annual_maintenance_inr: '₹8,500 – ₹12,000',
  maintenance_complexity: 'MODERATE',
  reliability_watchpoints_count: 2,
  one_line_summary: 'Reliable, efficient family hatchback with strong resale liquidity and stable bodyshell.',
};

const mockDeal: DealAnalysisResponse = {
  canonical_vehicle_id: 'v1',
  vehicle_summary: 'Maruti Suzuki Swift ZXi',
  asking_price: 640000,
  asking_price_formatted: '₹6.40 Lakh',
  asking_price_evidence_state: 'USER_INPUT',
  deal_quality: 'FAIR_DEAL',
  deal_quality_label: 'Fair Deal',
  price_deviation: {
    absolute_difference: -10000,
    relative_difference_percent: -1.5,
    user_facing_summary: 'Within Fair Range',
    evidence_state: 'SUPPORTED',
  },
  range_position: {
    position_ratio: 0.5,
    category: 'INSIDE_RANGE',
    explanation: 'Asking price falls well inside expected conformal boundary.',
  },
  anomaly_status: {
    is_anomaly: false,
    anomaly_type: 'NONE',
    anomaly_metric: 'CONFORMAL_RESIDUAL',
  },
  valuation: {
    estimated_fair_market_value: 650000,
    estimated_fair_market_value_formatted: '₹6.50 Lakh',
    expected_fair_market_lower: 580000,
    expected_fair_market_upper: 720000,
    confidence_state: 'HIGH',
    evidence_quality: 'GOOD',
    model_version: 'v1.0.0',
    target_semantic_concept: 'HISTORICAL_ASKING_PRICE_CONFORMAL_MEDIAN',
  },
  negotiation: {
    target_range_formatted: '₹6.10L – ₹6.35L',
    negotiation_strength: 'MODERATE',
    walk_away_signal: false,
    rationale: 'Asking price is aligned with historical fair market distribution.',
    safety_disclaimer: 'Guidance only.',
  },
  explanation: 'Asking price is aligned with historical fair market distribution.',
  risk_signals: [],
  limitations: [],
  analysis_timestamp: '2026-10-09T00:00:00Z',
};

const mockDecision: DecisionEvaluationResponse = {
  canonical_vehicle_id: 'v1',
  vehicle_summary: 'Maruti Suzuki Swift ZXi',
  intrinsic_score: 82,
  user_fit_score: 91,
  vehicle_fit_score: 91,
  deal_fit_score: 85,
  hard_constraint_status: 'PASS',
  recommendation_verdict: 'STRONG_CONSIDERATION',
  verdict_label: 'Exceptional Personal Match',
  fit_breakdown: {
    budget_fit: 90,
    usage_fit: 95,
    family_fit: 92,
    component_weights: {},
    overall_user_fit_score: 91,
    decision_quality: 'HIGH',
    data_limitations: [],
  },
  why_it_fits: [
    'Fits acquisition budget ceiling of ₹7.0 Lakhs',
    'Matches 5-seater family requirement comfortably',
    'Low maintenance exposure aligns with high sensitivity',
  ],
  why_it_may_not_fit: [],
  tradeoffs: [
    'Engine performance is adequate rather than spirited',
    'Highway stability is moderate compared to heavier European sedans',
  ],
  what_to_verify_before_buying: [
    'Inspect AMT clutch actuator calibration if automated variant',
    'Verify service history for suspension bushing wear',
  ],
  alternatives: [],
  decision_quality: 'HIGH',
  limitations: [
    'Annual driving distance not specified; default consumption assumed',
  ],
};

describe('Phase 18 — Production Decision Experience & Trust UX Tests', () => {
  it('renders DecisionSummaryCard with 3 mathematically separated pillars (Section 4B)', () => {
    render(
      <DecisionSummaryCard
        summary={mockSummary}
        dealAnalysis={mockDeal}
        decision={mockDecision}
      />
    );

    // Pillar 1: Vehicle Quality
    expect(screen.getByText('1. Vehicle Quality')).toBeInTheDocument();
    expect(screen.getByText('82')).toBeInTheDocument();
    expect(screen.getByText(/Independent of asking price/i)).toBeInTheDocument();

    // Pillar 2: Your Fit
    expect(screen.getByText('2. Your Fit')).toBeInTheDocument();
    expect(screen.getByText('91')).toBeInTheDocument();
    expect(screen.getByText(/Matches your specific usage/i)).toBeInTheDocument();

    // Pillar 3: Deal Assessment
    expect(screen.getByText('3. Deal Assessment')).toBeInTheDocument();
    expect(screen.getAllByText('FAIR DEAL').length).toBeGreaterThan(0);
    expect(screen.getByText(/Asking ₹6.40L vs ₹6.50L FMV/i)).toBeInTheDocument();
  });

  it('renders Section 5 "Should I Consider This?" card with grounded strong points and watch-outs', () => {
    render(
      <DecisionSummaryCard
        summary={mockSummary}
        dealAnalysis={mockDeal}
        decision={mockDecision}
      />
    );

    expect(screen.getByText('Should I Consider This Vehicle?')).toBeInTheDocument();
    expect(screen.getByText(/Strong Points \(Grounded Evidence\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Key Watch-Outs Before Deciding/i)).toBeInTheDocument();

    // Strong point from safety rating
    expect(screen.getByText(/Strong structural safety profile \(4★ Global NCAP rating\)/i)).toBeInTheDocument();
    // Watch-out from reliability watchpoints
    expect(screen.getByText(/2 documented mechanical watchpoints require inspection before purchase/i)).toBeInTheDocument();
  });

  it('provides Section 6 deterministic "Why this result?" factor explainability without decorative AI', () => {
    render(
      <DecisionSummaryCard
        summary={mockSummary}
        dealAnalysis={mockDeal}
        decision={mockDecision}
      />
    );

    const toggleBtn = screen.getByText(/Why this result\? \(Deterministic Factor Explainability\)/i);
    expect(toggleBtn).toBeInTheDocument();
    fireEvent.click(toggleBtn);

    // Explains deterministic score dimensions
    expect(screen.getByText(/Based on CarSpective's Phase 5 Intrinsic Scoring Engine/i)).toBeInTheDocument();
    expect(screen.getByText(/Structural Safety \(25% weight\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Reliability & Longevity \(25% weight\)/i)).toBeInTheDocument();
    expect(screen.getByText(/strictly isolated from seller asking price and user profile settings/i)).toBeInTheDocument();

    // Never says 'AI thinks'
    expect(screen.queryByText(/AI thinks/i)).not.toBeInTheDocument();
  });

  it('supports Section 18 progressive disclosure levels (L1, L2, L3 Lineage)', () => {
    render(
      <DecisionSummaryCard
        summary={mockSummary}
        dealAnalysis={mockDeal}
        decision={mockDecision}
      />
    );

    const l3Btn = screen.getByText('L3 Lineage');
    fireEvent.click(l3Btn);

    expect(screen.getByText(/Data Provenance & Freshness \(Phase 16 & 17 Governed Audits\)/i)).toBeInTheDocument();
    expect(screen.getByText(/57,480 Indian used-car seller asking-price observations \(2018–2024\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Never claimed as transaction prices/i)).toBeInTheDocument();
    expect(screen.getByText(/4a4ccf3f78/i)).toBeInTheDocument();
  });

  it('verifies Section 17 contextual AI assistant prompts', () => {
    render(
      <AssistantDrawerIntegration
        vehicleSummary="Maruti Suzuki Swift 2021"
        score={82}
        fmvLakhs={6.5}
      />
    );

    expect(screen.getByText('Why is this car rated 82?')).toBeInTheDocument();
    expect(screen.getByText('Is this asking price fair?')).toBeInTheDocument();
    expect(screen.getByText('What should I inspect first?')).toBeInTheDocument();
    expect(screen.getByText('How does this compare with the alternatives?')).toBeInTheDocument();
    expect(screen.getByText('What are the biggest ownership risks?')).toBeInTheDocument();
    expect(screen.getByText('What current market evidence do we have?')).toBeInTheDocument();
  });

  it('verifies Section 16 inspection professional disclaimer', () => {
    const mockInspSummary = {
      total_applicable_items: 49,
      critical_items_count: 8,
      top_watchpoints: ['Engine Oil Contamination', 'Brake Pad Thickness'],
      documentation_requirements: ['RC Copy', 'Insurance Valid'],
      purchase_readiness: 'INSPECTION_RECOMMENDED',
    };

    render(
      <InspectionCalloutSection
        summary={mockInspSummary}
        onOpenChecklist={vi.fn()}
      />
    );

    expect(screen.getByText(/This checklist supports decision-making and does not replace a professional inspection/i)).toBeInTheDocument();
  });

  it('verifies Section 9 requirement provenance chips in RequirementsEditor', () => {
    const profile: UserRequirementsProfile = {
      budget_max_inr: 700000,
      usage_profile: 'CITY',
      provenance_map: {
        budget: { state: 'USER_EXPLICIT' },
        usage: { state: 'USER_INFERRED' },
      },
    };

    render(
      <RequirementsEditor
        profile={profile}
        onChange={vi.fn()}
      />
    );

    // Budget has USER_EXPLICIT -> 'You specified'
    const budgetChip = screen.getByTestId('provenance-budget');
    expect(budgetChip).toHaveTextContent('You specified');

    // Usage has USER_INFERRED -> 'Inferred from prompt'
    const usageChip = screen.getByTestId('provenance-usage');
    expect(usageChip).toHaveTextContent('Inferred from prompt');

    // Transmission is NOT_SPECIFIED -> 'Not specified'
    const transChip = screen.getByTestId('provenance-transmission');
    expect(transChip).toHaveTextContent('Not specified');
  });

  it('verifies Section 10 User Fit explanation: Matches, Doesn\'t fully match, and Missing information', () => {
    render(
      <PersonalizedDecisionCard
        decision={mockDecision}
      />
    );

    expect(screen.getByText('Matches your needs')).toBeInTheDocument();
    expect(screen.getByText('Fits acquisition budget ceiling of ₹7.0 Lakhs')).toBeInTheDocument();

    expect(screen.getByText("Doesn't fully match")).toBeInTheDocument();
    expect(screen.getByText('Engine performance is adequate rather than spirited')).toBeInTheDocument();

    expect(screen.getByText('Missing information')).toBeInTheDocument();
    expect(screen.getByText(/Annual driving distance not specified/i)).toBeInTheDocument();
  });

  it('verifies Section 20 empty states adhere to 3-part structure (What is missing, Why it matters, What you can do next)', () => {
    render(
      <EmptyState
        title="No Live Market Observations"
        missingInfo="Live multi-metro dealer inventory feeds for this variant"
        whyItMatters="Without current observations, real-time demand pressure cannot be observed"
        nextStep="Rely on the historical 2018–2024 empirical baseline and conformal FMV range"
      />
    );

    expect(screen.getByText(/1. What is missing:/i)).toBeInTheDocument();
    expect(screen.getByText(/Live multi-metro dealer inventory feeds/i)).toBeInTheDocument();

    expect(screen.getByText(/2. Why it matters:/i)).toBeInTheDocument();
    expect(screen.getByText(/real-time demand pressure cannot be observed/i)).toBeInTheDocument();

    expect(screen.getByText(/3. What you can do next:/i)).toBeInTheDocument();
    expect(screen.getByText(/historical 2018–2024 empirical baseline/i)).toBeInTheDocument();
  });
});
