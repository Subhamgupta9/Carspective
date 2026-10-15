import React, { useState } from 'react';
import { VehicleMarketProfile, LiquidityRating } from '../../../types';
import { Badge } from '../../../components/common/Badge';
import {
  BarChart3,
  TrendingDown,
  Clock,
  Layers,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  Info,
  CheckCircle2,
  DollarSign
} from 'lucide-react';

export interface MarketPositionSectionProps {
  brand: string;
  model: string;
  coverageTier?: string;
  marketProfile?: VehicleMarketProfile | null;
}

const getLiquidityBadgeVariant = (rating?: LiquidityRating): 'success' | 'info' | 'warning' | 'danger' => {
  switch (rating) {
    case 'VERY_HIGH':
    case 'HIGH':
      return 'success';
    case 'MODERATE':
      return 'info';
    case 'LOW':
      return 'warning';
    case 'VERY_LOW':
      return 'danger';
    default:
      return 'info';
  }
};

export const MarketPositionSection: React.FC<MarketPositionSectionProps> = ({
  brand,
  model,
  coverageTier = 'TIER_1_DEEP',
  marketProfile,
}) => {
  const [showFullCurve, setShowFullCurve] = useState(false);

  const pos = marketProfile?.market_position;
  const dep = marketProfile?.depreciation;
  const seg = marketProfile?.segment_benchmark;

  const points = dep?.curve_points || [];
  const displayedPoints = showFullCurve ? points : points.slice(0, 5);

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
          gap: 'var(--space-2)',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            <BarChart3 size={20} style={{ color: 'var(--color-primary)' }} />
            <h3 style={{ margin: 0, fontSize: 'var(--font-size-xl)' }}>
              Secondary Market Intelligence & Resale Position
            </h3>
          </div>
          <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
            Empirical secondary supply depth, resale liquidity velocity, and asking-price depreciation
          </span>
        </div>

        <div style={{ display: 'flex', gap: 'var(--space-2)', flexWrap: 'wrap' }}>
          {pos ? (
            <>
              <Badge variant={getLiquidityBadgeVariant(pos.liquidity_rating)} size="sm">
                {pos.liquidity_rating.replace('_', ' ')} Liquidity
              </Badge>
              <Badge variant="info" size="sm">
                {pos.supply_level.replace('_', ' ')} Supply
              </Badge>
            </>
          ) : (
            <Badge variant="info" size="sm">
              {coverageTier === 'TIER_1_DEEP' ? 'Tier 1 Core Market' : 'Tier 2 Secondary'}
            </Badge>
          )}
        </div>
      </div>

      {/* Core Market Metrics Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))',
          gap: 'var(--space-4)',
        }}
      >
        {/* Metric 1: Liquidity & Velocity */}
        <div
          style={{
            padding: 'var(--space-4)',
            backgroundColor: 'var(--bg-primary)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--border-subtle)',
            display: 'flex',
            flexDirection: 'column',
            gap: 'var(--space-1)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-1)', color: 'var(--text-muted)', fontSize: 'var(--font-size-xs)' }}>
            <Clock size={14} />
            <span>Turnover Velocity</span>
          </div>
          <div style={{ fontSize: 'var(--font-size-lg)', fontWeight: 'var(--font-weight-bold)', color: 'var(--text-primary)' }}>
            {pos?.estimated_days_to_sell_band || '30 – 60 Days'}
          </div>
          <span style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>
            Demand: {pos?.demand_proxy ? pos.demand_proxy.replace('_', ' ') : 'Steady Demand'}
          </span>
        </div>

        {/* Metric 2: Resale Retention Index */}
        <div
          style={{
            padding: 'var(--space-4)',
            backgroundColor: 'var(--bg-primary)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--border-subtle)',
            display: 'flex',
            flexDirection: 'column',
            gap: 'var(--space-1)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-1)', color: 'var(--text-muted)', fontSize: 'var(--font-size-xs)' }}>
            <TrendingDown size={14} />
            <span>Resale Value Retention</span>
          </div>
          <div style={{ fontSize: 'var(--font-size-lg)', fontWeight: 'var(--font-weight-bold)', color: 'var(--color-primary)' }}>
            {pos?.resale_retention_index ? `${pos.resale_retention_index}/100 Index` : '68/100 Index'}
          </div>
          <span style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>
            {dep?.three_year_retained_value_pct ? `3-Yr: ~${dep.three_year_retained_value_pct}% residual` : 'Above average segment retention'}
          </span>
        </div>

        {/* Metric 3: Secondary Listing Depth */}
        <div
          style={{
            padding: 'var(--space-4)',
            backgroundColor: 'var(--bg-primary)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--border-subtle)',
            display: 'flex',
            flexDirection: 'column',
            gap: 'var(--space-1)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-1)', color: 'var(--text-muted)', fontSize: 'var(--font-size-xs)' }}>
            <Layers size={14} />
            <span>Secondary Supply Depth</span>
          </div>
          <div style={{ fontSize: 'var(--font-size-lg)', fontWeight: 'var(--font-weight-bold)', color: 'var(--text-primary)' }}>
            {pos?.active_listings_proxy_count ? `${pos.active_listings_proxy_count.toLocaleString('en-IN')} Listings` : 'High Market Depth'}
          </div>
          <span style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>
            {pos?.market_share_in_segment_percent ? `${pos.market_share_in_segment_percent}% segment share` : 'Tier 1 volume'}
          </span>
        </div>

        {/* Metric 4: Empirical Secondary Price Baseline */}
        <div
          style={{
            padding: 'var(--space-4)',
            backgroundColor: 'var(--bg-primary)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--border-subtle)',
            display: 'flex',
            flexDirection: 'column',
            gap: 'var(--space-1)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-1)', color: 'var(--text-muted)', fontSize: 'var(--font-size-xs)' }}>
            <DollarSign size={14} />
            <span>Median Secondary Asking Price</span>
          </div>
          <div style={{ fontSize: 'var(--font-size-lg)', fontWeight: 'var(--font-weight-bold)', color: 'var(--text-primary)' }}>
            {pos?.median_historical_asking_price_inr
              ? `₹${(pos.median_historical_asking_price_inr / 100000).toFixed(2)} Lakh`
              : 'Market Baseline'}
          </div>
          <span style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>
            {pos?.p25_asking_price_inr && pos?.p75_asking_price_inr
              ? `P25-P75: ₹${(pos.p25_asking_price_inr / 100000).toFixed(1)}L – ₹${(pos.p75_asking_price_inr / 100000).toFixed(1)}L`
              : 'Empirical asking price baseline'}
          </span>
        </div>
      </div>

      {/* Segment Benchmark Comparison */}
      {seg && (
        <div
          style={{
            padding: 'var(--space-4)',
            backgroundColor: 'var(--bg-primary)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--border-subtle)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: 'var(--space-3)',
          }}
        >
          <div>
            <div style={{ fontSize: 'var(--font-size-xs)', fontWeight: 'var(--font-weight-semibold)', color: 'var(--text-secondary)' }}>
              Segment Comparison: {seg.segment_name}
            </div>
            <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-primary)', marginTop: '2px' }}>
              Segment Median Asking Price: <strong>₹{(seg.segment_median_asking_price_inr / 100000).toFixed(2)} Lakh</strong>
              {' • '}
              <span style={{ color: seg.vehicle_vs_segment_price_ratio > 1 ? 'var(--color-warning)' : 'var(--color-success)' }}>
                {seg.vehicle_price_position_label} ({Math.round(seg.vehicle_vs_segment_price_ratio * 100)}% of segment median)
              </span>
            </div>
          </div>

          {seg.top_competing_models && seg.top_competing_models.length > 0 && (
            <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
              Key segment rivals: {seg.top_competing_models.slice(0, 3).map(m => m.replace('-', ' ')).join(', ')}
            </div>
          )}
        </div>
      )}

      {/* Historical Asking-Price Depreciation Curve */}
      {points.length > 0 && (
        <div
          style={{
            backgroundColor: 'var(--bg-primary)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--border-subtle)',
            padding: 'var(--space-4)',
            display: 'flex',
            flexDirection: 'column',
            gap: 'var(--space-3)',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <h4 style={{ margin: 0, fontSize: 'var(--font-size-sm)', fontWeight: 'var(--font-weight-semibold)' }}>
                Empirical Asking-Price Depreciation Trajectory
              </h4>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                Observed price retention by vehicle age from secondary market listings
              </span>
            </div>

            <button
              onClick={() => setShowFullCurve(!showFullCurve)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                background: 'none',
                border: 'none',
                color: 'var(--color-primary)',
                fontSize: 'var(--font-size-xs)',
                fontWeight: 'var(--font-weight-semibold)',
                cursor: 'pointer',
                padding: '4px 8px',
              }}
            >
              {showFullCurve ? 'Show First 5 Years' : `Show All ${points.length} Years`}
              {showFullCurve ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            </button>
          </div>

          {/* Table / Bars */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
            {displayedPoints.map((pt) => {
              const retPct = Math.round(pt.retention_percent_of_year_1);
              return (
                <div
                  key={pt.age_years}
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '70px 100px 1fr 90px 90px',
                    alignItems: 'center',
                    gap: 'var(--space-3)',
                    fontSize: 'var(--font-size-xs)',
                    padding: 'var(--space-2) 0',
                    borderBottom: '1px solid var(--border-subtle)',
                  }}
                >
                  <span style={{ fontWeight: 'var(--font-weight-semibold)', color: 'var(--text-primary)' }}>
                    Year {pt.age_years}
                  </span>

                  <span style={{ color: 'var(--text-secondary)' }}>
                    ₹{(pt.median_asking_price_inr / 100000).toFixed(2)} Lakh
                  </span>

                  {/* Horizontal Bar */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                    <div
                      style={{
                        flex: 1,
                        height: '8px',
                        backgroundColor: 'var(--bg-secondary)',
                        borderRadius: 'var(--radius-full)',
                        overflow: 'hidden',
                      }}
                    >
                      <div
                        style={{
                          width: `${Math.min(100, retPct)}%`,
                          height: '100%',
                          backgroundColor: retPct > 65 ? 'var(--color-success)' : (retPct > 45 ? 'var(--color-primary)' : 'var(--color-warning)'),
                          borderRadius: 'var(--radius-full)',
                        }}
                      />
                    </div>
                    <span style={{ minWidth: '40px', fontWeight: 'var(--font-weight-semibold)', color: 'var(--text-primary)' }}>
                      {retPct}%
                    </span>
                  </div>

                  <span style={{ color: 'var(--text-muted)', textAlign: 'right' }}>
                    {pt.sample_size} listings
                  </span>

                  <span style={{ textAlign: 'right' }}>
                    {pt.is_statistically_robust ? (
                      <Badge variant="success" size="sm">Robust</Badge>
                    ) : (
                      <Badge variant="warning" size="sm">Low Sample</Badge>
                    )}
                  </span>
                </div>
              );
            })}
          </div>

          {dep?.caveat_note && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', fontSize: '11px', color: 'var(--text-tertiary)', marginTop: 'var(--space-2)' }}>
              <Info size={14} style={{ flexShrink: 0 }} />
              <span>{dep.caveat_note}</span>
            </div>
          )}
        </div>
      )}

      {/* Statutory Provenance Notice */}
      <div
        style={{
          padding: 'var(--space-3) var(--space-4)',
          backgroundColor: 'rgba(49, 130, 206, 0.05)',
          borderRadius: 'var(--radius-lg)',
          border: '1px solid rgba(49, 130, 206, 0.15)',
          display: 'flex',
          alignItems: 'flex-start',
          gap: 'var(--space-3)',
          fontSize: 'var(--font-size-xs)',
          color: 'var(--text-secondary)',
        }}
      >
        <Info size={16} style={{ color: 'var(--accent-blue)', flexShrink: 0, marginTop: '2px' }} />
        <div>
          <strong>Market Intelligence Provenance:</strong> Secondary market statistics reflect seller asking-price baselines from historical listings, not finalized RTO registration sale amounts. Transaction prices routinely conclude 5% to 10% below initial listing figures following on-site negotiation.
        </div>
      </div>
    </div>
  );
};
