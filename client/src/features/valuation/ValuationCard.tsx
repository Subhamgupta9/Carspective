import React from 'react';
import { ValuationResponse } from '../../types';
import { formatINR, formatINRFull } from '../../utils/formatters';
import { EvidenceBadge } from '../../components/common/EvidenceBadge';
import { Range } from '../../components/common/Range';
import { Info, AlertTriangle, ShieldCheck, Database } from 'lucide-react';

export interface ValuationCardProps {
  valuation?: ValuationResponse | null;
  askingPrice?: number;
  isLoading?: boolean;
}

export const ValuationCard: React.FC<ValuationCardProps> = ({
  valuation,
  askingPrice,
  isLoading,
}) => {
  if (isLoading) {
    return (
      <div style={{ padding: 'var(--space-6)', textAlign: 'center' }}>
        <p style={{ color: 'var(--text-muted)', fontSize: 'var(--font-size-sm)' }}>
          Computing historical asking-price valuation and conformal range...
        </p>
      </div>
    );
  }

  if (!valuation) {
    return null;
  }

  const {
    estimated_fair_market_value,
    expected_fair_market_range,
    confidence_state,
    evidence_quality,
    market_evidence,
    limitations,
  } = valuation;

  const isInsufficient = confidence_state === 'INSUFFICIENT_DATA' || !estimated_fair_market_value;

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-5)',
        backgroundColor: 'var(--bg-primary)',
        borderRadius: 'var(--radius-xl)',
        border: '1px solid var(--border-subtle)',
        padding: 'var(--space-6)',
        boxShadow: 'var(--shadow-sm)',
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 'var(--space-3)',
          borderBottom: '1px solid var(--border-light)',
          paddingBottom: 'var(--space-4)',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            <h3 style={{ fontSize: 'var(--font-size-2xl)', margin: 0 }}>Market Valuation</h3>
            <EvidenceBadge state={evidence_quality || 'EMPIRICAL'} size="sm" />
          </div>
          <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-muted)', margin: 'var(--space-1) 0 0 0' }}>
            Statistical model estimate of the historical market asking-price baseline.
          </p>
        </div>

        <span
          style={{
            fontSize: 'var(--font-size-xs)',
            fontWeight: 'var(--font-weight-semibold)',
            backgroundColor: 'var(--bg-tertiary)',
            padding: 'var(--space-1) var(--space-3)',
            borderRadius: 'var(--radius-full)',
            color: 'var(--text-secondary)',
          }}
        >
          {confidence_state.replace('_', ' ')}
        </span>
      </div>

      {isInsufficient ? (
        /* Limited Analysis State */
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: 'var(--space-3)',
            padding: 'var(--space-4)',
            backgroundColor: 'var(--bg-secondary)',
            borderRadius: 'var(--radius-lg)',
            border: '1px dashed var(--border-medium)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', color: 'var(--status-attention)' }}>
            <AlertTriangle size={20} />
            <h4 style={{ margin: 0, fontSize: 'var(--font-size-base)', color: 'var(--text-primary)' }}>
              Limited Analysis
            </h4>
          </div>
          <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)', margin: 0 }}>
            Insufficient historical listing records exist for this specific configuration to produce an
            authoritative fair-market value estimate without excessive uncertainty.
          </p>
          <ul style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)', paddingLeft: 'var(--space-4)' }}>
            <li>What is known: Vehicle identity verified.</li>
            <li>What is missing: Robust local price distribution for this specific vintage/fuel variant.</li>
            <li>Why uncertainty is high: Sparse comparable density prevents calibrated conformal bounds.</li>
          </ul>
        </div>
      ) : (
        /* Full Calibrated Valuation Display */
        <>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
              gap: 'var(--space-6)',
              alignItems: 'center',
            }}
          >
            {/* Primary Value Callout */}
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span style={{ fontSize: 'var(--font-size-xs)', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 'var(--font-weight-semibold)', letterSpacing: '0.05em' }}>
                Estimated Fair Market Value
              </span>
              <span
                style={{
                  fontSize: 'var(--font-size-4xl)',
                  fontWeight: 'var(--font-weight-extrabold)',
                  color: 'var(--text-primary)',
                  letterSpacing: '-0.02em',
                  margin: 'var(--space-1) 0',
                }}
              >
                {formatINR(estimated_fair_market_value)}
              </span>
              <span style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-muted)' }}>
                Exact Baseline: {formatINRFull(estimated_fair_market_value)}
              </span>
            </div>

            {/* Expected Fair Market Range */}
            {expected_fair_market_range && (
              <div
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 'var(--space-2)',
                  backgroundColor: 'var(--bg-secondary)',
                  padding: 'var(--space-4)',
                  borderRadius: 'var(--radius-lg)',
                  border: '1px solid var(--border-light)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 'var(--font-weight-semibold)', color: 'var(--text-secondary)' }}>
                    Expected Fair Market Range
                  </span>
                  <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--accent-blue)', fontWeight: 'var(--font-weight-medium)' }}>
                    {expected_fair_market_range.confidence_interval_percent}% Conformal Interval
                  </span>
                </div>

                <div style={{ fontSize: 'var(--font-size-lg)', fontWeight: 'var(--font-weight-bold)', color: 'var(--text-primary)' }}>
                  {formatINR(expected_fair_market_range.lower_bound)} — {formatINR(expected_fair_market_range.upper_bound)}
                </div>

                {/* Range Bar Component */}
                <Range
                  low={expected_fair_market_range.lower_bound}
                  high={expected_fair_market_range.upper_bound}
                  point={askingPrice}
                  pointLabel="Asking Price"
                />
              </div>
            )}
          </div>

          {/* Historical Asking-Price Baseline Mandatory Governance Explanation */}
          <div
            style={{
              backgroundColor: 'var(--accent-blue-light)',
              borderRadius: 'var(--radius-md)',
              padding: 'var(--space-3) var(--space-4)',
              display: 'flex',
              gap: 'var(--space-2)',
              alignItems: 'flex-start',
            }}
          >
            <Database size={16} color="var(--accent-blue)" style={{ flexShrink: 0, marginTop: '2px' }} />
            <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              <strong>Empirical Asking-Price Baseline:</strong> This estimate is based on CarSpective's validated
              statistical model trained on 57,480 historical Indian used-car listing records. It represents observed
              seller asking price patterns, not guaranteed completed transaction values or guaranteed selling prices.
            </div>
          </div>

          {/* Market Evidence Footnote */}
          {market_evidence && market_evidence.comparable_count !== undefined && (
            <div style={{ display: 'flex', gap: 'var(--space-4)', fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
              <span>Historical sample density: {market_evidence.comparable_count} comparable listings</span>
              {market_evidence.price_spread_percent !== undefined && (
                <span>Market spread: ±{market_evidence.price_spread_percent}%</span>
              )}
            </div>
          )}
        </>
      )}

      {/* Disclosures & Limitations */}
      {limitations && limitations.length > 0 && (
        <div style={{ borderTop: '1px solid var(--border-light)', paddingTop: 'var(--space-3)' }}>
          <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)', lineHeight: 1.5 }}>
            <strong>Governance Notes:</strong> {limitations.join(' ')}
          </div>
        </div>
      )}
    </div>
  );
};
