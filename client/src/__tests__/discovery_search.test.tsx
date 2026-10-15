import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AppProvider } from '../state/AppContext';
import { SearchBox } from '../components/common/SearchBox';
import { SearchPage } from '../pages/SearchPage';
import { vehicleApi } from '../api/vehicleApi';

describe('Phase 12 — Discovery Search Component Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders SearchBox with placeholder and input', () => {
    const handleSearch = vi.fn();
    render(
      <SearchBox onSearch={handleSearch} placeholder="Search by make, model, or year..." />
    );

    const input = screen.getByPlaceholderText(/search by make, model, or year/i);
    expect(input).toBeInTheDocument();
    expect(input).toHaveAttribute('role', 'combobox');
  });

  it('triggers SearchBox search on Enter and form submission', () => {
    const handleSearch = vi.fn();
    render(
      <SearchBox onSearch={handleSearch} />
    );

    const input = screen.getByRole('combobox');
    fireEvent.change(input, { target: { value: 'Creta 2022' } });
    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });

    expect(handleSearch).toHaveBeenCalledWith('Creta 2022');
  });

  it('renders SearchPage with search results and candidate cards', async () => {
    vi.spyOn(vehicleApi, 'searchVehicles').mockResolvedValue({
      query: 'Swift 2021',
      intent: {
        raw_query: 'Swift 2021',
        normalized_query: 'Swift 2021',
        manufacturer: { value: 'Maruti Suzuki', provenance: 'USER_EXPLICIT', confidence: 1.0 },
        model: { value: 'Swift', provenance: 'USER_EXPLICIT', confidence: 1.0 },
        model_year: { value: 2021, provenance: 'USER_EXPLICIT', confidence: 1.0 },
      },
      result_type: 'HIGH_CONFIDENCE_MATCH',
      total_count: 1,
      results: [
        {
          canonical_vehicle_id: 'maruti-suzuki::swift::gen-3-2018::2021::zxi::1-2-k12m-5mt',
          title: 'Maruti Suzuki Swift ZXi (2021)',
          manufacturer: 'Maruti Suzuki',
          model: 'Swift',
          generation: 'Gen 3 (2018–2024)',
          model_year: 2021,
          variant: 'ZXi',
          powertrain: 'Petrol · Manual',
          fuel_type: 'Petrol',
          transmission: 'Manual',
          body_type: 'Hatchback',
          seating_capacity: 5,
          coverage_tier: 'TIER_1_DEEP',
          evidence_state: 'VERIFIED',
          has_deep_knowledge: true,
          match_score: 95.0,
          match_reasons: [
            { factor: 'MODEL_EXACT', score_contribution: 30.0, description: 'Exact match for model: Swift' },
            { factor: 'YEAR_EXACT', score_contribution: 20.0, description: 'Matched model year: 2021' }
          ],
          available_actions: ['view', 'compare', 'value', 'deal', 'inspect']
        }
      ],
      suggestions: [],
      provenance: {
        query_normalized: 'Swift 2021',
        rules_applied: ['parsed_model', 'parsed_year'],
        taxonomy_version: 'Phase 2 Canonical Taxonomy',
        resolution_method: 'Deterministic Pattern Matching & Taxonomy Graph',
        evidence_sources_checked: 12
      }
    });

    render(
      <AppProvider>
        <SearchPage onNavigate={vi.fn()} />
      </AppProvider>
    );

    // Enter query in SearchPage
    const input = screen.getByRole('combobox');
    fireEvent.change(input, { target: { value: 'Swift 2021' } });
    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });

    await waitFor(() => {
      expect(screen.getByText('Maruti Suzuki Swift ZXi (2021)')).toBeInTheDocument();
      expect(screen.getByText('95% Match')).toBeInTheDocument();
      expect(screen.getByText(/Exact match for model: Swift/i)).toBeInTheDocument();
    });
  });

  it('renders Ambiguity Clarification card when model has multiple generations', async () => {
    vi.spyOn(vehicleApi, 'searchVehicles').mockResolvedValue({
      query: 'Swift',
      intent: {
        raw_query: 'Swift',
        normalized_query: 'Swift',
        manufacturer: { value: 'Maruti Suzuki', provenance: 'SYSTEM_RESOLVED', confidence: 1.0 },
        model: { value: 'Swift', provenance: 'USER_EXPLICIT', confidence: 1.0 },
      },
      result_type: 'AMBIGUOUS',
      total_count: 3,
      results: [],
      clarification: {
        clarification_type: 'MULTIPLE_GENERATIONS',
        prompt: 'I found 4 generations of the Swift. Which production generation or model year are you looking for?',
        options: [
          { generation: 'Gen 2 (2011–2018)', year_range: '2011–2018', suggested_query: 'Swift 2015' },
          { generation: 'Gen 3 (2018–2024)', year_range: '2018–2024', suggested_query: 'Swift 2021' }
        ]
      },
      suggestions: [],
      provenance: {
        query_normalized: 'Swift',
        rules_applied: ['parsed_model'],
        taxonomy_version: 'Phase 2 Canonical Taxonomy',
        resolution_method: 'Deterministic Pattern Matching & Taxonomy Graph',
        evidence_sources_checked: 12
      }
    });

    render(
      <AppProvider>
        <SearchPage onNavigate={vi.fn()} />
      </AppProvider>
    );

    const input = screen.getByRole('combobox');
    fireEvent.change(input, { target: { value: 'Swift' } });
    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });

    await waitFor(() => {
      expect(screen.getByText(/Ambiguity Clarification Required/i)).toBeInTheDocument();
      expect(screen.getByText('Gen 2 (2011–2018)')).toBeInTheDocument();
      expect(screen.getByText('Gen 3 (2018–2024)')).toBeInTheDocument();
    });
  });

  it('renders No Match fallback state with safe taxonomy suggestions', async () => {
    vi.spyOn(vehicleApi, 'searchVehicles').mockResolvedValue({
      query: 'Ferrari F8 Tributo',
      intent: {
        raw_query: 'Ferrari F8 Tributo',
        normalized_query: 'Ferrari F8 Tributo',
      },
      result_type: 'NO_MATCH',
      total_count: 0,
      results: [],
      suggestions: ['Maruti Suzuki Swift', 'Hyundai Creta', 'Tata Nexon'],
      provenance: {
        query_normalized: 'Ferrari F8 Tributo',
        rules_applied: [],
        taxonomy_version: 'Phase 2 Canonical Taxonomy',
        resolution_method: 'Deterministic Pattern Matching & Taxonomy Graph',
        evidence_sources_checked: 12
      }
    });

    render(
      <AppProvider>
        <SearchPage onNavigate={vi.fn()} />
      </AppProvider>
    );

    const input = screen.getByRole('combobox');
    fireEvent.change(input, { target: { value: 'Ferrari F8 Tributo' } });
    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });

    await waitFor(() => {
      expect(screen.getByText(/No Confident Canonical Match/i)).toBeInTheDocument();
      expect(screen.getByText(/Maruti Suzuki Swift/i)).toBeInTheDocument();
      expect(screen.getByText(/Hyundai Creta/i)).toBeInTheDocument();
    });
  });
});
