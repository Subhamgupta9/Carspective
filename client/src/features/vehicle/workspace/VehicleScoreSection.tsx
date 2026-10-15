import React from 'react';
import { ScoreResponse, EvidenceState } from '../../../types';
import { Badge } from '../../../components/common/Badge';
import { EvidenceBadge } from '../../../components/common/EvidenceBadge';
import { Award, ShieldCheck, Wrench, RefreshCw, Compass, CheckCircle2, AlertTriangle, Info } from 'lucide-react';

export interface VehicleScoreSectionProps {
  score?: ScoreResponse | null;
  isLoading?: boolean;
}

export const VehicleScoreSection: React.FC<VehicleScoreSectionProps> = ({
  score,
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
          minHeight: '200px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'var(--text-muted)',
        }}
      >
        Calculating Intrinsic CarSpective Score...
      </div>
    );
  }

  if (!score || score.overall_score === null) {
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
          CarSpective Score
        </h3>
        <p style={{ margin: 0, fontSize: 'var(--font-size-sm)', color: 'var(--text-muted)' }}>
          Insufficient empirical data to compute composite intrinsic score.
        </p>
      </div>
    );
  }

  const getDimensionIcon = (name: string) => {
    switch (name) {
      case 'Structural Safety':
        return <ShieldCheck size={18} style={{ color: 'var(--color-primary)' }} />;
      case 'Reliability & Longevity':
        return <Award size={18} style={{ color: 'var(--color-success)' }} />;
      case 'Maintenance & Ownership':
        return <Wrench size={18} style={{ color: 'var(--accent-blue)' }} />;
      case 'Resale & Market Liquidity':
        return <RefreshCw size={18} style={{ color: 'var(--color-warning)' }} />;
      case 'Real-World Practicality':
      default:
        return <Compass size={18} style={{ color: 'var(--text-primary)' }} />;
    }
  };

  const getScoreColor = (val?: number | null) => {
    if (val === null || val === undefined) return 'var(--text-muted)';
    if (val >= 80) return 'var(--color-success)';
    if (val >= 70) return 'var(--color-primary)';
    if (val >= 55) return 'var(--color-warning)';
    return 'var(--color-danger)';
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
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            <Award size={22} style={{ color: 'var(--color-primary)' }} />
            <h3 style={{ margin: 0, fontSize: 'var(--font-size-xl)' }}>
              Intrinsic CarSpective Score
            </h3>
          </div>
          <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
            Phase 5 Five-Dimension Evaluated Ownership Merit (Mathematically Isolated from Asking Price)
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
          <EvidenceBadge state={(score.evidence_quality as EvidenceState) || 'SUPPORTED'} size="sm" />
          <Badge variant="info" size="md">
            {score.overall_score_formatted || `${score.overall_score}/100`}
          </Badge>
        </div>
      </div>

      {/* 5 Locked Dimensions Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: 'var(--space-4)',
        }}
      >
        {score.dimensions.map((dim) => {
          const dimScore = dim.score;
          const scorePercent = dimScore !== null ? dimScore : 0;
          return (
            <div
              key={dim.dimension_name}
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
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                  {getDimensionIcon(dim.dimension_name)}
                  <span style={{ fontWeight: 'var(--font-weight-semibold)', fontSize: 'var(--font-size-sm)', color: 'var(--text-primary)' }}>
                    {dim.dimension_name}
                  </span>
                </div>
                <span
                  style={{
                    fontSize: 'var(--font-size-base)',
                    fontWeight: 'var(--font-weight-bold)',
                    color: getScoreColor(dimScore),
                  }}
                >
                  {dim.score_formatted || (dimScore !== null ? `${dimScore}/100` : 'N/A')}
                </span>
              </div>

              {/* Progress Bar */}
              <div
                style={{
                  height: '6px',
                  borderRadius: 'var(--radius-full)',
                  backgroundColor: 'var(--bg-tertiary)',
                  overflow: 'hidden',
                }}
              >
                <div
                  style={{
                    width: `${scorePercent}%`,
                    height: '100%',
                    backgroundColor: getScoreColor(dimScore),
                    borderRadius: 'var(--radius-full)',
                    transition: 'width 0.4s ease',
                  }}
                />
              </div>

              {/* Contributing Factors */}
              {dim.contributing_factors && dim.contributing_factors.length > 0 && (
                <ul
                  style={{
                    margin: 0,
                    paddingLeft: 'var(--space-4)',
                    fontSize: '11px',
                    color: 'var(--text-muted)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '2px',
                    lineHeight: 1.4,
                  }}
                >
                  {dim.contributing_factors.slice(0, 2).map((factor, idx) => (
                    <li key={idx}>{factor}</li>
                  ))}
                </ul>
              )}
            </div>
          );
        })}
      </div>

      {/* Explanation Narrative */}
      {score.explanation && (
        <div
          style={{
            padding: 'var(--space-3) var(--space-4)',
            backgroundColor: 'var(--bg-primary)',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--border-subtle)',
            fontSize: 'var(--font-size-xs)',
            color: 'var(--text-secondary)',
            lineHeight: 1.5,
          }}
        >
          <strong>Scoring Assessment:</strong> {score.explanation.summary}
        </div>
      )}

      {/* Governance & Anti-Hallucination Isolation Footer */}
      <div
        style={{
          display: 'flex',
          gap: 'var(--space-2)',
          padding: 'var(--space-3)',
          backgroundColor: 'rgba(56, 161, 105, 0.04)',
          borderRadius: 'var(--radius-md)',
          border: '1px solid rgba(56, 161, 105, 0.2)',
          fontSize: '11px',
          color: 'var(--text-tertiary)',
        }}
      >
        <Info size={16} style={{ flexShrink: 0, color: 'var(--color-success)', marginTop: '1px' }} />
        <span>
          <strong>Scoring Invariant:</strong> Intrinsic CarSpective Score evaluates engineering integrity, reliability track record, and ownership economics. It is 100% mathematically isolated from the asking price of any individual vehicle listing.
        </span>
      </div>
    </div>
  );
};
