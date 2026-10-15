import React from 'react';
import { RecommendationResponse, MarketAlternative } from '../../types';
import { formatINR } from '../../utils/formatters';
import { Badge } from '../../components/common/Badge';
import { ThumbsUp, HelpCircle, AlertTriangle, XCircle, ArrowUpRight } from 'lucide-react';

export interface RecommendationCardProps {
  recommendation?: RecommendationResponse | null;
  onSelectAlternative?: (alt: MarketAlternative) => void;
  isLoading?: boolean;
}

export const RecommendationCard: React.FC<RecommendationCardProps> = ({
  recommendation,
  onSelectAlternative,
  isLoading,
}) => {
  if (isLoading) {
    return (
      <div style={{ padding: 'var(--space-6)', textAlign: 'center' }}>
        <p style={{ color: 'var(--text-muted)', fontSize: 'var(--font-size-sm)' }}>
          Evaluating holistic vehicle suitability and market alternatives...
        </p>
      </div>
    );
  }

  if (!recommendation) return null;

  const getVerdictConfig = (verdict: string) => {
    switch (verdict) {
      case 'STRONG CONSIDERATION':
        return {
          icon: <ThumbsUp size={20} />,
          badgeVariant: 'success' as const,
          color: 'var(--status-pass)',
          bg: 'var(--status-pass-bg)',
          border: 'var(--status-pass-border)',
        };
      case 'CONSIDER':
        return {
          icon: <HelpCircle size={20} />,
          badgeVariant: 'info' as const,
          color: 'var(--accent-blue)',
          bg: 'var(--accent-blue-light)',
          border: 'rgba(0, 102, 255, 0.2)',
        };
      case 'PROCEED WITH CAUTION':
        return {
          icon: <AlertTriangle size={20} />,
          badgeVariant: 'warning' as const,
          color: 'var(--status-attention)',
          bg: 'var(--status-attention-bg)',
          border: 'var(--status-attention-border)',
        };
      case 'NOT RECOMMENDED':
        return {
          icon: <XCircle size={20} />,
          badgeVariant: 'danger' as const,
          color: 'var(--status-fail)',
          bg: 'var(--status-fail-bg)',
          border: 'var(--status-fail-border)',
        };
      default:
        return {
          icon: <HelpCircle size={20} />,
          badgeVariant: 'neutral' as const,
          color: 'var(--text-muted)',
          bg: 'var(--bg-tertiary)',
          border: 'var(--border-subtle)',
        };
    }
  };

  const vConfig = getVerdictConfig(recommendation.verdict);

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
          <h3 style={{ fontSize: 'var(--font-size-2xl)', margin: 0 }}>Recommendation Analysis</h3>
          <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-muted)', margin: 'var(--space-1) 0 0 0' }}>
            Decision-support framework synthesizing vehicle quality, deal pricing, and buyer requirements.
          </p>
        </div>

        <Badge variant={vConfig.badgeVariant} size="md">
          {recommendation.verdict_label}
        </Badge>
      </div>

      {/* Verdict Banner */}
      <div
        style={{
          backgroundColor: vConfig.bg,
          border: `1px solid ${vConfig.border}`,
          borderRadius: 'var(--radius-lg)',
          padding: 'var(--space-4) var(--space-5)',
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--space-3)',
        }}
      >
        <span style={{ color: vConfig.color }}>{vConfig.icon}</span>
        <div>
          <div style={{ fontSize: 'var(--font-size-lg)', fontWeight: 'var(--font-weight-extrabold)', color: vConfig.color }}>
            {recommendation.verdict}
          </div>
          <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)', marginTop: '2px' }}>
            Decision support recommendation based on available vehicle evidence and commercial parameters.
          </div>
        </div>
      </div>

      {/* Structured Explanation Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
          gap: 'var(--space-4)',
        }}
      >
        <div style={{ backgroundColor: 'var(--bg-secondary)', padding: 'var(--space-4)', borderRadius: 'var(--radius-lg)' }}>
          <div style={{ fontSize: 'var(--font-size-xs)', fontWeight: 'var(--font-weight-semibold)', color: 'var(--status-pass)' }}>
            Strongest Positive Factor
          </div>
          <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-primary)', margin: 'var(--space-1) 0 0' }}>
            {recommendation.explanation.strongest_positive_factor}
          </p>
        </div>

        <div style={{ backgroundColor: 'var(--bg-secondary)', padding: 'var(--space-4)', borderRadius: 'var(--radius-lg)' }}>
          <div style={{ fontSize: 'var(--font-size-xs)', fontWeight: 'var(--font-weight-semibold)', color: 'var(--status-attention)' }}>
            Primary Trade-Off / Compromise
          </div>
          <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-primary)', margin: 'var(--space-1) 0 0' }}>
            {recommendation.explanation.biggest_tradeoff}
          </p>
        </div>

        <div style={{ backgroundColor: 'var(--bg-secondary)', padding: 'var(--space-4)', borderRadius: 'var(--radius-lg)' }}>
          <div style={{ fontSize: 'var(--font-size-xs)', fontWeight: 'var(--font-weight-semibold)', color: 'var(--accent-blue)' }}>
            Deal & Pricing Impact
          </div>
          <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-primary)', margin: 'var(--space-1) 0 0' }}>
            {recommendation.explanation.deal_consideration}
          </p>
        </div>
      </div>

      {/* User-Fit Score Breakdown */}
      {recommendation.user_fit && (
        <div style={{ backgroundColor: 'var(--bg-tertiary)', padding: 'var(--space-4)', borderRadius: 'var(--radius-lg)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-2)' }}>
            <span style={{ fontSize: 'var(--font-size-sm)', fontWeight: 'var(--font-weight-semibold)' }}>
              User-Fit Alignment: {recommendation.user_fit.overall_fit}%
            </span>
            <Badge variant="neutral" size="sm">
              User Stated
            </Badge>
          </div>
          <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)', margin: 0 }}>
            {recommendation.user_fit.fit_summary}
          </p>
        </div>
      )}

      {/* Market Alternatives */}
      {recommendation.alternatives && recommendation.alternatives.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
          <h4 style={{ fontSize: 'var(--font-size-base)', margin: 0 }}>Market Alternatives to Consider</h4>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 'var(--space-3)' }}>
            {recommendation.alternatives.map((alt, idx) => (
              <div
                key={idx}
                onClick={() => onSelectAlternative && onSelectAlternative(alt)}
                style={{
                  padding: 'var(--space-3) var(--space-4)',
                  borderRadius: 'var(--radius-lg)',
                  backgroundColor: 'var(--bg-secondary)',
                  border: '1px solid var(--border-light)',
                  cursor: onSelectAlternative ? 'pointer' : 'default',
                  transition: 'border-color var(--transition-fast)',
                }}
                onMouseEnter={e => (e.currentTarget.style.borderColor = 'var(--accent-blue)')}
                onMouseLeave={e => (e.currentTarget.style.borderColor = 'var(--border-light)')}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontWeight: 'var(--font-weight-bold)', fontSize: 'var(--font-size-sm)' }}>
                    {alt.brand} {alt.model} ({alt.manufacturing_year})
                  </span>
                  <ArrowUpRight size={14} color="var(--accent-blue)" />
                </div>
                <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--accent-blue)', fontWeight: 'var(--font-weight-semibold)', margin: 'var(--space-1) 0' }}>
                  Typical: {alt.typical_price_formatted} • Score: {alt.carspective_score}/100
                </div>
                <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)', lineHeight: 1.4 }}>
                  {alt.rationale}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
