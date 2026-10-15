import React from 'react';
import { ScoreResponse, DimensionScore } from '../../types';
import { EvidenceBadge } from './EvidenceBadge';
import { Shield, Wrench, RefreshCw, Activity, Car, Info } from 'lucide-react';

export interface ScoreProps {
  score?: ScoreResponse | null;
  isLoading?: boolean;
}

export const Score: React.FC<ScoreProps> = ({ score, isLoading }) => {
  if (isLoading) {
    return (
      <div style={{ padding: 'var(--space-6)', textAlign: 'center' }}>
        <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-muted)' }}>Calculating CARspective Score...</div>
      </div>
    );
  }

  if (!score) {
    return null;
  }

  const dimensionIcons: Record<string, React.ReactNode> = {
    'Structural Safety': <Shield size={16} />,
    'Reliability & Longevity': <Activity size={16} />,
    'Maintenance & Ownership': <Wrench size={16} />,
    'Resale & Market Liquidity': <RefreshCw size={16} />,
    'Real-World Practicality': <Car size={16} />,
  };

  const getScoreColor = (val?: number | null) => {
    if (val === null || val === undefined) return 'var(--text-muted)';
    if (val >= 80) return 'var(--status-pass)';
    if (val >= 65) return 'var(--accent-blue)';
    if (val >= 50) return 'var(--status-attention)';
    return 'var(--status-fail)';
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-6)',
        backgroundColor: 'var(--bg-primary)',
        borderRadius: 'var(--radius-xl)',
        border: '1px solid var(--border-subtle)',
        padding: 'var(--space-6)',
        boxShadow: 'var(--shadow-sm)',
      }}
    >
      {/* Top Banner: Score & Concept Separation */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 'var(--space-4)',
          borderBottom: '1px solid var(--border-light)',
          paddingBottom: 'var(--space-5)',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            <h3 style={{ fontSize: 'var(--font-size-2xl)', margin: 0 }}>CARspective Score</h3>
            <EvidenceBadge state={score.evidence_quality} size="sm" />
          </div>
          <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-muted)', marginTop: 'var(--space-1)' }}>
            Intrinsic vehicle ownership quality based on safety, reliability, and maintenance evidence.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'baseline', gap: 'var(--space-2)' }}>
          <span
            style={{
              fontSize: 'var(--font-size-4xl)',
              fontWeight: 'var(--font-weight-extrabold)',
              color: getScoreColor(score.overall_score),
              letterSpacing: '-0.03em',
            }}
          >
            {score.overall_score !== null && score.overall_score !== undefined
              ? score.overall_score
              : '—'}
          </span>
          <span style={{ fontSize: 'var(--font-size-lg)', color: 'var(--text-muted)' }}>
            {score.overall_score !== null ? '/ 100' : 'Limited Analysis'}
          </span>
        </div>
      </div>

      {/* Critical Principle Disclaimer Pill */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--space-2)',
          backgroundColor: 'var(--bg-secondary)',
          borderRadius: 'var(--radius-md)',
          padding: 'var(--space-2) var(--space-3)',
          fontSize: 'var(--font-size-xs)',
          color: 'var(--text-secondary)',
        }}
      >
        <Info size={14} color="var(--accent-intelligence)" />
        <span>
          <strong>Vehicle Quality ≠ Deal Quality:</strong> This score measures intrinsic engineering and ownership
          merit. It does <em>not</em> factor in asking price or listing condition.
        </span>
      </div>

      {/* Five Dimensions Breakdown */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
        <h4 style={{ fontSize: 'var(--font-size-sm)', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)' }}>
          Five Evaluated Dimensions
        </h4>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 'var(--space-3)' }}>
          {score.dimensions.map((dim: DimensionScore) => (
            <div
              key={dim.dimension_name}
              style={{
                backgroundColor: 'var(--bg-secondary)',
                borderRadius: 'var(--radius-lg)',
                padding: 'var(--space-3) var(--space-4)',
                border: '1px solid var(--border-light)',
                display: 'flex',
                flexDirection: 'column',
                gap: 'var(--space-2)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', fontSize: 'var(--font-size-xs)', fontWeight: 'var(--font-weight-semibold)', color: 'var(--text-primary)' }}>
                  {dimensionIcons[dim.dimension_name] || <Activity size={14} />}
                  {dim.dimension_name}
                </span>
                <span
                  style={{
                    fontSize: 'var(--font-size-sm)',
                    fontWeight: 'var(--font-weight-bold)',
                    color: getScoreColor(dim.score),
                  }}
                >
                  {dim.score_formatted}
                </span>
              </div>

              {/* Progress bar */}
              <div
                style={{
                  width: '100%',
                  height: '6px',
                  backgroundColor: 'var(--border-subtle)',
                  borderRadius: 'var(--radius-full)',
                  overflow: 'hidden',
                }}
              >
                <div
                  style={{
                    width: `${dim.score ?? 0}%`,
                    height: '100%',
                    backgroundColor: getScoreColor(dim.score),
                    transition: 'width var(--transition-smooth)',
                  }}
                />
              </div>

              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 'var(--space-1)' }}>
                <EvidenceBadge state={dim.evidence_state} size="sm" />
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{dim.confidence} Confidence</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Structured Explanation Summary */}
      {score.explanation && (
        <div
          style={{
            backgroundColor: 'var(--bg-tertiary)',
            borderRadius: 'var(--radius-lg)',
            padding: 'var(--space-4)',
            fontSize: 'var(--font-size-sm)',
            lineHeight: 1.6,
          }}
        >
          <div style={{ fontWeight: 'var(--font-weight-semibold)', color: 'var(--text-primary)', marginBottom: 'var(--space-1)' }}>
            Analytical Summary
          </div>
          <p style={{ margin: 0, color: 'var(--text-secondary)' }}>{score.explanation.summary}</p>
        </div>
      )}
    </div>
  );
};
