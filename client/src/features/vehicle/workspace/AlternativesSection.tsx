import React from 'react';
import { MarketAlternative } from '../../../types';
import { Badge } from '../../../components/common/Badge';
import { Button } from '../../../components/common/Button';
import { Scale, ArrowRight, Award, Compass } from 'lucide-react';
import { useApp } from '../../../state/AppContext';

export interface AlternativesSectionProps {
  alternatives?: MarketAlternative[];
  onNavigateVehicle?: (canonicalId: string) => void;
  onNavigateTab?: (tab: string) => void;
}

export const AlternativesSection: React.FC<AlternativesSectionProps> = ({
  alternatives = [],
  onNavigateVehicle,
  onNavigateTab,
}) => {
  const { addComparisonVehicle } = useApp();

  if (alternatives.length === 0) {
    return null;
  }

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
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            <Compass size={20} style={{ color: 'var(--color-primary)' }} />
            <h3 style={{ margin: 0, fontSize: 'var(--font-size-xl)' }}>
              Market Alternatives & Tradeoffs
            </h3>
          </div>
          <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
            Ground-truthed segment competitors in similar price and capability categories
          </span>
        </div>

        <Badge variant="neutral" size="sm">
          {alternatives.length} Alternatives
        </Badge>
      </div>

      {/* Alternatives Cards */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: 'var(--space-4)',
        }}
      >
        {alternatives.map((alt, idx) => {
          const altId = `${alt.brand.toLowerCase().replace(/\s+/g, '-')}::${alt.model.toLowerCase().replace(/\s+/g, '-')}`;
          return (
            <div
              key={idx}
              style={{
                padding: 'var(--space-4)',
                backgroundColor: 'var(--bg-primary)',
                borderRadius: 'var(--radius-lg)',
                border: '1px solid var(--border-subtle)',
                display: 'flex',
                flexDirection: 'column',
                gap: 'var(--space-3)',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <h4 style={{ margin: '0 0 2px', fontSize: 'var(--font-size-base)', fontWeight: 'var(--font-weight-bold)' }}>
                    {alt.brand} {alt.model}
                  </h4>
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                    Typical Year: {alt.manufacturing_year} • Typical Price: {alt.typical_price_formatted}
                  </span>
                </div>
                <Badge variant="info" size="sm">
                  {alt.carspective_score}/100
                </Badge>
              </div>

              <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                <strong>Key Advantage:</strong> {alt.advantage_over_target}
              </div>

              <p style={{ margin: 0, fontSize: '11px', color: 'var(--text-tertiary)', lineHeight: 1.4 }}>
                {alt.rationale}
              </p>

              {/* Action Buttons */}
              <div style={{ display: 'flex', gap: 'var(--space-2)', marginTop: 'auto', paddingTop: 'var(--space-2)' }}>
                <Button
                  variant="outline"
                  size="sm"
                  leftIcon={<Scale size={14} />}
                  onClick={() => {
                    addComparisonVehicle({
                      brand: alt.brand,
                      model: alt.model,
                      year: alt.manufacturing_year,
                    });
                    if (onNavigateTab) onNavigateTab('comparison');
                  }}
                >
                  Compare
                </Button>

                <Button
                  variant="ghost"
                  size="sm"
                  rightIcon={<ArrowRight size={14} />}
                  onClick={() => onNavigateVehicle && onNavigateVehicle(altId)}
                >
                  View Workspace
                </Button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
