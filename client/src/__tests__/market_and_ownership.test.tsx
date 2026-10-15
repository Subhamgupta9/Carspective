import { describe, it, expect, vi } from 'vitest';
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { MarketPositionSection } from '../features/vehicle/workspace/MarketPositionSection';
import { OwnershipSection } from '../features/vehicle/workspace/OwnershipSection';
import { marketApi } from '../api/marketApi';
import { ownershipApi } from '../api/ownershipApi';
import * as clientModule from '../api/client';
import {
  VehicleMarketProfile,
  VehicleOwnershipIntelligence,
  OwnershipProfile,
} from '../types';

describe('Phase 14 — Market Intelligence & Real-World Ownership Components', () => {
  const mockMarketProfile: VehicleMarketProfile = {
    canonical_vehicle_id: 'maruti-suzuki::swift',
    model_slug: 'swift',
    market_position: {
      secondary_market_tier: 'TIER_1_DEEP',
      historical_listing_count: 3240,
      market_share_in_segment_percent: 18.5,
      supply_level: 'EXTENSIVE',
      liquidity_rating: 'VERY_HIGH',
      estimated_days_to_sell_band: '15 – 30 Days',
      demand_proxy: 'HIGH_DEMAND',
      active_listings_proxy_count: 3240,
      median_historical_asking_price_inr: 585000,
      p25_asking_price_inr: 450000,
      p75_asking_price_inr: 690000,
      resale_retention_index: 78,
      evidence_notes: 'High empirical sample depth across major metro markets',
    },
    depreciation: {
      curve_points: [
        {
          age_years: 1,
          mean_asking_price_inr: 680000,
          median_asking_price_inr: 675000,
          p25_asking_price_inr: 630000,
          p75_asking_price_inr: 720000,
          sample_size: 420,
          retention_percent_of_year_1: 100,
          is_statistically_robust: true,
        },
        {
          age_years: 3,
          mean_asking_price_inr: 540000,
          median_asking_price_inr: 535000,
          p25_asking_price_inr: 490000,
          p75_asking_price_inr: 580000,
          sample_size: 610,
          retention_percent_of_year_1: 79,
          is_statistically_robust: true,
        },
        {
          age_years: 5,
          mean_asking_price_inr: 430000,
          median_asking_price_inr: 425000,
          p25_asking_price_inr: 390000,
          p75_asking_price_inr: 470000,
          sample_size: 512,
          retention_percent_of_year_1: 63,
          is_statistically_robust: true,
        },
      ],
      typical_annual_depreciation_pct: 8.2,
      three_year_retained_value_pct: 79,
      five_year_retained_value_pct: 63,
      data_sufficiency_status: 'ROBUST',
      caveat_note: 'Asking price trend based on historical secondary listings.',
    },
    segment_benchmark: {
      segment_name: 'Compact Hatchback',
      segment_median_asking_price_inr: 510000,
      segment_retention_index_median: 72,
      vehicle_vs_segment_price_ratio: 1.05,
      vehicle_price_position_label: 'PREMIUM_IN_SEGMENT',
      top_competing_models: ['hyundai-i20', 'tata-altroz', 'maruti-baleno'],
    },
    evidence_disclosure: 'Empirical aggregation of 57,480 Indian used-car listings.',
    provenance_notice: 'Secondary market statistics reflect seller asking-price baselines.',
  };

  const mockOwnershipProfile: OwnershipProfile = {
    service_interval_km: 10000,
    service_interval_months: 12,
    typical_annual_maintenance_inr: '₹5,500 – ₹7,500',
    maintenance_complexity: 'Low',
    parts_availability: 'Extensive OEM Network',
    real_world_city_mileage_kmpl: 14.5,
    real_world_highway_mileage_kmpl: 19.8,
    ownership_strengths: ['Low cost routine maintenance', 'Widespread service support'],
    ownership_concerns: ['Thin body panels prone to minor dents'],
    evidence_state: 'SUPPORTED',
  };

  const mockOwnershipIntelligence: VehicleOwnershipIntelligence = {
    canonical_vehicle_id: 'maruti-suzuki::swift',
    model_slug: 'swift',
    maintenance: {
      typical_annual_maintenance_inr: 6500,
      service_interval_km: 10000,
      service_interval_months: 12,
      maintenance_complexity: 'Low',
      diy_friendliness: 'Moderate',
      routine_schedule: [
        {
          interval_km: 10000,
          interval_months: 12,
          milestone_name: '10K Minor Service',
          typical_tasks: ['Engine oil change', 'Oil filter replacement'],
          estimated_cost_inr: 3200,
          evidence_source: 'OEM Schedule',
        },
      ],
      major_milestones: [],
      parts_availability_index: 'Extensive',
      independent_garage_familiarity: 'Universal across India',
    },
    fuel: {
      arai_claimed_kmpl: 22.38,
      real_world_city_kmpl: 14.5,
      real_world_highway_kmpl: 19.8,
      real_world_combined_kmpl: 16.5,
      fuel_type: 'Petrol',
      transmission_type: 'Manual',
      annual_fuel_cost_10k_km_inr: 58600,
      annual_fuel_cost_15k_km_inr: 87900,
      cost_per_km_inr: 5.86,
    },
    tco_1_year: {
      horizon_years: 1,
      total_cost_inr: 125000,
      cost_per_km_inr: 10.42,
      depreciation_cost_inr: 60000,
      fuel_cost_inr: 45000,
      maintenance_cost_inr: 6500,
      insurance_cost_inr: 11000,
      statutory_charges_inr: 2500,
      components: [
        {
          component_name: 'Depreciation',
          amount_inr: 60000,
          percentage_of_total: 48,
          status: 'MODEL_ESTIMATED',
          basis_note: 'Empirical depreciation curve',
        },
        {
          component_name: 'Fuel Expense',
          amount_inr: 45000,
          percentage_of_total: 36,
          status: 'EVIDENCE_BACKED',
          basis_note: 'Real-world fuel economy baseline',
        },
      ],
      yearly_progression: [],
    },
    tco_3_year: {
      horizon_years: 3,
      total_cost_inr: 310000,
      cost_per_km_inr: 8.61,
      depreciation_cost_inr: 140000,
      fuel_cost_inr: 135000,
      maintenance_cost_inr: 21000,
      insurance_cost_inr: 28000,
      statutory_charges_inr: 3000,
      components: [],
      yearly_progression: [],
    },
    tco_5_year: {
      horizon_years: 5,
      total_cost_inr: 485000,
      cost_per_km_inr: 8.08,
      depreciation_cost_inr: 195000,
      fuel_cost_inr: 225000,
      maintenance_cost_inr: 38000,
      insurance_cost_inr: 42000,
      statutory_charges_inr: 5000,
      components: [
        {
          component_name: 'Depreciation',
          amount_inr: 195000,
          percentage_of_total: 40,
          status: 'MODEL_ESTIMATED',
          basis_note: 'Secondary asking curve trajectory',
        },
        {
          component_name: 'Fuel Expense',
          amount_inr: 225000,
          percentage_of_total: 46,
          status: 'EVIDENCE_BACKED',
          basis_note: 'Combined mileage at standard tariff',
        },
        {
          component_name: 'Routine Maintenance',
          amount_inr: 38000,
          percentage_of_total: 8,
          status: 'EVIDENCE_BACKED',
          basis_note: 'OEM scheduled maintenance intervals',
        },
      ],
      yearly_progression: [],
    },
    risk_signals: [
      {
        risk_id: 'risk_clutch',
        title: 'Premature Clutch Wear on City Commuters',
        severity: 'MODERATE',
        component_affected: 'Clutch Assembly',
        typical_occurrence_km: 55000,
        estimated_repair_cost_inr: 8500,
        preventative_measure: 'Inspect bite point and pedal firmness during pre-purchase check',
        evidence_source: 'Authorized Workshop Advisory',
      },
    ],
    disclaimer: 'TCO combines empirical wear rates with standardized fuel baselines.',
  };

  it('renders MarketPositionSection with empirical liquidity, supply, and depreciation', () => {
    render(
      <MarketPositionSection
        brand="Maruti Suzuki"
        model="Swift"
        coverageTier="TIER_1_DEEP"
        marketProfile={mockMarketProfile}
      />
    );

    // Verify Title & Badges
    expect(screen.getByText(/Secondary Market Intelligence & Resale Position/i)).toBeInTheDocument();
    expect(screen.getByText(/VERY HIGH Liquidity/i)).toBeInTheDocument();
    expect(screen.getByText(/EXTENSIVE Supply/i)).toBeInTheDocument();

    // Verify Metrics
    expect(screen.getByText(/15 – 30 Days/i)).toBeInTheDocument();
    expect(screen.getByText(/78\/100 Index/i)).toBeInTheDocument();
    expect(screen.getByText(/3,240 Listings/i)).toBeInTheDocument();
    expect(screen.getByText(/₹5.85 Lakh/i)).toBeInTheDocument();

    // Verify Depreciation Curve
    expect(screen.getByText(/Empirical Asking-Price Depreciation Trajectory/i)).toBeInTheDocument();
    expect(screen.getByText(/Year 1/i)).toBeInTheDocument();
    expect(screen.getByText(/Year 3/i)).toBeInTheDocument();

    // Verify Provenance Notice
    expect(screen.getByText(/Market Intelligence Provenance:/i)).toBeInTheDocument();
  });

  it('renders OwnershipSection with Fuel Calculator, TCO Simulator, and Risk Signals', () => {
    render(
      <OwnershipSection
        ownership={mockOwnershipProfile}
        ownershipIntelligence={mockOwnershipIntelligence}
      />
    );

    // Verify Section Header
    expect(screen.getByText(/Real-World Ownership & Lifecycle Economics/i)).toBeInTheDocument();

    // Verify Service Cadence & Maintenance
    expect(screen.getAllByText(/10,000 km/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/₹5,500 – ₹7,500/i)).toBeInTheDocument();

    // Verify Fuel Cost Calculator
    expect(screen.getByText(/Interactive Fuel Cost Calculator/i)).toBeInTheDocument();
    expect(screen.getByText(/1,000 km/i)).toBeInTheDocument();

    // Verify TCO Projection
    expect(screen.getByText(/Total Cost of Ownership \(TCO\) Projection/i)).toBeInTheDocument();
    expect(screen.getByText(/₹4,85,000/i)).toBeInTheDocument();
    expect(screen.getByText(/₹8.08 \/ km/i)).toBeInTheDocument();

    // Verify Risk Signals
    expect(screen.getByText(/Critical Ownership Risk Signals/i)).toBeInTheDocument();
    expect(screen.getByText(/Premature Clutch Wear on City Commuters/i)).toBeInTheDocument();
    expect(screen.getByText(/₹8,500/i)).toBeInTheDocument();
  });

  it('interacts with Fuel Cost Calculator sliders and updates monthly cost', () => {
    render(
      <OwnershipSection
        ownership={mockOwnershipProfile}
        ownershipIntelligence={mockOwnershipIntelligence}
      />
    );

    // Find monthly km slider and change value
    const sliders = screen.getAllByRole('slider');
    expect(sliders.length).toBeGreaterThanOrEqual(2);

    const kmSlider = sliders[0];
    fireEvent.change(kmSlider, { target: { value: '2000' } });

    // 2000 km driving should now be displayed
    expect(screen.getByText(/2,000 km/i)).toBeInTheDocument();
  });

  it('switches TCO horizons between 1-Year and 5-Year', () => {
    render(
      <OwnershipSection
        ownership={mockOwnershipProfile}
        ownershipIntelligence={mockOwnershipIntelligence}
      />
    );

    // Click 1-Year horizon tab
    const oneYearTab = screen.getByText('1-Year');
    fireEvent.click(oneYearTab);

    // Should display 1-year total: ₹1,25,000
    expect(screen.getByText(/₹1,25,000/i)).toBeInTheDocument();
    expect(screen.getByText(/₹10.42 \/ km/i)).toBeInTheDocument();
  });

  it('marketApi and ownershipApi call correct backend endpoints', async () => {
    const requestSpy = vi.spyOn(clientModule, 'request').mockResolvedValue({ status: 'ok' } as any);

    await marketApi.getMarketProfile('honda::city');
    expect(requestSpy).toHaveBeenCalledWith('/api/v1/market/honda%3A%3Acity');

    await marketApi.getDepreciationTrends('honda::city');
    expect(requestSpy).toHaveBeenCalledWith('/api/v1/market/honda%3A%3Acity/trends');

    await ownershipApi.getOwnershipIntelligence('honda::city');
    expect(requestSpy).toHaveBeenCalledWith('/api/v1/ownership/honda%3A%3Acity');

    await ownershipApi.calculateFuelCost({ mileage_kmpl: 15, monthly_km: 1000 });
    expect(requestSpy).toHaveBeenCalledWith(
      '/api/v1/ownership/cost',
      expect.objectContaining({ method: 'POST' })
    );

    requestSpy.mockRestore();
  });
});
