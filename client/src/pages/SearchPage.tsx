import React, { useState, useEffect } from 'react';
import { SearchBox } from '../components/common/SearchBox';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { EvidenceBadge } from '../components/common/EvidenceBadge';
import { useApp } from '../state/AppContext';
import { vehicleApi } from '../api/vehicleApi';
import {
  DiscoveryCandidate,
  DiscoverySearchResponse,
  SearchResultType,
} from '../types';
import {
  HelpCircle,
  CheckCircle,
  Sparkles,
  ArrowRight,
  Filter,
  DollarSign,
  ShieldCheck,
  AlertTriangle,
  Compass,
} from 'lucide-react';

export interface SearchPageProps {
  onNavigate: (path: string) => void;
}

const BODY_TYPES = ['All', 'SUV', 'Sedan', 'Hatchback', 'MPV'];
const FUEL_TYPES = ['All', 'Petrol', 'Diesel', 'CNG'];
const BUDGET_OPTIONS = [
  { label: 'Any Budget', max: undefined },
  { label: 'Under ₹5 Lakh', max: 500000 },
  { label: 'Under ₹10 Lakh', max: 1000000 },
  { label: 'Under ₹15 Lakh', max: 1500000 },
  { label: 'Under ₹25 Lakh', max: 2500000 },
];

