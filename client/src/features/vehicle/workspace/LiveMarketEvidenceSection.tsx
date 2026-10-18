import React from 'react';
import {
  CurrentMarketIntelligenceResponse,
  CurrentPriceDistribution,
  CurrentMarketSupply,
  CurrentRegionalIntelligence,
  CurrentVsHistoricalComparison,
  CurrentMarketEvidence,
} from '../../../types';
import { Badge } from '../../../components/common/Badge';
import {
  Radio,
  MapPin,
  TrendingUp,
  TrendingDown,
  Layers,
  ShieldCheck,
  AlertCircle,
  HelpCircle,
  Building2,
  Calendar,
} from 'lucide-react';

export interface LiveMarketEvidenceSectionProps {
  currentMarket?: CurrentMarketIntelligenceResponse | null;
  canonicalVehicleId: string;
}

const formatLakhs = (valInr?: number): string => {
  if (valInr === undefined || valInr === null || isNaN(valInr)) return '—';
  return `₹${(valInr / 100000).toFixed(2)}L`;
};

export const LiveMarketEvidenceSection: React.FC<LiveMarketEvidenceSectionProps> = ({
  currentMarket,
  canonicalVehicleId,
}) => {
  if (!currentMarket) {
    return (
      <div
        style={{
          borderRadius: 'var(--radius-xl)',
          backgroundColor: 'var(--bg-secondary)',
          border: '1px solid var(--border-medium)',
          padding: 'var(--space-6)',
          display: 'flex',
          flexDirection: 'column',
          gap: 'var(--space-3)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
          <Radio size={20} style={{ color: 'var(--text-muted)' }} />
          <h3 style={{ margin: 0, fontSize: 'var(--font-size-xl)' }}>
            Live Market Observations & Evidence
          </h3>
          <Badge variant="neutral" size="sm">No Feeds Available</Badge>
        </div>
        <p style={{ margin: 0, fontSize: 'var(--font-size-sm)', color: 'var(--text-muted)' }}>
          No current market observation feeds are currently connected for vehicle <code>{canonicalVehicleId}</code>.
          Pricing guidance relies strictly on the historical 2018–2024 empirical baseline.
        </p>
      </div>
    );
  }

  const {
    observation_period,
    supply,
    price_distribution,
    regional_breakdown,
    comparison_with_historical,
    evidence,
    limitations,
  } = currentMarket;

  const hasDistribution = price_distribution && price_distribution.sample_size >= 3;

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
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          flexWrap: 'wrap',
          gap: 'var(--space-3)',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            <Radio size={20} style={{ color: 'var(--color-primary)' }} />
            <h3 style={{ margin: 0, fontSize: 'var(--font-size-xl)' }}>
              Live Market Evidence & 2026 Observations
            </h3>
            <Badge variant="success" size="sm">
              {observation_period}
            </Badge>
          </div>
          <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
            Empirical multi-metro asking-price distributions, current supply velocity, and regional clusters
          </span>
        </div>

        <div style={{ display: 'flex', gap: 'var(--space-2)', flexWrap: 'wrap' }}>
          <Badge variant="info" size="sm">
            {supply.supply_tier.replace('_', ' ')}
          </Badge>
          <Badge variant="neutral" size="sm">
            {evidence.usable_observations} Usable Observations
          </Badge>
        </div>
      </div>

      {/* Epistemic Honesty Banner */}
      <div
        style={{
          backgroundColor: 'rgba(234, 179, 8, 0.08)',
          borderLeft: '4px solid #EAB308',
          padding: 'var(--space-3) var(--space-4)',
          borderRadius: 'var(--radius-md)',
          fontSize: 'var(--font-size-xs)',
          color: 'var(--text-secondary)',
          display: 'flex',
          gap: 'var(--space-3)',
          alignItems: 'flex-start',
        }}
      >
        <HelpCircle size={18} style={{ color: '#EAB308', flexShrink: 0, marginTop: '2px' }} />
        <div>
          <strong style={{ color: 'var(--text-primary)' }}>Epistemic Data Integrity Notice:</strong> Observations represent active seller asking prices collected across participating multi-metro feeds (2026-Q3). They do NOT represent completed sales, realized resale values, or guaranteed transaction settlements. Historical dataset remains 57,480 listings (2018–2024). Intrinsic vehicle scoring is strictly isolated from asking prices.
        </div>
      </div>

      {/* Metrics Row */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: 'var(--space-4)',
        }}
      >
        {/* Card 1: Asking Price Distribution */}
        <div
          style={{
            backgroundColor: 'var(--bg-tertiary)',
            padding: 'var(--space-4)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--border-subtle)',
          }}
        >
          <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)', marginBottom: 'var(--space-1)' }}>
            Current Asking Price (Median)
          </div>
          {hasDistribution ? (
            <>
              <div style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 'var(--font-weight-bold)', color: 'var(--text-primary)' }}>
                {formatLakhs(price_distribution.median_price)}
              </div>
              <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)', marginTop: 'var(--space-1)' }}>
                IQR: {formatLakhs(price_distribution.p25_price)} – {formatLakhs(price_distribution.p75_price)}
              </div>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: 'var(--space-1)' }}>
                Range (p10–p90): {formatLakhs(price_distribution.p10_price)} – {formatLakhs(price_distribution.p90_price)} (n={price_distribution.sample_size})
              </div>
            </>
          ) : (
            <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-muted)' }}>
              Insufficient observations for percentiles (n={supply.total_observations})
            </div>
          )}
        </div>

        {/* Card 2: Supply Depth */}
        <div
          style={{
            backgroundColor: 'var(--bg-tertiary)',
            padding: 'var(--space-4)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--border-subtle)',
          }}
        >
          <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)', marginBottom: 'var(--space-1)' }}>
            Current Supply Depth
          </div>
          <div style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 'var(--font-weight-bold)', color: 'var(--text-primary)' }}>
            {supply.active_listings_count} <span style={{ fontSize: 'var(--font-size-sm)', fontWeight: 'normal' }}>Active</span>
          </div>
          <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)', marginTop: 'var(--space-1)' }}>
            Total Recorded: {supply.total_observations} ({supply.supply_tier.replace('_', ' ')})
          </div>
          <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: 'var(--space-1)' }}>
            Freshness: {evidence.freshness_distribution['CURRENT'] || 0} Current (&le;30d), {evidence.freshness_distribution['AGING'] || 0} Aging
          </div>
        </div>

        {/* Card 3: Comparison with Historical Baseline */}
        {comparison_with_historical && (
          <div
            style={{
              backgroundColor: 'var(--bg-tertiary)',
              padding: 'var(--space-4)',
              borderRadius: 'var(--radius-lg)',
              border: '1px solid var(--border-subtle)',
            }}
          >
            <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)', marginBottom: 'var(--space-1)' }}>
              Historical vs Current Shift
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
              <span style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 'var(--font-weight-bold)', color: 'var(--text-primary)' }}>
                {comparison_with_historical.price_shift_percentage > 0 ? '+' : ''}
                {comparison_with_historical.price_shift_percentage.toFixed(1)}%
              </span>
              {comparison_with_historical.price_trend_direction === 'INCREASING' && (
                <TrendingUp size={18} style={{ color: '#EF4444' }} />
              )}
              {comparison_with_historical.price_trend_direction === 'DECREASING' && (
                <TrendingDown size={18} style={{ color: '#10B981' }} />
              )}
            </div>
            <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)', marginTop: 'var(--space-1)' }}>
              Historical: {formatLakhs(comparison_with_historical.historical_median_asking_price)} &rarr; Current: {formatLakhs(comparison_with_historical.current_median_asking_price)}
            </div>
            <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: 'var(--space-1)' }}>
              Historical sample: {comparison_with_historical.historical_sample_size != null ? comparison_with_historical.historical_sample_size.toLocaleString() : '—'} listings
            </div>
          </div>
        )}
      </div>

      {/* Regional Intelligence Breakdown */}
      {regional_breakdown && regional_breakdown.length > 0 && (
        <div style={{ marginTop: 'var(--space-2)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: 'var(--space-3)' }}>
            <MapPin size={16} style={{ color: 'var(--color-primary)' }} />
            <span style={{ fontSize: 'var(--font-size-sm)', fontWeight: 'var(--font-weight-semibold)' }}>
              Metropolitan Cluster Distribution & Median Asking Prices
            </span>
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
              gap: 'var(--space-3)',
            }}
          >
            {regional_breakdown.map((r) => (
              <div
                key={r.region}
                style={{
                  backgroundColor: 'var(--bg-tertiary)',
                  padding: 'var(--space-3)',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border-subtle)',
                }}
              >
                <div style={{ fontSize: 'var(--font-size-xs)', fontWeight: 'var(--font-weight-semibold)', color: 'var(--text-primary)' }}>
                  {r.region}
                </div>
                <div style={{ fontSize: 'var(--font-size-sm)', fontWeight: 'var(--font-weight-bold)', color: 'var(--color-primary)', marginTop: '2px' }}>
                  {formatLakhs(r.median_asking_price)}
                </div>
                <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '2px' }}>
                  {r.observation_count} listings ({r.share_percentage.toFixed(0)}% share)
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Evidence Provenance Footer */}
      <div
        style={{
          borderTop: '1px solid var(--border-subtle)',
          paddingTop: 'var(--space-4)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 'var(--space-2)',
          fontSize: 'var(--font-size-xs)',
          color: 'var(--text-muted)',
        }}
      >
        <div>
          <span>Feeds: </span>
          <strong>{evidence.sources_contributed.join(', ') || 'Governed Multi-Metro Feeds'}</strong>
          <span> &bull; Deduplication: {evidence.duplicate_count} isolated</span>
          <span> &bull; Outliers: {evidence.outlier_count} audited</span>
        </div>
        <div>
          <span>Collection Window: {evidence.collection_window}</span>
        </div>
      </div>
    </div>
  );
};
