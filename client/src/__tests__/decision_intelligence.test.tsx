import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { RequirementsEditor } from '../features/decision/RequirementsEditor';
import { PersonalizedDecisionCard } from '../features/decision/PersonalizedDecisionCard';
import { PersonalizedShortlistDrawer } from '../features/decision/PersonalizedShortlistDrawer';
import { decisionApi } from '../api/decisionApi';
import {
  UserRequirementsProfile,
  DecisionEvaluationResponse,
  PersonalizedComparisonResponse,
} from '../types';

vi.mock('../api/decisionApi', () => ({
  decisionApi: {
    parseQuery: vi.fn(),
    evaluateVehicle: vi.fn(),
    rankShortlist: vi.fn(),
    compareVehicles: vi.fn(),
    prioritizeInspection: vi.fn(),
  },
}));

describe('Phase 15 — Personalized Decision Intelligence Frontend Components', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const mockProfile: UserRequirementsProfile = {
    budget_max_inr: 1000000,
    budget_flexible: true,
    usage_profile: 'CITY',
    family_size: 4,
    transmission_preferences: ['Automatic'],
    fuel_preferences: ['Petrol'],
    safety_priority: 'HIGH',
    maintenance_priority: 'HIGH',
    hard_constraints: {
      strict_budget_ceiling: false,
      strict_transmission: false,
      strict_fuel_type: false,
      strict_min_seating: false,
      strict_body_type: false,
    },
  };

  const mockDecision: DecisionEvaluationResponse = {
    canonical_vehicle_id: 'tata::nexon::1st-gen::2021::xz-plus',
    vehicle_summary: '2021 Tata Nexon XZ Plus',
    intrinsic_score: 86,
    user_fit_score: 91,
    vehicle_fit_score: 91,
    deal_fit_score: 84,
    hard_constraint_status: 'PASS',
    recommendation_verdict: 'STRONG CONSIDERATION',
    verdict_label: 'Exceptional Match For Your Profile',
    fit_breakdown: {
      budget_fit: 95,
      usage_fit: 90,
      safety_fit: 98,
      reliability_fit: 82,
      maintenance_fit: 80,
      component_weights: { budget_fit: 0.3, safety_fit: 0.4, usage_fit: 0.3 },
      overall_user_fit_score: 91,
      decision_quality: 'HIGH',
      data_limitations: [],
    },
    why_it_fits: [
      '5-Star Global NCAP safety rating directly fulfills your critical safety requirement.',
      'Automatic transmission provides effortless daily driving in heavy urban traffic.',
    ],
    why_it_may_not_fit: [],
    tradeoffs: [
      'Tradeoff: Robust crash safety comes with heavier vehicle weight and slightly lower city fuel economy.',
    ],
    what_to_verify_before_buying: [
      'Check transmission fluid quality and test shift smoothness between 1st and 2nd gear.',
    ],
    alternatives: [
      {
        canonical_vehicle_id: 'maruti::brezza::2nd-gen::2022',
        vehicle_summary: '2022 Maruti Brezza',
        intrinsic_score: 82,
        user_fit_score: 87,
        advantage_over_target: 'Significantly lower routine maintenance and smoother engine.',
        tradeoff_vs_target: 'Lacks the 5-star crash safety rating and thick sheet metal of the Nexon.',
        verdict_label: 'Better For Low Running Cost',
      },
    ],
    decision_quality: 'HIGH',
    limitations: [],
    computation_latency_ms: 45.2,
  };

  it('RequirementsEditor renders profile controls and triggers onChange on user interaction', () => {
    const handleChange = vi.fn();
    render(<RequirementsEditor profile={mockProfile} onChange={handleChange} />);

    expect(screen.getByText('Personalized Decision Profile')).toBeInTheDocument();
    expect(screen.getByDisplayValue('1000000')).toBeInTheDocument();

    const cityBtn = screen.getByText('CITY');
    expect(cityBtn).toBeInTheDocument();

    // Toggle Highway
    const highwayBtn = screen.getByText('HIGHWAY');
    fireEvent.click(highwayBtn);
    expect(handleChange).toHaveBeenCalledWith(
      expect.objectContaining({ usage_profile: 'HIGHWAY' })
    );

    // Reset button
    const resetBtn = screen.getByTitle('Reset all preferences');
    fireEvent.click(resetBtn);
    expect(handleChange).toHaveBeenCalledWith(
      expect.objectContaining({ budget_max_inr: undefined })
    );
  });

  it('RequirementsEditor parses natural language prompt and populates profile', async () => {
    const handleChange = vi.fn();
    (decisionApi.parseQuery as any).mockResolvedValueOnce({
      parsed_profile: {
        budget_max_inr: 1200000,
        transmission_preferences: ['Automatic'],
        safety_priority: 'CRITICAL',
      },
      extracted_fields_count: 3,
      clarification_questions: ['Did you mean acquisition price or 5-year budget?'],
      provenance_summary: {},
    });

    render(<RequirementsEditor profile={mockProfile} onChange={handleChange} />);

    const input = screen.getByPlaceholderText(/e.g. 'I need an automatic SUV/i);
    fireEvent.change(input, { target: { value: 'automatic car under 12 lakh with top safety' } });

    const applyBtn = screen.getByText('Apply');
    fireEvent.click(applyBtn);

    await waitFor(() => {
      expect(decisionApi.parseQuery).toHaveBeenCalledWith('automatic car under 12 lakh with top safety');
      expect(handleChange).toHaveBeenCalledWith(
        expect.objectContaining({
          budget_max_inr: 1200000,
          safety_priority: 'CRITICAL',
        })
      );
    });
  });

  it('PersonalizedDecisionCard renders User Fit Score, Decision Quality, and separate Vehicle vs Deal Fit', () => {
    render(<PersonalizedDecisionCard decision={mockDecision} />);

    expect(screen.getByText('STRONG CONSIDERATION')).toBeInTheDocument();
    expect(screen.getByText('Exceptional Match For Your Profile')).toBeInTheDocument();
    expect(screen.getByText('Quality: HIGH')).toBeInTheDocument();
    expect(screen.getByText('91')).toBeInTheDocument(); // User Fit Score

    // Vehicle Fit vs Deal Fit vs Intrinsic Truth
    expect(screen.getByText('Vehicle Fit (Suitability)')).toBeInTheDocument();
    expect(screen.getByText('91/100')).toBeInTheDocument();
    expect(screen.getByText('Intrinsic Vehicle Truth')).toBeInTheDocument();
    expect(screen.getByText('86/100')).toBeInTheDocument();
    expect(screen.getByText('Deal Fit (Asking Price)')).toBeInTheDocument();
    expect(screen.getByText('84/100')).toBeInTheDocument();

    // Why it fits & tradeoffs
    expect(screen.getByText(/5-Star Global NCAP safety rating/i)).toBeInTheDocument();
    expect(screen.getByText(/Robust crash safety comes with heavier vehicle weight/i)).toBeInTheDocument();
    expect(screen.getByText(/2022 Maruti Brezza/i)).toBeInTheDocument();
  });

  it('PersonalizedDecisionCard displays Hard Constraint Violation banner when status is FAIL', () => {
    const failedDecision: DecisionEvaluationResponse = {
      ...mockDecision,
      hard_constraint_status: 'FAIL',
      recommendation_verdict: 'NOT RECOMMENDED',
      verdict_label: 'Violates Stated Hard Constraints',
      why_it_may_not_fit: ['Asking price (₹12.5 Lakh) exceeds strict budget ceiling of ₹10 Lakh.'],
    };

    render(<PersonalizedDecisionCard decision={failedDecision} />);

    expect(screen.getByText('NOT RECOMMENDED')).toBeInTheDocument();
    expect(screen.getByText('Violates Stated Hard Constraints')).toBeInTheDocument();
    expect(screen.getByText('Hard Constraint Violation')).toBeInTheDocument();
    expect(screen.getByText(/exceeds strict budget ceiling/i)).toBeInTheDocument();
  });

  it('PersonalizedShortlistDrawer renders Best Overall vs Best For You and explains divergence', async () => {
    const mockComparisonRes: PersonalizedComparisonResponse = {
      general_winner_index: 0,
      general_winner_rationale: 'Nexon has highest intrinsic score (86/100).',
      user_winner_index: 1,
      user_winner_rationale: 'Brezza matches your budget and low maintenance requirements (92/100).',
      divergence_explanation: 'While Nexon is the stronger vehicle overall, Brezza fits your specific budget and low maintenance priority better.',
      vehicles: [
        mockDecision,
        {
          ...mockDecision,
          canonical_vehicle_id: 'maruti::brezza::2nd-gen::2022',
          vehicle_summary: '2022 Maruti Brezza',
          intrinsic_score: 82,
          user_fit_score: 92,
        },
      ],
      computation_latency_ms: 55.4,
    };

    (decisionApi.compareVehicles as any).mockResolvedValueOnce(mockComparisonRes);

    render(
      <PersonalizedShortlistDrawer
        isOpen={true}
        onClose={vi.fn()}
        shortlistIds={['tata::nexon::1st-gen::2021', 'maruti::brezza::2nd-gen::2022']}
        onRemoveVehicle={vi.fn()}
        profile={mockProfile}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Personalized Shortlist & Comparison (2)')).toBeInTheDocument();
      expect(screen.getByText('Personalization Divergence Detected')).toBeInTheDocument();
      expect(screen.getByText(/While Nexon is the stronger vehicle overall/i)).toBeInTheDocument();
      expect(screen.getByText('Best Vehicle Overall')).toBeInTheDocument();
      expect(screen.getByText('Best For You')).toBeInTheDocument();
    });
  });
});
