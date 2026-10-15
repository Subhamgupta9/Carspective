import React from 'react';
import { ExecutiveSummary, EvidenceState } from '../../../types';
import { Badge } from '../../../components/common/Badge';
import {
  Award,
  TrendingUp,
  Shield,
  Wrench,
  AlertTriangle,
  Sparkles,
  CheckCircle2,
} from 'lucide-react';

export interface ExecutiveSummaryCardProps {
  summary: ExecutiveSummary;
  coverageTier?: string;
}

export const ExecutiveSummaryCard: React.FC<ExecutiveSummaryCardProps> = ({
  summary,
  coverageTier = 'TIER_1_DEEP',
}) => {
  const getVerdictVariant = (verdict: string) => {
    switch (verdict.toUpperCase()) {
      case 'STRONG CONSIDERATION':
      case 'BUY':
        return 'success';
      case 'CONSIDER':
        return 'info';
      case 'PROCEED WITH CAUTION':
      case 'INSPECT_FIRST':
        return 'warning';
      case 'NOT RECOMMENDED':
      case 'AVOID':
        return 'danger';
      default:
        return 'neutral';
    }
  };

  const getScoreVariant = (band: string) => {
    switch (band) {
      case 'EXCELLENT':
        return 'success';
      case 'GOOD':
        return 'info';
      case 'FAIR':
        return 'warning';
      case 'CAUTION':
        return 'danger';
      default:
        return 'neutral';
    }
  };

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
        boxShadow: 'var(--shadow-sm)',
      }}
    >
      {/* Top Banner */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 'var(--space-3)',
          borderBottom: '1px solid var(--border-subtle)',
          paddingBottom: 'var(--space-4)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
          <Sparkles size={20} style={{ color: 'var(--accent-blue)' }} />
          <h2 style={{ margin: 0, fontSize: 'var(--font-size-xl)', fontWeight: 'var(--font-weight-bold)' }}>
            Executive Intelligence Summary
          </h2>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
          <Badge variant={getVerdictVariant(summary.recommendation_verdict)} size="md">
            Verdict: {summary.recommendation_verdict}
          </Badge>
          <Badge variant="neutral" size="sm">
            {coverageTier === 'TIER_1_DEEP' ? 'Tier 1 Deep Knowledge' : 'Tier 2 Empirical'}
          </Badge>
        </div>
      </div>

      {/* Decision Anchors Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: 'var(--space-4)',
        }}
      >
        {/* Anchor 1: Intrinsic Score */}
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
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', color: 'var(--text-muted)', fontSize: 'var(--font-size-xs)' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-1)' }}>
              <Award size={14} /> CarSpective Score
            </span>
            <Badge variant={getScoreVariant(summary.score_band)} size="sm">
              {summary.score_band}
            </Badge>
          </div>
          <div style={{ fontSize: 'var(--font-size-3xl)', fontWeight: 'var(--font-weight-bold)', color: 'var(--text-primary)' }}>
            {summary.carspective_score !== null && summary.carspective_score !== undefined
              ? `${summary.carspective_score}/100`
              : 'N/A'}
          </div>
          <span style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>
            Intrinsic vehicle ownership proposition
          </span>
        </div>

        {/* Anchor 2: Fair Market Value */}
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
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', color: 'var(--text-muted)', fontSize: 'var(--font-size-xs)' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-1)' }}>
              <TrendingUp size={14} /> Fair Market Value
            </span>
            {summary.deal_quality && (
              <Badge variant="info" size="sm">
                {summary.deal_quality.replace('_', ' ')}
              </Badge>
            )}
          </div>
          <div style={{ fontSize: 'var(--font-size-3xl)', fontWeight: 'var(--font-weight-bold)', color: 'var(--color-primary)' }}>
            {summary.estimated_fair_market_value_lakhs !== null && summary.estimated_fair_market_value_lakhs !== undefined
              ? `₹${summary.estimated_fair_market_value_lakhs.toFixed(2)} L`
              : 'N/A'}
          </div>
          <span style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>
            {summary.expected_fair_market_range_low_lakhs && summary.expected_fair_market_range_high_lakhs
              ? `Range: ₹${summary.expected_fair_market_range_low_lakhs.toFixed(2)} L – ₹${summary.expected_fair_market_range_high_lakhs.toFixed(2)} L`
              : 'Statistical asking-price baseline'}
          </span>
        </div>

        {/* Anchor 3: Safety Profile */}
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
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', color: 'var(--text-muted)', fontSize: 'var(--font-size-xs)' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-1)' }}>
              <Shield size={14} /> Safety Rating
            </span>
            {summary.bodyshell_integrity && (
              <Badge variant={summary.bodyshell_integrity.toLowerCase().includes('stable') ? 'success' : 'warning'} size="sm">
                {summary.bodyshell_integrity} Shell
              </Badge>
            )}
          </div>
          <div style={{ fontSize: 'var(--font-size-3xl)', fontWeight: 'var(--font-weight-bold)', color: 'var(--text-primary)' }}>
            {summary.safety_stars !== null && summary.safety_stars !== undefined
              ? `${summary.safety_stars} / 5 ★`
              : 'Not Rated'}
          </div>
          <span style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>
            {summary.safety_agency ? `${summary.safety_agency} official protocol` : 'No official crash rating published'}
          </span>
        </div>

        {/* Anchor 4: Ownership & Maintenance */}
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
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', color: 'var(--text-muted)', fontSize: 'var(--font-size-xs)' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-1)' }}>
              <Wrench size={14} /> Annual Maintenance
            </span>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
              {summary.maintenance_complexity || 'Standard'} Complexity
            </span>
          </div>
          <div style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 'var(--font-weight-bold)', color: 'var(--text-primary)' }}>
            {summary.typical_annual_maintenance_inr || '₹5,000 – ₹8,000 / yr'}
          </div>
          <span style={{ fontSize: '11px', color: summary.reliability_watchpoints_count > 0 ? 'var(--color-warning)' : 'var(--color-success)', display: 'flex', alignItems: 'center', gap: 'var(--space-1)' }}>
            {summary.reliability_watchpoints_count > 0 ? (
              <>
                <AlertTriangle size={12} /> {summary.reliability_watchpoints_count} documented watchpoints
              </>
            ) : (
              <>
                <CheckCircle2 size={12} /> No critical design defects reported
              </>
            )}
          </span>
        </div>
      </div>

      {/* Decision Takeaway Narrative */}
      <div
        style={{
          padding: 'var(--space-3) var(--space-4)',
          backgroundColor: 'rgba(49, 130, 206, 0.06)',
          borderRadius: 'var(--radius-md)',
          borderLeft: '4px solid var(--accent-blue)',
          fontSize: 'var(--font-size-sm)',
          color: 'var(--text-secondary)',
          lineHeight: 1.5,
        }}
      >
        <strong>Executive Takeaway:</strong> {summary.one_line_summary}
      </div>
    </div>
  );
};
