import React from 'react';
import { formatINR } from '../../utils/formatters';

export interface RangeProps {
  low: number;
  high: number;
  point?: number;
  pointLabel?: string;
  className?: string;
}

export const Range: React.FC<RangeProps> = ({
  low,
  high,
  point,
  pointLabel = 'Asking Price',
  className = '',
}) => {
  const span = Math.max(high - low, 1);
  let pointPercent: number | null = null;

  if (point !== undefined && point !== null) {
    const raw = ((point - low) / span) * 100;
    // Clamped between 0 and 100 for bar rendering
    pointPercent = Math.max(0, Math.min(100, raw));
  }

  const isBelow = point !== undefined && point < low;
  const isAbove = point !== undefined && point > high;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)', width: '100%' }} className={className}>
      {/* Range Track */}
      <div
        style={{
          position: 'relative',
          width: '100%',
          height: '10px',
          backgroundColor: 'var(--border-subtle)',
          borderRadius: 'var(--radius-full)',
          overflow: 'visible',
          marginTop: 'var(--space-4)',
          marginBottom: 'var(--space-2)',
        }}
      >
        {/* Fair Market Range Zone */}
        <div
          style={{
            position: 'absolute',
            left: '0%',
            width: '100%',
            height: '100%',
            backgroundColor: 'rgba(0, 102, 255, 0.2)',
            borderLeft: '2px solid var(--accent-blue)',
            borderRight: '2px solid var(--accent-blue)',
            borderRadius: 'var(--radius-full)',
          }}
        />

        {/* Pinpoint / Marker for specific point (e.g. asking price or target) */}
        {pointPercent !== null && (
          <div
            style={{
              position: 'absolute',
              left: `${pointPercent}%`,
              top: '50%',
              transform: 'translate(-50%, -50%)',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              zIndex: 2,
            }}
          >
            <div
              style={{
                width: '18px',
                height: '18px',
                borderRadius: '50%',
                backgroundColor: isAbove ? 'var(--status-fail)' : isBelow ? 'var(--status-pass)' : 'var(--accent-blue)',
                border: '3px solid #FFFFFF',
                boxShadow: 'var(--shadow-md)',
              }}
              title={`${pointLabel}: ${formatINR(point)}`}
            />
          </div>
        )}
      </div>

      {/* Bounds Labels */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          fontSize: 'var(--font-size-xs)',
          color: 'var(--text-muted)',
          fontWeight: 'var(--font-weight-medium)',
        }}
      >
        <span>Low: {formatINR(low)}</span>
        {point !== undefined && (
          <span style={{ fontWeight: 'var(--font-weight-bold)', color: isAbove ? 'var(--status-fail)' : 'var(--text-primary)' }}>
            {pointLabel}: {formatINR(point)}
          </span>
        )}
        <span>High: {formatINR(high)}</span>
      </div>
    </div>
  );
};
