import { describe, it, expect } from 'vitest';
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { VehicleSpecs } from '../features/vehicle/VehicleSpecs';
import { VehicleKnowledgeProfile } from '../types';

describe('Phase 11 — Vehicle Knowledge & Intelligence Rendering', () => {
  const mockKnowledgeProfile: VehicleKnowledgeProfile = {
    canonical_vehicle_id: 'maruti-suzuki::swift::gen-3-2018',
    make: 'Maruti Suzuki',
    model: 'Swift',
    generation_name: '3rd Generation',
    year: 2020,
    variant_name: 'VXi',
    body_type: 'Hatchback',
    segment: 'B-Segment Hatchback',
    coverage_tier: 'TIER_1_DEEP',
    specifications: {
      displacement_cc: 1197,
      max_power_bhp: 89,
      max_torque_nm: 113,
      transmission: '5-Speed Manual',
      drivetrain: 'FWD',
      fuel_type: 'Petrol',
      arai_mileage_kmpl: 23.2,
      evidence_state: 'VERIFIED',
    },
    dimensions: {
      length_mm: 3845,
      width_mm: 1735,
      height_mm: 1530,
      wheelbase_mm: 2450,
      ground_clearance_mm: 163,
      boot_capacity_l: 268,
      evidence_state: 'VERIFIED',
    },
    safety: {
      organization: 'Global NCAP',
      test_year: 2018,
      adult_stars: 2,
      child_stars: 2,
      bodyshell_integrity: 'UNSTABLE',
      standard_safety_equipment: 'Dual Front Airbags, ABS with EBD, ISOFIX mounts',
      evidence_state: 'VERIFIED',
    },
    features: [
      {
        feature_key: 'dual_front_airbags',
        feature_name: 'Dual Front Airbags',
        category: 'SAFETY',
        availability: 'STANDARD',
        evidence_state: 'VERIFIED',
      },
      {
        feature_key: 'touchscreen_smartplay',
        feature_name: 'Touchscreen Smartplay',
        category: 'INFOTAINMENT',
        availability: 'OPTIONAL',
        evidence_state: 'SUPPORTED',
      },
    ],
    ownership: {
      service_interval_km: 10000,
      service_interval_months: 12,
      typical_annual_maintenance_inr: '4,800',
      parts_availability: 'EXCELLENT',
      maintenance_complexity: 'LOW',
      real_world_city_mileage_kmpl: '14.5',
      real_world_highway_mileage_kmpl: '19.2',
      ownership_strengths: ['Low cost routine service'],
      ownership_concerns: ['Light build sheet metal'],
      evidence_state: 'SUPPORTED',
    },
    reliability_issues: [
      {
        issue_key: 'steering_column_rattle',
        category: 'STEERING_SUSPENSION',
        title: 'Steering Column Rattle Over Broken Pavement',
        description: 'Intermediate steering shaft wear causing low-frequency rattling.',
        severity: 'MODERATE',
        verification_status: 'CONFIRMED',
        evidence_state: 'SUPPORTED',
      },
    ],
    pros: [
      {
        is_pro: true,
        statement: 'Peppy and refined K12N DualJet engine',
        category: 'PERFORMANCE',
        source_type: 'JOURNALIST_CONSENSUS',
        evidence_state: 'SUPPORTED',
      },
    ],
    cons: [
      {
        is_pro: false,
        statement: '2-Star Global NCAP safety with unstable bodyshell',
        category: 'SAFETY',
        source_type: 'CRASH_TEST',
        evidence_state: 'VERIFIED',
      },
    ],
    reviews: {
      what_owners_say: 'Highly reliable daily commuter with stellar fuel economy.',
      what_experts_say: 'Agile chassis and responsive engine, compromised by structural safety.',
      carspective_analysis: 'The Swift remains an undisputed ownership value benchmark.',
      has_owner_evidence: true,
      has_expert_evidence: true,
      evidence_state: 'SUPPORTED',
    },
    freshness_summary: {
      last_verified: '2026-10-08',
      has_stale_data: false,
      evidence_coverage: {
        specifications: 'SUPPORTED',
        safety: 'VERIFIED',
        ownership: 'SUPPORTED',
      },
    },
  };

  it('renders verified powertrain, dimensions, and crash safety stars accurately', () => {
    render(
      <VehicleSpecs
        vehicle={{ brand: 'Maruti Suzuki', model: 'Swift', year: 2020 }}
        knowledgeProfile={mockKnowledgeProfile}
      />
    );

    // Header and title
    expect(screen.getByText('Canonical Vehicle Intelligence')).toBeInTheDocument();
    expect(screen.getByText('TIER 1 DEEP')).toBeInTheDocument();

    // Powertrain specs
    expect(screen.getByText(/1,197 cc • 89 bhp • 113 Nm/)).toBeInTheDocument();
    expect(screen.getByText(/23.2 km\/l \(ARAI\)/)).toBeInTheDocument();

    // Dimensions
    expect(screen.getByText(/3845 × 1735 × 1530 mm • 268 L Boot/)).toBeInTheDocument();

    // Safety breakdown
    expect(screen.getByText(/Crash Safety Assessment — Global NCAP \(2018\)/)).toBeInTheDocument();
    expect(screen.getByText(/Bodyshell: UNSTABLE/)).toBeInTheDocument();
  });

  it('renders variant equipment matrix and allows tab filtering', () => {
    render(
      <VehicleSpecs
        vehicle={{ brand: 'Maruti Suzuki', model: 'Swift', year: 2020 }}
        knowledgeProfile={mockKnowledgeProfile}
      />
    );

    // Initial view shows both standard and optional
    expect(screen.getByText('Dual Front Airbags')).toBeInTheDocument();
    expect(screen.getByText('Touchscreen Smartplay')).toBeInTheDocument();

    // Filter to STANDARD only
    fireEvent.click(screen.getByRole('button', { name: 'STANDARD' }));
    expect(screen.getByText('Dual Front Airbags')).toBeInTheDocument();
    expect(screen.queryByText('Touchscreen Smartplay')).not.toBeInTheDocument();

    // Filter to OPTIONAL only
    fireEvent.click(screen.getByRole('button', { name: 'OPTIONAL' }));
    expect(screen.getByText('Touchscreen Smartplay')).toBeInTheDocument();
    expect(screen.queryByText('Dual Front Airbags')).not.toBeInTheDocument();
  });

  it('renders ownership, mechanical watchpoints, pros/cons, and review synthesis', () => {
    render(
      <VehicleSpecs
        vehicle={{ brand: 'Maruti Suzuki', model: 'Swift', year: 2020 }}
        knowledgeProfile={mockKnowledgeProfile}
      />
    );

    // Ownership
    expect(screen.getByText(/10,000 km \/ 12 mo/)).toBeInTheDocument();
    expect(screen.getByText(/₹4,800/)).toBeInTheDocument();

    // Watchpoints
    expect(screen.getByText(/Steering Column Rattle Over Broken Pavement/)).toBeInTheDocument();
    expect(screen.getByText('MODERATE')).toBeInTheDocument();

    // Pros & Cons
    expect(screen.getByText('Peppy and refined K12N DualJet engine')).toBeInTheDocument();
    expect(screen.getByText('2-Star Global NCAP safety with unstable bodyshell')).toBeInTheDocument();

    // Tripartite reviews
    expect(screen.getByText('Highly reliable daily commuter with stellar fuel economy.')).toBeInTheDocument();
    expect(screen.getByText('The Swift remains an undisputed ownership value benchmark.')).toBeInTheDocument();
  });

  it('handles unverified fallback without fabricating missing fields', () => {
    render(
      <VehicleSpecs
        vehicle={{ brand: 'CustomKit', model: 'Special', year: 2022 }}
        knowledgeProfile={null}
      />
    );

    expect(screen.getByText('No official crash rating published for this generation')).toBeInTheDocument();
    expect(screen.queryByText('Crash Safety Assessment')).not.toBeInTheDocument();
  });
});
