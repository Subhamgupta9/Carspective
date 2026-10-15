import React from 'react';
import { ComparisonResponse } from '../../types';
import { Badge } from '../../components/common/Badge';
import { Trophy, Check, X, Shield, Activity, Wrench, RefreshCw, Car } from 'lucide-react';

export interface ComparisonMatrixProps {
  comparison?: ComparisonResponse | null;
  isLoading?: boolean;
}

export const ComparisonMatrix: React.FC<ComparisonMatrixProps> = ({
  comparison,
  isLoading,
}) => {
  if (isLoading) {
    return (
      <div style={{ padding: 'var(--space-8)', textAlign: 'center' }}>
        <p style={{ color: 'var(--text-muted)' }}>Comparing canonical vehicles and calculating trade-offs...</p>
      </div>
    );
  }

  if (!comparison) return null;

  const categoryIcons: Record<string, React.ReactNode> = {
    'Structural Safety': <Shield size={16} />,
    'Reliability & Longevity': <Activity size={16} />,
    'Maintenance & Ownership': <Wrench size={16} />,
    'Resale & Market Liquidity': <RefreshCw size={16} />,
    'Real-World Practicality': <Car size={16} />,
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
      {/* Overall Winner Callout Banner */}
      {comparison.overall_result && (
        <div
          style={{
            backgroundColor: 'var(--accent-blue-light)',
            border: '1px solid rgba(0, 102, 255, 0.2)',
            borderRadius: 'var(--radius-xl)',
            padding: 'var(--space-5)',
            display: 'flex',
            alignItems: 'flex-start',
            gap: 'var(--space-4)',
          }}
        >
          <div
            style={{
              padding: 'var(--space-3)',
              borderRadius: 'var(--radius-full)',
              backgroundColor: '#FFFFFF',
              color: 'var(--accent-blue)',
              boxShadow: 'var(--shadow-sm)',
            }}
          >
            <Trophy size={24} />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-1)', flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
              <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 'var(--font-weight-bold)', color: 'var(--accent-blue)', textTransform: 'uppercase' }}>
                Overall Outcome: {comparison.overall_result.result_type.replace('_', ' ')}
              </span>
            </div>

            <h3 style={{ margin: 0, fontSize: 'var(--font-size-2xl)', color: 'var(--text-primary)' }}>
              {comparison.overall_result.winner_name
                ? `${comparison.overall_result.winner_name} Leads Overall`
                : 'Balanced Proposition Across Candidates'}
            </h3>

            <p style={{ margin: 0, fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              {comparison.overall_result.rationale || comparison.overall_result.summary}
            </p>
          </div>
        </div>
      )}

      {/* Category Winners Grid */}
      {comparison.category_comparisons && Object.keys(comparison.category_comparisons).length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
          <h4 style={{ fontSize: 'var(--font-size-lg)', margin: 0 }}>Category Decision Analysis</h4>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 'var(--space-3)' }}>
            {Object.entries(comparison.category_comparisons).map(([catName, res]) => (
              <div
                key={catName}
                style={{
                  padding: 'var(--space-4)',
                  backgroundColor: 'var(--bg-secondary)',
                  borderRadius: 'var(--radius-lg)',
                  border: '1px solid var(--border-light)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 'var(--space-2)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', fontWeight: 'var(--font-weight-semibold)', fontSize: 'var(--font-size-sm)' }}>
                    {categoryIcons[catName] || <Activity size={14} />}
                    {catName}
                  </span>
                  <Badge variant={res.status === 'WINNER' ? 'success' : res.status === 'TIE' ? 'neutral' : 'warning'} size="sm">
                    {res.status === 'WINNER' && res.winner_name ? `${res.winner_name}` : res.status}
                  </Badge>
                </div>

                <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)', margin: 0 }}>
                  {res.summary}
                </p>

                {res.key_differences && res.key_differences.length > 0 && (
                  <ul style={{ fontSize: '0.75rem', color: 'var(--text-muted)', margin: 0, paddingLeft: 'var(--space-4)' }}>
                    {res.key_differences.map((diff, i) => (
                      <li key={i}>{diff}</li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Trade-offs & Scenarios */}
      {comparison.tradeoffs && comparison.tradeoffs.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
          <h4 style={{ fontSize: 'var(--font-size-lg)', margin: 0 }}>Vehicle Strengths & Compromises</h4>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: `repeat(${comparison.tradeoffs.length}, minmax(260px, 1fr))`,
              gap: 'var(--space-4)',
              overflowX: 'auto',
            }}
          >
            {comparison.tradeoffs.map(t => (
              <div
                key={t.vehicle_id}
                style={{
                  backgroundColor: 'var(--bg-secondary)',
                  borderRadius: 'var(--radius-lg)',
                  padding: 'var(--space-4)',
                  border: '1px solid var(--border-subtle)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 'var(--space-3)',
                }}
              >
                <div style={{ fontWeight: 'var(--font-weight-bold)', fontSize: 'var(--font-size-base)', borderBottom: '1px solid var(--border-light)', paddingBottom: 'var(--space-2)' }}>
                  {t.vehicle_name}
                </div>

                {/* Pros */}
                <div>
                  <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 'var(--font-weight-semibold)', color: 'var(--status-pass)' }}>
                    Key Advantages
                  </span>
                  <ul style={{ listStyle: 'none', padding: 0, margin: 'var(--space-1) 0 0', display: 'flex', flexDirection: 'column', gap: 'var(--space-1)' }}>
                    {t.key_strengths.map((pro, idx) => (
                      <li key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: 'var(--space-1)', fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)' }}>
                        <Check size={12} color="var(--status-pass)" style={{ marginTop: '3px', flexShrink: 0 }} />
                        <span>{pro}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Cons */}
                <div>
                  <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 'var(--font-weight-semibold)', color: 'var(--status-attention)' }}>
                    Watch Points & Limitations
                  </span>
                  <ul style={{ listStyle: 'none', padding: 0, margin: 'var(--space-1) 0 0', display: 'flex', flexDirection: 'column', gap: 'var(--space-1)' }}>
                    {t.key_weaknesses.map((con, idx) => (
                      <li key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: 'var(--space-1)', fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)' }}>
                        <X size={12} color="var(--status-attention)" style={{ marginTop: '3px', flexShrink: 0 }} />
                        <span>{con}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
