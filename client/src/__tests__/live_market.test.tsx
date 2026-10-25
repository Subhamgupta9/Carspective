import { describe, it, expect, vi } from 'vitest';
import React from 'react';
import { render, screen } from '@testing-library/react';
import { LiveMarketEvidenceSection } from '../features/vehicle/workspace/LiveMarketEvidenceSection';
import { marketApi } from '../api/marketApi';
import * as clientModule from '../api/client';
import { CurrentMarketIntelligenceResponse } from '../types';

describe('Phase 17 — Live Market Intelligence & Evidence Components', () => {
  const mockCurrentMarket: CurrentMarketIntelligenceResponse = {
    canonical_vehicle_id: 'maruti-suzuki::swift::gen-3-2018::2021::zxi::1-2-k12m-5mt',
    observation_period: '2026-Q3 (Current Market Observations)',
    supply: {
      canonical_vehicle_id: 'maruti-suzuki::swift::gen-3-2018::2021::zxi::1-2-k12m-5mt',
      total_observations: 12,
      active_listings_count: 10,
      supply_tier: 'HIGH_SUPPLY',
      regional_distribution: { 'Delhi NCR': 4, 'Mumbai': 3, 'Bengaluru': 3 },
      seller_distribution: { 'INDIVIDUAL': 5, 'CERTIFIED_DEALER': 4, 'INDEPENDENT_DEALER': 1 },
      freshness_distribution: { 'CURRENT': 9, 'AGING': 1 },
    },
    price_distribution: {
      canonical_vehicle_id: 'maruti-suzuki::swift::gen-3-2018::2021::zxi::1-2-k12m-5mt',
      sample_size: 10,
      min_price: 580000,
      p10_price: 610000,
      p25_price: 640000,
      median_price: 675000,
      p75_price: 710000,
      p90_price: 740000,
      max_price: 760000,
      iqr: 70000,
      std_dev: 48000,
      mean_price: 672000,
    },
    regional_breakdown: [
      {
        region: 'Delhi NCR',
        observation_count: 4,
        share_percentage: 40.0,
        median_asking_price: 670000,
      },
      {
        region: 'Mumbai',
        observation_count: 3,
        share_percentage: 30.0,
        median_asking_price: 690000,
      },
      {
        region: 'Bengaluru',
        observation_count: 3,
        share_percentage: 30.0,
        median_asking_price: 680000,
      },
    ],
    comparison_with_historical: {
      canonical_vehicle_id: 'maruti-suzuki::swift::gen-3-2018::2021::zxi::1-2-k12m-5mt',
      historical_sample_size: 3240,
      historical_median_asking_price: 585000,
      current_sample_size: 10,
      current_median_asking_price: 675000,
      price_shift_percentage: 15.38,
      price_trend_direction: 'INCREASING',
      commentary: 'Current 2026-Q3 median asking price is 15.4% above historical 2018–2024 baseline.',
    },
    evidence: {
      sources_contributed: ['src-current-market-aggregator-2026', 'src-current-certified-dealer-network-2026'],
      total_observations: 12,
      usable_observations: 10,
      duplicate_count: 1,
      outlier_count: 1,
      geographic_coverage: ['Bengaluru', 'Delhi NCR', 'Mumbai'],
      collection_window: '2026-07-01 to 2026-10-08',
      freshness_distribution: { 'CURRENT': 9, 'AGING': 1 },
      evidence_state: 'EMPIRICAL',
      limitations: [
        'Observations reflect active seller asking prices, not realized sale prices.',
        'Geographic coverage is limited to participating metro clusters.',
      ],
    },
    limitations: [
      'Observations reflect active seller asking prices, not realized sale prices.',
    ],
  };

  it('renders LiveMarketEvidenceSection with live observations and epistemic integrity notice', () => {
    render(
      <LiveMarketEvidenceSection
        currentMarket={mockCurrentMarket}
        canonicalVehicleId="maruti-suzuki::swift::gen-3-2018::2021::zxi::1-2-k12m-5mt"
      />
    );

    // Title and observation period
    expect(screen.getByText(/Live Market Evidence & 2026 Observations/i)).toBeInTheDocument();
    expect(screen.getByText(/2026-Q3 \(Current Market Observations\)/i)).toBeInTheDocument();

    // Epistemic honesty statement
    expect(screen.getByText(/Epistemic Data Integrity Notice:/i)).toBeInTheDocument();
    expect(screen.getByText(/They do NOT represent completed sales, realized resale values/i)).toBeInTheDocument();

    // Asking price median and IQR
    expect(screen.getByText(/Current Asking Price \(Median\)/i)).toBeInTheDocument();
    expect(screen.getAllByText(/₹6.75L/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/IQR: ₹6.40L – ₹7.10L/i)).toBeInTheDocument();

    // Supply depth
    expect(screen.getByText(/Current Supply Depth/i)).toBeInTheDocument();
    expect(screen.getByText('Active')).toBeInTheDocument();
    expect(screen.getByText(/Usable Observations/i)).toBeInTheDocument();

    // Regional clusters
    expect(screen.getByText('Delhi NCR')).toBeInTheDocument();
    expect(screen.getByText('Mumbai')).toBeInTheDocument();
    expect(screen.getByText('Bengaluru')).toBeInTheDocument();
  });

  it('renders fallback state cleanly when currentMarket is null', () => {
    render(
      <LiveMarketEvidenceSection
        currentMarket={null}
        canonicalVehicleId="toyota::corolla::2015"
      />
    );

    expect(screen.getByText(/No Feeds Available/i)).toBeInTheDocument();
    expect(screen.getByText(/Pricing guidance relies strictly on the historical 2018–2024 empirical baseline/i)).toBeInTheDocument();
  });

  it('renders regional clusters cleanly when share_percentage and region use backend database aliases', () => {
    const backendData: CurrentMarketIntelligenceResponse = {
      ...mockCurrentMarket,
      regional_breakdown: [
        {
          region_name: 'Bengaluru',
          median_asking_price_inr: 655000,
          observation_count: 2,
        } as any,
        {
          region_name: 'Delhi NCR',
          median_asking_price_inr: 637500,
          observation_count: 4,
        } as any,
      ],
      comparison_with_historical: {
        ...mockCurrentMarket.comparison_with_historical!,
        price_shift_percentage: undefined as any,
      },
    };

    render(
      <LiveMarketEvidenceSection
        currentMarket={backendData}
        canonicalVehicleId="maruti-suzuki::swift"
      />
    );

    expect(screen.getByText('Bengaluru')).toBeInTheDocument();
    expect(screen.getByText('Delhi NCR')).toBeInTheDocument();
    expect(screen.getByText('₹6.55L')).toBeInTheDocument();
    expect(screen.getByText('₹6.38L')).toBeInTheDocument();
  });
});
