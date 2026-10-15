import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ValuationCard } from '../features/valuation/ValuationCard';
import { DealAnalyzerCard } from '../features/deal/DealAnalyzerCard';
import { Vehicle3DViewer } from '../features/vehicle/Vehicle3DViewer';
import { ComparisonMatrix } from '../features/comparison/ComparisonMatrix';
import { Score } from '../components/common/Score';

describe('Critical UX & Governance Test Suite', () => {
  it('renders Limited Analysis state when valuation data is insufficient', () => {
    const insufficientValuation = {
      vehicle_resolution_status: 'EXACT_MATCH',
      confidence_state: 'INSUFFICIENT_DATA' as const,
      evidence_quality: 'INSUFFICIENT_DATA',
      model_metadata: {
        algorithm: 'LightGBM',
        version: 'v1.0',
        dataset_reference: '57,480 historical Indian used-car listing records',
        target_semantic_concept: 'Statistical Model Estimate of the Historical Market Asking-Price Baseline',
      },
      valuation_timestamp: '2026-10-08T00:00:00Z',
      limitations: ['Insufficient records to compute reliable conformal interval.'],
    };

    render(<ValuationCard valuation={insufficientValuation} />);
    expect(screen.getByText('Limited Analysis')).toBeInTheDocument();
    expect(screen.getByText(/Insufficient historical listing records/i)).toBeInTheDocument();
    // Invariant: Never renders fake precision or numbers when insufficient
    expect(screen.queryByText(/Estimated Fair Market Value/i)).not.toBeInTheDocument();
  });

  it('renders full valuation card with asking-price baseline disclaimer', () => {
    const validValuation = {
      estimated_fair_market_value: 850000,
      expected_fair_market_range: {
        lower_bound: 780000,
        upper_bound: 920000,
        confidence_interval_percent: 80,
        multiplier: 0.21,
      },
      vehicle_resolution_status: 'EXACT_MATCH',
      confidence_state: 'HIGH_CONFIDENCE' as const,
      evidence_quality: 'EMPIRICAL',
      model_metadata: {
        algorithm: 'LightGBM',
        version: 'v1.0',
        dataset_reference: '57,480 historical Indian used-car listing records',
        target_semantic_concept: 'Statistical Model Estimate of the Historical Market Asking-Price Baseline',
      },
      valuation_timestamp: '2026-10-08T00:00:00Z',
      limitations: ['Statistical model estimate of historical seller asking prices.'],
    };

    render(<ValuationCard valuation={validValuation} askingPrice={870000} />);
    expect(screen.getByText(/Estimated Fair Market Value/i)).toBeInTheDocument();
    expect(screen.getByText('₹8.50 L')).toBeInTheDocument();
    expect(screen.getByText(/Empirical Asking-Price Baseline:/i)).toBeInTheDocument();
    expect(screen.getByText(/57,480 historical Indian used-car listing records/i)).toBeInTheDocument();
  });

  it('deals with unusually low asking prices by advising caution rather than calling it simply great', () => {
    const anomalousDeal = {
      asking_price: 350000,
      asking_price_formatted: '₹3,50,000',
      asking_price_evidence_state: 'UNVERIFIED',
      deal_quality: 'UNUSUALLY_LOW_ASKING_PRICE' as const,
      deal_quality_label: 'Unusually Low Asking Price',
      vehicle_summary: '2021 Honda City',
      valuation: {
        estimated_fair_market_value: 850000,
        confidence_state: 'HIGH_CONFIDENCE',
        evidence_quality: 'EMPIRICAL',
        model_version: 'v1.0',
        target_semantic_concept: 'Historical baseline',
      },
      price_deviation: {
        absolute_difference: -500000,
        relative_difference_percent: -58.8,
        user_facing_summary: '58.8% below expected asking price baseline',
        evidence_state: 'MODEL_ESTIMATE',
      },
      range_position: {
        category: 'BELOW_RANGE' as const,
        explanation: 'Far below fair market range bounds.',
      },
      anomaly_status: {
        is_anomaly: true,
        anomaly_type: 'ANOMALOUS_LOW',
        anomaly_metric: 'Z_SCORE',
      },
      negotiation: {
        target_price: 800000,
        negotiation_strength: 'LIMITED' as const,
        walk_away_signal: false,
        rationale: 'Anomalously low price requires mechanical scrutiny.',
        safety_disclaimer: 'Statistical guidance.',
      },
      risk_signals: [],
      explanation: 'Vehicle is listed far below reasonable market bounds.',
      limitations: [],
      analysis_timestamp: '2026-10-08T00:00:00Z',
    };

    render(<DealAnalyzerCard dealAnalysis={anomalousDeal} onAnalyze={() => {}} />);
    expect(screen.getByText(/Unusually Low Price/i)).toBeInTheDocument();
    expect(screen.getByText(/Caution: Low price does not guarantee a good purchase/i)).toBeInTheDocument();
  });

  it('INVARIANT: 3D viewer refuses to substitute Porsche 911 GLB for non-Porsche models', () => {
    render(<Vehicle3DViewer brand="Honda" model="City" year={2021} />);
    expect(screen.getByText(/Verified Dimensional Geometry/i)).toBeInTheDocument();
    expect(screen.getByText(/refuses to substitute unrelated 3D models/i)).toBeInTheDocument();
    expect(screen.queryByText(/Load Interactive 3D Model/i)).not.toBeInTheDocument();
  });

  it('INVARIANT: Score component strictly separates vehicle proposition from deal asking price', () => {
    const mockScore = {
      vehicle_summary: 'Honda City 2021',
      overall_score: 84,
      overall_score_formatted: '84/100',
      evidence_quality: 'HIGH' as const,
      dimensions: [
        {
          dimension_name: 'Structural Safety',
          score: 88,
          score_formatted: '88/100',
          evidence_state: 'VERIFIED' as const,
          confidence: 'HIGH',
          contributing_factors: ['Global NCAP 4-Star'],
          sources: ['Global NCAP Official Test'],
          limitations: [],
        },
      ],
      explanation: {
        strong_areas: ['Structural Safety'],
        watch_areas: [],
        summary: 'Exceptional structural integrity.',
      },
      limitations: [],
      score_timestamp: '2026-10-08T00:00:00Z',
    };

    render(<Score score={mockScore} />);
    expect(screen.getByText(/Vehicle Quality ≠ Deal Quality:/i)).toBeInTheDocument();
    expect(screen.getByText(/This score measures intrinsic engineering and ownership merit/i)).toBeInTheDocument();
    expect(screen.getByText('84')).toBeInTheDocument();
  });
});
