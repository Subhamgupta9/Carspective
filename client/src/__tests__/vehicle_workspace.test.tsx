import { describe, it, expect, vi } from 'vitest';
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ExecutiveSummaryCard } from '../features/vehicle/workspace/ExecutiveSummaryCard';
import { IdentityConfidenceCard } from '../features/vehicle/workspace/IdentityConfidenceCard';
import { MarketValueCard } from '../features/vehicle/workspace/MarketValueCard';
import { DealAnalyzerSection } from '../features/vehicle/workspace/DealAnalyzerSection';
import { VehicleScoreSection } from '../features/vehicle/workspace/VehicleScoreSection';
import { KeySpecsSection } from '../features/vehicle/workspace/KeySpecsSection';
import { SafetySection } from '../features/vehicle/workspace/SafetySection';
import { InspectionCalloutSection } from '../features/vehicle/workspace/InspectionCalloutSection';
import { OwnershipSection } from '../features/vehicle/workspace/OwnershipSection';
import { AppProvider } from '../state/AppContext';
import { VehiclePage } from '../pages/VehiclePage';
import { vehicleApi } from '../api/vehicleApi';
import {
  ExecutiveSummary,
  IdentityConfidenceInfo,
  ValuationResponse,
  ScoreResponse,
  VehicleWorkspaceResponse,
} from '../types';

