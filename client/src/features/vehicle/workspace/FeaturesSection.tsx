import React, { useState } from 'react';
import { VariantFeature, EvidenceState } from '../../../types';
import { Badge } from '../../../components/common/Badge';
import { Layers, Check, X, HelpCircle } from 'lucide-react';

export interface FeaturesSectionProps {
  features?: VariantFeature[];
  variantName?: string;
}

export const FeaturesSection: React.FC<FeaturesSectionProps> = ({
  features = [],
  variantName = 'Standard Trim',
}) => {
  const [filter, setFilter] = useState<'ALL' | 'STANDARD' | 'OPTIONAL'>('ALL');

  const filtered = features.filter((f) => {
    if (filter === 'ALL') return true;
    if (filter === 'STANDARD') return f.availability.toUpperCase() === 'STANDARD';
    if (filter === 'OPTIONAL') return f.availability.toUpperCase() === 'OPTIONAL';
    return true;
  });

  return (
    <div
      style={{
        borderRadius: 'var(--radius-xl)',
        backgroundColor: 'var(--bg-secondary)',
        border: '1px solid var(--border-medium)',
        padding: 'var(--space-6)',
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-5)',
      }}
    >
      {/* Header with Filter Pills */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 'var(--space-3)' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            <Layers size={20} style={{ color: 'var(--accent-blue)' }} />
            <h3 style={{ margin: 0, fontSize: 'var(--font-size-xl)' }}>
              Features & Equipment Breakdown
            </h3>
          </div>
          <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
            Equipment specification for {variantName}
          </span>
        </div>

        {/* Filter Switcher */}
        <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
          {(['ALL', 'STANDARD', 'OPTIONAL'] as const).map((mode) => (
            <button
              key={mode}
              onClick={() => setFilter(mode)}
              style={{
                padding: 'var(--space-1) var(--space-3)',
                borderRadius: 'var(--radius-full)',
                border: filter === mode ? '1px solid var(--accent-blue)' : '1px solid var(--border-medium)',
                backgroundColor: filter === mode ? 'var(--accent-blue)' : 'var(--bg-primary)',
                color: filter === mode ? '#FFFFFF' : 'var(--text-secondary)',
                fontSize: 'var(--font-size-xs)',
                fontWeight: filter === mode ? 'var(--font-weight-semibold)' : 'var(--font-weight-normal)',
                cursor: 'pointer',
              }}
            >
              {mode === 'ALL' ? 'All Features' : mode === 'STANDARD' ? 'Standard' : 'Optional'}
            </button>
          ))}
        </div>
      </div>

      {/* Features Grid */}
      {filtered.length === 0 ? (
        <div style={{ padding: 'var(--space-4)', textAlign: 'center', color: 'var(--text-muted)', fontSize: 'var(--font-size-sm)' }}>
          No features matching the selected filter.
        </div>
      ) : (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
            gap: 'var(--space-3)',
          }}
        >
          {filtered.map((f) => {
            const isStandard = f.availability.toUpperCase() === 'STANDARD';
            return (
              <div
                key={f.feature_key}
                style={{
                  padding: 'var(--space-3)',
                  backgroundColor: 'var(--bg-primary)',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border-subtle)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: 'var(--space-2)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                  {isStandard ? (
                    <Check size={16} style={{ color: 'var(--color-success)', flexShrink: 0 }} />
                  ) : (
                    <HelpCircle size={16} style={{ color: 'var(--color-warning)', flexShrink: 0 }} />
                  )}
                  <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 'var(--font-weight-medium)', color: 'var(--text-primary)' }}>
                    {f.feature_name || f.feature_key.replace(/_/g, ' ')}
                  </span>
                </div>

                <Badge variant={isStandard ? 'success' : 'neutral'} size="sm">
                  {f.availability}
                </Badge>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