export const SearchPage: React.FC<SearchPageProps> = ({ onNavigate }) => {
  const { setCurrentVehicle } = useApp();
  const [query, setQuery] = useState('');
  const [selectedBody, setSelectedBody] = useState('All');
  const [selectedFuel, setSelectedFuel] = useState('All');
  const [selectedBudget, setSelectedBudget] = useState<number | undefined>(undefined);
  const [searchResponse, setSearchResponse] = useState<DiscoverySearchResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const executeSearch = async (
    q: string,
    body: string = selectedBody,
    fuel: string = selectedFuel,
    budget: number | undefined = selectedBudget
  ) => {
    setIsLoading(true);
    try {
      const res = await vehicleApi.searchVehicles({
        q: q || undefined,
        body_type: body !== 'All' ? body : undefined,
        fuel: fuel !== 'All' ? fuel : undefined,
        budget_max: budget,
        limit: 20,
      });
      setSearchResponse(res);
    } catch {
      setSearchResponse(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    // Initial load: show popular discovery results
    executeSearch('', selectedBody, selectedFuel, selectedBudget);
  }, [selectedBody, selectedFuel, selectedBudget]);

  const handleSearchSubmit = (searchTerm: string) => {
    setQuery(searchTerm);
    executeSearch(searchTerm, selectedBody, selectedFuel, selectedBudget);
  };

  const handleSelectCandidate = (candidate: DiscoveryCandidate, targetAction: string = 'view') => {
    setCurrentVehicle({
      brand: candidate.manufacturer,
      model: candidate.model,
      year: candidate.model_year,
      canonical_id: candidate.canonical_vehicle_id,
      fuel_type: candidate.fuel_type || 'Petrol',
      transmission_type: candidate.transmission || 'Manual',
      asking_price: 850000,
      km_driven: 35000,
    });

    if (targetAction === 'view') {
      onNavigate(`/vehicle/${encodeURIComponent(candidate.canonical_vehicle_id)}`);
    } else if (targetAction === 'value') {
      onNavigate('/valuation');
    } else if (targetAction === 'deal') {
      onNavigate('/deal');
    } else if (targetAction === 'inspect') {
      onNavigate('/inspection');
    } else if (targetAction === 'assistant') {
      onNavigate('/assistant');
    } else if (targetAction === 'compare') {
      onNavigate(`/compare?vehicles=${encodeURIComponent(candidate.canonical_vehicle_id)}`);
    }
  };

  const getResultTypeBadge = (type: SearchResultType) => {
    switch (type) {
      case 'EXACT_MATCH':
        return <Badge variant="success" size="sm">Exact Match</Badge>;
      case 'HIGH_CONFIDENCE_MATCH':
        return <Badge variant="info" size="sm">High Confidence</Badge>;
      case 'AMBIGUOUS':
        return <Badge variant="warning" size="sm">Ambiguous Query</Badge>;
      case 'FILTERED_RESULTS':
        return <Badge variant="neutral" size="sm">Discovery Results</Badge>;
      case 'NO_MATCH':
        return <Badge variant="danger" size="sm">No Direct Match</Badge>;
      default:
        return null;
    }
  };

  return (
    <div className="container" style={{ padding: 'var(--space-8) 0', display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
      {/* Header */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: 'var(--space-2)' }}>
          <Compass size={24} color="var(--accent-blue)" />
          <h1 style={{ fontSize: 'var(--font-size-3xl)', margin: 0 }}>Intelligent Vehicle Discovery</h1>
        </div>
        <p style={{ fontSize: 'var(--font-size-base)', color: 'var(--text-muted)', margin: 0 }}>
          Natural intent understanding, deterministic canonical resolution, and explainable automotive matching.
        </p>
      </div>

      {/* Main Search Input */}
      <SearchBox
        onSelectVehicle={v => {
          if (v.canonical_id) {
            onNavigate(`/vehicle/${encodeURIComponent(v.canonical_id)}`);
          } else {
            handleSearchSubmit(`${v.brand} ${v.model} ${v.year || ''}`.trim());
          }
        }}
        placeholder="Search e.g. '2020 Swift VXi', 'Creta diesel automatic', 'SUV under 15 lakh'..."
        size="lg"
      />

      {/* Discovery Filters Bar */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: 'var(--space-4)',
          backgroundColor: 'var(--bg-secondary)',
          padding: 'var(--space-4)',
          borderRadius: 'var(--radius-lg)',
          alignItems: 'center',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', color: 'var(--text-secondary)' }}>
          <Filter size={16} />
          <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 'var(--font-weight-semibold)', textTransform: 'uppercase' }}>
            Filters:
          </span>
        </div>

        {/* Body Type Filter */}
        <div style={{ display: 'flex', gap: 'var(--space-1)', alignItems: 'center' }}>
          {BODY_TYPES.map(b => (
            <button
              key={b}
              onClick={() => setSelectedBody(b)}
              style={{
                padding: 'var(--space-1) var(--space-3)',
                borderRadius: 'var(--radius-full)',
                fontSize: 'var(--font-size-xs)',
                fontWeight: selectedBody === b ? 'var(--font-weight-semibold)' : 'normal',
                backgroundColor: selectedBody === b ? 'var(--accent-blue)' : 'var(--bg-primary)',
                color: selectedBody === b ? '#ffffff' : 'var(--text-secondary)',
                border: selectedBody === b ? '1px solid var(--accent-blue)' : '1px solid var(--border-subtle)',
                cursor: 'pointer',
              }}
            >
              {b}
            </button>
          ))}
        </div>

        {/* Fuel Type Filter */}
        <div style={{ display: 'flex', gap: 'var(--space-1)', alignItems: 'center' }}>
          {FUEL_TYPES.map(f => (
            <button
              key={f}
              onClick={() => setSelectedFuel(f)}
              style={{
                padding: 'var(--space-1) var(--space-3)',
                borderRadius: 'var(--radius-full)',
                fontSize: 'var(--font-size-xs)',
                fontWeight: selectedFuel === f ? 'var(--font-weight-semibold)' : 'normal',
                backgroundColor: selectedFuel === f ? 'var(--accent-blue)' : 'var(--bg-primary)',
                color: selectedFuel === f ? '#ffffff' : 'var(--text-secondary)',
                border: selectedFuel === f ? '1px solid var(--accent-blue)' : '1px solid var(--border-subtle)',
                cursor: 'pointer',
              }}
            >
              {f}
            </button>
          ))}
        </div>

        {/* Budget Filter */}
        <div style={{ display: 'flex', gap: 'var(--space-1)', alignItems: 'center' }}>
          {BUDGET_OPTIONS.map(b => (
            <button
              key={b.label}
              onClick={() => setSelectedBudget(b.max)}
              style={{
                padding: 'var(--space-1) var(--space-3)',
                borderRadius: 'var(--radius-full)',
                fontSize: 'var(--font-size-xs)',
                fontWeight: selectedBudget === b.max ? 'var(--font-weight-semibold)' : 'normal',
                backgroundColor: selectedBudget === b.max ? 'var(--accent-blue)' : 'var(--bg-primary)',
                color: selectedBudget === b.max ? '#ffffff' : 'var(--text-secondary)',
                border: selectedBudget === b.max ? '1px solid var(--accent-blue)' : '1px solid var(--border-subtle)',
                cursor: 'pointer',
              }}
            >
              {b.label}
            </button>
          ))}
        </div>
      </div>

      {/* Ambiguity Clarification Banner */}
      {searchResponse?.clarification && (
        <div
          style={{
            backgroundColor: 'var(--status-attention-bg)',
            border: '1px solid var(--status-attention-border)',
            padding: 'var(--space-4)',
            borderRadius: 'var(--radius-lg)',
            display: 'flex',
            flexDirection: 'column',
            gap: 'var(--space-3)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', color: 'var(--status-attention)' }}>
            <HelpCircle size={20} />
            <h4 style={{ margin: 0, fontSize: 'var(--font-size-base)', fontWeight: 'var(--font-weight-bold)' }}>
              Ambiguity Clarification Required
            </h4>
          </div>
          <p style={{ margin: 0, fontSize: 'var(--font-size-sm)', color: 'var(--text-primary)' }}>
            {searchResponse.clarification.prompt}
          </p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
            {searchResponse.clarification.options.map(opt => (
              <button
                key={opt.generation}
                onClick={() => handleSearchSubmit(opt.suggested_query)}
                style={{
                  padding: 'var(--space-2) var(--space-3)',
                  backgroundColor: 'var(--bg-primary)',
                  border: '1px solid var(--border-medium)',
                  borderRadius: 'var(--radius-md)',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 'var(--space-2)',
                  fontSize: 'var(--font-size-sm)',
                }}
              >
                <strong>{opt.generation}</strong>
                <span style={{ color: 'var(--text-muted)' }}>({opt.year_range})</span>
                <ArrowRight size={14} color="var(--accent-blue)" />
              </button>
            ))}
          </div>
        </div>
      )}

      {/* No Match Guardrail & Suggestions */}
      {searchResponse?.result_type === 'NO_MATCH' && (
        <Card style={{ padding: 'var(--space-6)', textAlign: 'center' }}>
          <AlertTriangle size={32} color="var(--status-attention)" style={{ margin: '0 auto var(--space-2)' }} />
          <h3 style={{ margin: '0 0 var(--space-2)' }}>No Confident Canonical Match</h3>
          <p style={{ color: 'var(--text-muted)', fontSize: 'var(--font-size-sm)', maxWidth: '500px', margin: '0 auto var(--space-4)' }}>
            We could not identify this vehicle in the canonical taxonomy without guessing silently.
          </p>
          {searchResponse.suggestions && searchResponse.suggestions.length > 0 && (
            <div>
              <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)', marginBottom: 'var(--space-2)' }}>
                Did you mean one of these supported models?
              </div>
              <div style={{ display: 'flex', justifyContent: 'center', gap: 'var(--space-2)', flexWrap: 'wrap' }}>
                {searchResponse.suggestions.map(s => (
                  <button
                    key={s}
                    onClick={() => handleSearchSubmit(s)}
                    style={{
                      padding: 'var(--space-1) var(--space-3)',
                      backgroundColor: 'var(--bg-secondary)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: 'var(--radius-full)',
                      cursor: 'pointer',
                      fontSize: 'var(--font-size-xs)',
                    }}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}
        </Card>
      )}

      {/* Results Header */}
      {searchResponse && searchResponse.results.length > 0 && (
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
            <h2 style={{ fontSize: 'var(--font-size-xl)', margin: 0 }}>
              Search Results ({searchResponse.total_count})
            </h2>
            {getResultTypeBadge(searchResponse.result_type)}
          </div>
          {searchResponse.intent.raw_query && (
            <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
              Normalized: <code>{searchResponse.provenance.query_normalized}</code>
            </div>
          )}
        </div>
      )}

      {/* Candidates List */}
      {isLoading ? (
        <div style={{ padding: 'var(--space-8)', textAlign: 'center', color: 'var(--text-muted)' }}>
          Resolving canonical vehicle taxonomy...
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
          {searchResponse?.results.map(c => (
            <Card
              key={c.canonical_vehicle_id}
              style={{
                padding: 'var(--space-5)',
                display: 'flex',
                flexDirection: 'column',
                gap: 'var(--space-4)',
                transition: 'border-color var(--transition-fast)',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: 'var(--space-1)' }}>
                    <Badge variant="neutral" size="sm">{c.manufacturer}</Badge>
                    <Badge variant="info" size="sm">{c.generation}</Badge>
                    <EvidenceBadge state={c.evidence_state} size="sm" />
                    {c.has_deep_knowledge && (
                      <Badge variant="success" size="sm">Deep Knowledge</Badge>
                    )}
                  </div>
                  <h3 style={{ fontSize: 'var(--font-size-lg)', margin: 'var(--space-1) 0', fontWeight: 'var(--font-weight-bold)' }}>
                    {c.title}
                  </h3>
                  <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
                    {c.variant || 'Standard'} • {c.powertrain || 'Standard'} • {c.body_type} • {c.seating_capacity} Seater
                  </div>
                </div>

                {/* Match Score Badge */}
                <div style={{ textAlign: 'right' }}>
                  <div
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: 'var(--space-1)',
                      padding: 'var(--space-1) var(--space-3)',
                      borderRadius: 'var(--radius-full)',
                      backgroundColor: c.match_score >= 80 ? 'var(--status-success-bg)' : 'var(--bg-secondary)',
                      color: c.match_score >= 80 ? 'var(--status-success)' : 'var(--text-primary)',
                      fontWeight: 'var(--font-weight-bold)',
                      fontSize: 'var(--font-size-sm)',
                    }}
                  >
                    <Sparkles size={14} />
                    <span>{Math.round(c.match_score)}% Match</span>
                  </div>
                </div>
              </div>

              {/* Explainable Match Reasons */}
              {c.match_reasons.length > 0 && (
                <div
                  style={{
                    backgroundColor: 'var(--bg-secondary)',
                    padding: 'var(--space-2) var(--space-3)',
                    borderRadius: 'var(--radius-md)',
                    display: 'flex',
                    flexWrap: 'wrap',
                    gap: 'var(--space-3)',
                  }}
                >
                  {c.match_reasons.map((r, rIdx) => (
                    <div
                      key={rIdx}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 'var(--space-1)',
                        fontSize: 'var(--font-size-xs)',
                        color: 'var(--text-secondary)',
                      }}
                    >
                      <CheckCircle size={12} color="var(--accent-blue)" />
                      <span>{r.description}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Quick Action Navigation Buttons */}
              <div
                style={{
                  display: 'flex',
                  flexWrap: 'wrap',
                  gap: 'var(--space-2)',
                  borderTop: '1px solid var(--border-subtle)',
                  paddingTop: 'var(--space-3)',
                  justifyContent: 'flex-end',
                }}
              >
                <button
                  onClick={() => handleSelectCandidate(c, 'view')}
                  style={{
                    padding: 'var(--space-2) var(--space-3)',
                    backgroundColor: 'var(--accent-blue)',
                    color: '#ffffff',
                    border: 'none',
                    borderRadius: 'var(--radius-md)',
                    cursor: 'pointer',
                    fontSize: 'var(--font-size-xs)',
                    fontWeight: 'var(--font-weight-semibold)',
                  }}
                >
                  View Vehicle
                </button>
                <button
                  onClick={() => handleSelectCandidate(c, 'value')}
                  style={{
                    padding: 'var(--space-2) var(--space-3)',
                    backgroundColor: 'var(--bg-primary)',
                    color: 'var(--text-primary)',
                    border: '1px solid var(--border-medium)',
                    borderRadius: 'var(--radius-md)',
                    cursor: 'pointer',
                    fontSize: 'var(--font-size-xs)',
                  }}
                >
                  Value This Car
                </button>
                <button
                  onClick={() => handleSelectCandidate(c, 'deal')}
                  style={{
                    padding: 'var(--space-2) var(--space-3)',
                    backgroundColor: 'var(--bg-primary)',
                    color: 'var(--text-primary)',
                    border: '1px solid var(--border-medium)',
                    borderRadius: 'var(--radius-md)',
                    cursor: 'pointer',
                    fontSize: 'var(--font-size-xs)',
                  }}
                >
                  Analyze Deal
                </button>
                <button
                  onClick={() => handleSelectCandidate(c, 'compare')}
                  style={{
                    padding: 'var(--space-2) var(--space-3)',
                    backgroundColor: 'var(--bg-primary)',
                    color: 'var(--text-primary)',
                    border: '1px solid var(--border-medium)',
                    borderRadius: 'var(--radius-md)',
                    cursor: 'pointer',
                    fontSize: 'var(--font-size-xs)',
                  }}
                >
                  Compare
                </button>
                <button
                  onClick={() => handleSelectCandidate(c, 'inspect')}
                  style={{
                    padding: 'var(--space-2) var(--space-3)',
                    backgroundColor: 'var(--bg-primary)',
                    color: 'var(--text-primary)',
                    border: '1px solid var(--border-medium)',
                    borderRadius: 'var(--radius-md)',
                    cursor: 'pointer',
                    fontSize: 'var(--font-size-xs)',
                  }}
                >
                  Inspect
                </button>
                <button
                  onClick={() => handleSelectCandidate(c, 'assistant')}
                  style={{
                    padding: 'var(--space-2) var(--space-3)',
                    backgroundColor: 'var(--bg-primary)',
                    color: 'var(--text-primary)',
                    border: '1px solid var(--border-medium)',
                    borderRadius: 'var(--radius-md)',
                    cursor: 'pointer',
                    fontSize: 'var(--font-size-xs)',
                  }}
                >
                  Ask AI
                </button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};