describe('Phase 13 — Vehicle Intelligence Workspace Components', () => {
  const mockExecutiveSummary: ExecutiveSummary = {
    carspective_score: 77,
    score_band: 'GOOD',
    estimated_fair_market_value_inr: 626000,
    estimated_fair_market_value_lakhs: 6.26,
    expected_fair_market_range_low_inr: 490000,
    expected_fair_market_range_high_inr: 763000,
    expected_fair_market_range_low_lakhs: 4.9,
    expected_fair_market_range_high_lakhs: 7.63,
    deal_quality: 'FAIR_DEAL',
    recommendation_verdict: 'CONSIDER',
    safety_stars: 2,
    safety_agency: 'Global NCAP',
    bodyshell_integrity: 'Unstable',
    typical_annual_maintenance_inr: '₹5,000 – ₹7,000',
    maintenance_complexity: 'Low',
    reliability_watchpoints_count: 2,
    one_line_summary: 'Maruti Suzuki Swift (2021) scores 77/100 with consider verdict and fair market baseline around ₹6.26 Lakhs.',
  };

  const mockConfidenceExact: IdentityConfidenceInfo = {
    level: 'exact',
    title: 'Exact Canonical Specification',
    description: 'Fully resolved down to Maruti Suzuki Swift 3rd Generation (2021) ZXi trim.',
    is_confirmed: true,
    needs_user_confirmation: false,
    sibling_variants: [
      { name: 'VXi', slug: 'vxi', powertrains: ['1.2 Petrol Manual'], canonical_id: 'swift::vxi', is_current: false },
      { name: 'ZXi', slug: 'zxi', powertrains: ['1.2 Petrol Manual'], canonical_id: 'swift::zxi', is_current: true },
    ],
    sibling_generations: [
      { name: '3rd Generation', slug: 'gen-3-2018', year_start: 2018, year_end: 2024, canonical_id: 'swift::gen-3', is_current: true },
    ],
  };

  const mockConfidenceAmbiguous: IdentityConfidenceInfo = {
    level: 'ambiguous',
    title: 'Ambiguous Identity — Please Confirm Generation & Trim',
    description: 'Matched vehicle Maruti Suzuki Swift. Multiple generations exist in our database.',
    is_confirmed: false,
    needs_user_confirmation: true,
    sibling_variants: [],
    sibling_generations: [
      { name: '2nd Generation', slug: 'gen-2-2011', year_start: 2011, year_end: 2017, canonical_id: 'swift::gen-2', is_current: false },
      { name: '3rd Generation', slug: 'gen-3-2018', year_start: 2018, year_end: 2024, canonical_id: 'swift::gen-3', is_current: true },
    ],
  };

  it('renders ExecutiveSummaryCard with all key decision anchors', () => {
    render(<ExecutiveSummaryCard summary={mockExecutiveSummary} coverageTier="TIER_1_DEEP" />);

    expect(screen.getByText('Executive Intelligence Summary')).toBeDefined();
    expect(screen.getByText('Verdict: CONSIDER')).toBeDefined();
    expect(screen.getByText('77/100')).toBeDefined();
    expect(screen.getByText('₹6.26 L')).toBeDefined();
    expect(screen.getByText(/Range: ₹4.90 L – ₹7.63 L/)).toBeDefined();
    expect(screen.getByText('2 / 5 ★')).toBeDefined();
    expect(screen.getByText('₹5,000 – ₹7,000')).toBeDefined();
    expect(screen.getByText(/2 documented watchpoints/)).toBeDefined();
    expect(screen.getByText(/Maruti Suzuki Swift \(2021\) scores 77\/100/)).toBeDefined();
  });

  it('renders IdentityConfidenceCard in exact state with variant switcher', () => {
    const onSelectMock = vi.fn();
    render(<IdentityConfidenceCard confidence={mockConfidenceExact} onSelectCanonicalVehicle={onSelectMock} />);

    expect(screen.getByText('Exact Canonical Specification')).toBeDefined();
    expect(screen.getByText('Exact Canonical Identity')).toBeDefined();

    const vxiBtn = screen.getByText('VXi');
    expect(vxiBtn).toBeDefined();
    fireEvent.click(vxiBtn);
    expect(onSelectMock).toHaveBeenCalledWith('swift::vxi');
  });

  it('renders IdentityConfidenceCard in ambiguous state prompting user confirmation', () => {
    render(<IdentityConfidenceCard confidence={mockConfidenceAmbiguous} />);

    expect(screen.getByText('Ambiguous — Confirmation Required')).toBeDefined();
    expect(screen.getByText(/Select your exact trim below to confirm/i)).toBeDefined();
    expect(screen.getByText(/2nd Generation/)).toBeDefined();
    expect(screen.getByText(/3rd Generation/)).toBeDefined();
  });

  it('renders MarketValueCard with conformal expected range framing', () => {
    const mockValuation: ValuationResponse = {
      canonical_vehicle_id: 'maruti-suzuki::swift::gen-3-2018::2021::zxi',
      vehicle_resolution_status: 'EXACT_MATCH',
      estimated_fair_market_value: 626000,
      expected_fair_market_range: {
        lower_bound: 490000,
        upper_bound: 763000,
        confidence_interval_percent: 80.0,
        multiplier: 0.2178,
      },
      confidence_state: 'HIGH_CONFIDENCE',
      evidence_quality: 'MODEL_ESTIMATE',
      model_metadata: {
        algorithm: 'LightGBM-Regressor',
        version: '1.0.0',
        dataset_reference: 'carspective_empirical_v1',
        target_semantic_concept: 'Fair Market Value',
      },
      valuation_timestamp: new Date().toISOString(),
      limitations: [],
    };

    render(<MarketValueCard valuation={mockValuation} />);

    expect(screen.getByText('Estimated Fair Market Value')).toBeDefined();
    expect(screen.getByText('₹6.26 Lakhs')).toBeDefined();
    expect(screen.getByText(/Expected Fair Market Range:/)).toBeDefined();
    expect(screen.getByText(/80% empirical conformal coverage/)).toBeDefined();
  });

  it('renders DealAnalyzerSection allowing custom asking price input', () => {
    const onEvalMock = vi.fn();
    render(
      <DealAnalyzerSection
        fairMarketValue={626000}
        onEvaluateDeal={onEvalMock}
      />
    );

    expect(screen.getByText('Commercial Deal Analyzer')).toBeDefined();
    const priceInput = screen.getByPlaceholderText('626000');
    fireEvent.change(priceInput, { target: { value: '650000' } });

    const submitBtn = screen.getByText('Evaluate Deal');
    fireEvent.click(submitBtn);

    expect(onEvalMock).toHaveBeenCalledWith(650000, undefined);
  });

  it('renders VehicleScoreSection with all 5 locked dimensions', () => {
    const mockScore: ScoreResponse = {
      canonical_vehicle_id: 'maruti-suzuki::swift::gen-3-2018::2021::zxi',
      vehicle_summary: 'Maruti Suzuki Swift 2021',
      overall_score: 77,
      overall_score_formatted: '77/100',
      evidence_quality: 'HIGH',
      dimensions: [
        { dimension_name: 'Structural Safety', score: 55, score_formatted: '55/100', evidence_state: 'VERIFIED', confidence: 'HIGH', contributing_factors: ['2-star Global NCAP', 'Unstable bodyshell'], sources: ['Global NCAP'], limitations: [] },
        { dimension_name: 'Reliability & Longevity', score: 85, score_formatted: '85/100', evidence_state: 'SUPPORTED', confidence: 'HIGH', contributing_factors: ['Durable K12 engine'], sources: ['Service Records'], limitations: [] },
        { dimension_name: 'Maintenance & Ownership', score: 92, score_formatted: '92/100', evidence_state: 'SUPPORTED', confidence: 'HIGH', contributing_factors: ['Widespread parts availability'], sources: ['OEM Network'], limitations: [] },
        { dimension_name: 'Resale & Market Liquidity', score: 88, score_formatted: '88/100', evidence_state: 'EMPIRICAL', confidence: 'HIGH', contributing_factors: ['High resale demand'], sources: ['Historical Listings'], limitations: [] },
        { dimension_name: 'Real-World Practicality', score: 72, score_formatted: '72/100', evidence_state: 'SUPPORTED', confidence: 'HIGH', contributing_factors: ['Compact city footprint'], sources: ['Tech Specs'], limitations: [] },
      ],
      explanation: {
        strong_areas: ['Maintenance & Ownership', 'Resale & Market Liquidity'],
        watch_areas: ['Structural Safety'],
        summary: 'Strong practical hatchback with low running cost, but compromised structural safety.',
      },
      limitations: [],
      score_timestamp: new Date().toISOString(),
    };

    render(<VehicleScoreSection score={mockScore} />);

    expect(screen.getByText('Intrinsic CarSpective Score')).toBeDefined();
    expect(screen.getByText('Structural Safety')).toBeDefined();
    expect(screen.getByText('Reliability & Longevity')).toBeDefined();
    expect(screen.getByText('Maintenance & Ownership')).toBeDefined();
    expect(screen.getByText('Resale & Market Liquidity')).toBeDefined();
    expect(screen.getByText('Real-World Practicality')).toBeDefined();
    expect(screen.getByText(/100% mathematically isolated from the asking price/)).toBeDefined();
  });

  it('renders SafetySection scoped strictly to generation', () => {
    const mockSafety = {
      organization: 'Global NCAP',
      test_year: 2018,
      adult_stars: 2,
      child_stars: 2,
      bodyshell_integrity: 'Unstable',
      standard_safety_equipment: 'Dual Front Airbags, ABS',
      evidence_state: 'VERIFIED' as const,
    };

    render(<SafetySection safety={mockSafety} generationName="3rd Generation" />);

    expect(screen.getByText('Safety & Crash Test Assessment')).toBeDefined();
    expect(screen.getAllByText('★★☆☆☆').length).toBe(2);
    expect(screen.getByText('Unstable')).toBeDefined();
    expect(screen.getByText(/This crash rating applies exclusively to 3rd Generation/)).toBeDefined();
  });

  it('renders InspectionCalloutSection with top watchpoints and checklist button', () => {
    const mockInspSummary = {
      total_applicable_items: 48,
      critical_items_count: 5,
      top_watchpoints: ['Engine: Check oil seepage near valve cover', 'Brakes: Check front disc pad wear'],
      documentation_requirements: ['Registration Certificate (RC)', 'Insurance Policy Document'],
      purchase_readiness: 'VERIFY_BEFORE_NEGOTIATING',
    };
    const onOpenMock = vi.fn();

    render(<InspectionCalloutSection summary={mockInspSummary} onOpenChecklist={onOpenMock} />);

    expect(screen.getByText(/Pre-Purchase Physical Inspection Intelligence/)).toBeDefined();
    expect(screen.getByText(/VERIFY BEFORE NEGOTIATING/)).toBeDefined();
    expect(screen.getByText('Engine: Check oil seepage near valve cover')).toBeDefined();
    expect(screen.getByText('Registration Certificate (RC)')).toBeDefined();

    const launchBtn = screen.getByText(/Open Full Interactive Checklist/);
    fireEvent.click(launchBtn);
    expect(onOpenMock).toHaveBeenCalled();
  });

  it('renders OwnershipSection with missing optional TCO and risk repair costs without toLocaleString crash', () => {
    const mockInnovaOwnershipIntelligence = {
      canonical_vehicle_id: 'toyota::innova-crysta::gen-1-2016::2016::gx',
      model_slug: 'innova-crysta',
      maintenance: {
        service_interval_km: 10000,
        service_interval_months: 12,
        typical_annual_maintenance_inr: '₹8,000 – ₹12,000',
        maintenance_complexity: 'Low',
        parts_availability: 'Excellent',
        routine_checklist: ['Engine oil replacement', 'Brake pad inspection'],
        evidence_state: 'SUPPORTED' as const,
      },
      fuel: {
        claimed_mileage_kmpl: 15.1,
        real_world_city_kmpl: 11.2,
        real_world_highway_kmpl: 14.5,
        fuel_type: 'Diesel',
      },
      tco_1_year: null as any,
      tco_3_year: null as any,
      tco_5_year: null as any,
      risk_signals: [
        {
          category: 'Fuel Cost Risk',
          severity: 'LOW' as const,
          title: 'Manageable Fuel Running Cost',
          description: 'Favorable power-to-weight ratio and efficient fuel delivery.',
          mitigation_advice: 'Maintain correct tyre pressure.',
          evidence_state: 'SUPPORTED',
        },
      ],
      disclaimer: 'Empirical projection',
    };

    render(
      <OwnershipSection
        ownership={null}
        ownershipIntelligence={mockInnovaOwnershipIntelligence as any}
      />
    );

    expect(screen.getByText('Real-World Ownership & Lifecycle Economics')).toBeDefined();
    expect(screen.getByText('Manageable Fuel Running Cost')).toBeDefined();
    expect(screen.getByText(/Favorable power-to-weight ratio/)).toBeDefined();
    expect(screen.getByText('10,000 km')).toBeDefined();
  });

  it('renders DealAnalyzerSection cleanly when dealAnalysis is null and fairMarketValue is absent', () => {
    const onEvaluateMock = vi.fn();
    render(
      <DealAnalyzerSection
        dealAnalysis={null}
        fairMarketValue={null}
        onEvaluateDeal={onEvaluateMock}
      />
    );

    expect(screen.getByText('Commercial Deal Analyzer')).toBeDefined();
    expect(screen.getByText('Seller Asking Price (₹)')).toBeDefined();
    expect(screen.getByRole('button', { name: /Evaluate Deal/i })).toBeDefined();
  });
});
