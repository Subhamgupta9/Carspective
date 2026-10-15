import React from 'react';
import { ValuationResponse, EvidenceState } from '../../../types';
import { Badge } from '../../../components/common/Badge';
import { EvidenceBadge } from '../../../components/common/EvidenceBadge';
import { TrendingUp, Info, HelpCircle } from 'lucide-react';

export interface MarketValueCardProps {
  valuation?: ValuationResponse | null;
  isLoading?: boolean;
}

export const MarketValueCard: React.FC<MarketValueCardProps> = ({
  valuation,
  isLoading,
}) => {
  if (isLoading) {
    return (
      <div
        style={{
          borderRadius: 'var(--radius-xl)',
          backgroundColor: 'var(--bg-secondary)',
          border: '1px solid var(--border-subtle)',
          padding: 'var(--space-6)',
          minHeight: '180px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'var(--text-muted)',
        }}
      >
        Calculating Fair Market Value...
      </div>
    );
  }

  if (!valuation || !valuation.estimated_fair_market_value) {
    return (
      <div
        style={{
          borderRadius: 'var(--radius-xl)',
          backgroundColor: 'var(--bg-secondary)',
          border: '1px solid var(--border-subtle)',
          padding: 'var(--space-6)',
        }}
      >
        <h3 style={{ margin: '0 0 var(--space-2)', fontSize: 'var(--font-size-lg)' }}>
          Fair Market Value
        </h3>
        <p style={{ margin: 0, fontSize: 'var(--font-size-sm)', color: 'var(--text-muted)' }}>
          Valuation model baseline is unavailable for this specific configuration.
        </p>
      </div>
    );
  }

  const fmv = valuation.estimated_fair_market_value;
  const fmvLakhs = (fmv / 100000).toFixed(2);
  const range = valuation.expected_fair_market_range;
  const lowLakhs = range ? (range.lower_bound / 100000).toFixed(2) : null;
  const highLakhs = range ? (range.upper_bound / 100000).toFixed(2) : null;

  // Calculate percentage position of fmv between low and high
  let fmvPercent = 50;
  if (range && range.upper_bound > range.lower_bound) {
    fmvPercent = Math.round(((fmv - range.lower_bound) / (range.upper_bound - range.lower_bound)) * 100);
    fmvPercent = Math.max(10, Math.min(90, fmvPercent));
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
        gap: 'var(--space-4)',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: 'var(--space-1)' }}>
            <TrendingUp size={20} style={{ color: 'var(--color-primary)' }} />
            <h3 style={{ margin: 0, fontSize: 'var(--font-size-xl)' }}>
              Estimated Fair Market Value
            </h3>
          </div>
          <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
            Phase 3 Machine Learning Historical Baseline
          </span>
        </div>

        <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
          <EvidenceBadge state={(valuation.evidence_quality as EvidenceState) || 'MODEL_ESTIMATE'} size="sm" />
          <Badge variant="neutral" size="sm">
            {valuation.confidence_state.replace('_', ' ')}
          </Badge>
        </div>
      </div>

      {/* Main Figures */}
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'baseline', gap: 'var(--space-4)' }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 'var(--space-2)' }}>
          <span style={{ fontSize: 'var(--font-size-4xl)', fontWeight: 'var(--font-weight-bold)', color: 'var(--color-primary)', letterSpacing: '-0.02em' }}>
            ₹{fmvLakhs} Lakhs
          </span>
          <span style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-muted)' }}>
            (₹{fmv.toLocaleString('en-IN')})
          </span>
        </div>

        {lowLakhs && highLakhs && (
          <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)' }}>
            Expected Fair Market Range: <strong>₹{lowLakhs} L – ₹{highLakhs} L</strong>
          </div>
        )}
      </div>

      {/* Visual Conformal Range Gauge */}
      {range && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)', margin: 'var(--space-2) 0' }}>
          <div
            style={{
              height: '10px',
              borderRadius: 'var(--radius-full)',
              backgroundColor: 'var(--bg-tertiary)',
              position: 'relative',
              overflow: 'visible',
            }}
          >
            {/* Range highlight */}
            <div
              style={{
                position: 'absolute',
                left: '0%',
                right: '0%',
                top: 0,
                bottom: 0,
                backgroundColor: 'rgba(49, 130, 206, 0.25)',
                borderRadius: 'var(--radius-full)',
              }}
            />
            {/* FMV Indicator Pin */}
            <div
              style={{
                position: 'absolute',
                left: `${fmvPercent}%`,
                top: '-4px',
                width: '18px',
                height: '18px',
                borderRadius: 'var(--radius-full)',
                backgroundColor: 'var(--color-primary)',
                border: '2px solid #FFFFFF',
                boxShadow: 'var(--shadow-md)',
                transform: 'translateX(-50%)',
              }}
              title={`FMV: ₹${fmvLakhs} L`}
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--text-muted)' }}>
            <span>Low: ₹{lowLakhs} L</span>
            <span style={{ color: 'var(--color-primary)', fontWeight: 'var(--font-weight-bold)' }}>
              Point Estimate: ₹{fmvLakhs} L
            </span>
            <span>High: ₹{highLakhs} L</span>
          </div>
        </div>
      )}

      {/* Epistemic Disclosures & Conformal Framing */}
      <div
        style={{
          display: 'flex',
          gap: 'var(--space-2)',
          padding: 'var(--space-3)',
          backgroundColor: 'var(--bg-primary)',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--border-subtle)',
          fontSize: '11px',
          color: 'var(--text-tertiary)',
          lineHeight: 1.4,
        }}
      >
        <Info size={16} style={{ flexShrink: 0, marginTop: '2px', color: 'var(--text-muted)' }} />
        <span>
          <strong>Valuation Governance:</strong> Estimated from CarSpective&apos;s valuation model based on 57,480 historical seller asking-price observations (2018–2024). The Expected Fair Market Range represents 80% empirical conformal coverage. This estimate does not represent completed transaction sale prices or guaranteed trade-in offers.
        </span>
      </div>
    </div>
  );
};
