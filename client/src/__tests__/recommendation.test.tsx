import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { RecommendationCard } from '../features/recommendation/RecommendationCard';
import { RecommendationResponse } from '../types';

describe('RecommendationCard Component Tests', () => {
  const mockRecommendation: RecommendationResponse = {
    canonical_vehicle_id: 'tata-nexon-2021',
    vehicle_summary: 'Tata Nexon 2021 XZ+',
    verdict: 'STRONG CONSIDERATION',
    verdict_label: 'Strong Consideration',
    carspective_score: 87,
    carspective_score_quality: 'HIGH',
    deal_quality: 'FAIR_DEAL',
    user_fit: {
      overall_fit: 91,
      budget_fit: 95,
      usage_fit: 90,
      family_fit: 88,
      powertrain_fit: 92,
      priority_alignment: 90,
      fit_summary: 'Excellent alignment with daily urban commute and family safety priorities.',
      evidence_state: 'USER_STATED',
    },
    risk_summary: {},
    explanation: {
      strongest_positive_factor: '5-Star Adult Safety rating and high ground clearance.',
      biggest_tradeoff: 'Slightly firmer ride quality over broken city tarmac.',
      deal_consideration: 'Asking price is aligned with expected historical baseline.',
      user_fit_consideration: 'Fits within user specified budget.',
      detailed_rationale: 'Solid choice for safety-conscious buyers.',
    },
    alternatives: [
      {
        brand: 'Hyundai',
        model: 'Venue',
        manufacturing_year: 2021,
        typical_price_inr: 820000,
        typical_price_formatted: '₹8.20 L',
        carspective_score: 79,
        rationale: 'More refined petrol engine option.',
        advantage_over_target: 'Smoother DCT transmission.',
      },
    ],
    limitations: [],
    analysis_timestamp: '2026-10-08T00:00:00Z',
  };

  it('renders verdict, positive factor, tradeoff, and fit percentage', () => {
    render(<RecommendationCard recommendation={mockRecommendation} />);
    expect(screen.getByText('STRONG CONSIDERATION')).toBeInTheDocument();
    expect(screen.getByText(/5-Star Adult Safety rating/i)).toBeInTheDocument();
    expect(screen.getByText(/Slightly firmer ride quality/i)).toBeInTheDocument();
    expect(screen.getByText(/User-Fit Alignment: 91%/i)).toBeInTheDocument();
  });

  it('renders market alternatives and triggers onSelectAlternative callback', () => {
    const handleSelectAlt = vi.fn();
    render(
      <RecommendationCard
        recommendation={mockRecommendation}
        onSelectAlternative={handleSelectAlt}
      />
    );

    expect(screen.getByText(/Hyundai Venue \(2021\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Typical: ₹8.20 L/i)).toBeInTheDocument();

    fireEvent.click(screen.getByText(/Hyundai Venue \(2021\)/i));
    expect(handleSelectAlt).toHaveBeenCalledTimes(1);
  });
});
