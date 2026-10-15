import React from 'react';
import { VehicleProCon, EvidenceState } from '../../../types';
import { ThumbsUp, ThumbsDown } from 'lucide-react';

export interface ProsConsSectionProps {
  pros?: VehicleProCon[];
  cons?: VehicleProCon[];
}

export const ProsConsSection: React.FC<ProsConsSectionProps> = ({
  pros = [],
  cons = [],
}) => {
  if (pros.length === 0 && cons.length === 0) {
    return null;
  }

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
        gap: 'var(--space-4)',
      }}
    >
      {/* Verified Strengths */}
      {pros.length > 0 && (
        <div
          style={{
            padding: 'var(--space-5)',
            backgroundColor: 'var(--bg-secondary)',
            borderRadius: 'var(--radius-xl)',
            border: '1px solid rgba(56, 161, 105, 0.25)',
            display: 'flex',
            flexDirection: 'column',
            gap: 'var(--space-3)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', color: 'var(--color-success)', fontWeight: 'var(--font-weight-bold)', fontSize: 'var(--font-size-base)' }}>
            <ThumbsUp size={18} />
            <span>Verified Strengths</span>
          </div>
          <ul style={{ margin: 0, paddingLeft: 'var(--space-4)', fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: 'var(--space-2)', lineHeight: 1.5 }}>
            {pros.map((p, idx) => (
              <li key={idx}>{p.statement}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Documented Considerations */}
      {cons.length > 0 && (
        <div
          style={{
            padding: 'var(--space-5)',
            backgroundColor: 'var(--bg-secondary)',
            borderRadius: 'var(--radius-xl)',
            border: '1px solid rgba(229, 62, 62, 0.25)',
            display: 'flex',
            flexDirection: 'column',
            gap: 'var(--space-3)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', color: 'var(--color-danger)', fontWeight: 'var(--font-weight-bold)', fontSize: 'var(--font-size-base)' }}>
            <ThumbsDown size={18} />
            <span>Documented Considerations</span>
          </div>
          <ul style={{ margin: 0, paddingLeft: 'var(--space-4)', fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: 'var(--space-2)', lineHeight: 1.5 }}>
            {cons.map((c, idx) => (
              <li key={idx}>{c.statement}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};
