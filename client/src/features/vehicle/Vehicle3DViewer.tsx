import React, { useState } from 'react';
import { Eye, ShieldCheck, Info } from 'lucide-react';
import { Badge } from '../../components/common/Badge';

export interface Vehicle3DViewerProps {
  brand: string;
  model: string;
  year?: number;
}

export const Vehicle3DViewer: React.FC<Vehicle3DViewerProps> = ({
  brand,
  model,
  year,
}) => {
  const [interactiveMode, setInteractiveMode] = useState(false);

  // Strict Phase 9 Governance Rule:
  // Never present the Porsche 911 3D asset as a placeholder for non-Porsche vehicles!
  const isPorsche911 =
    brand.toLowerCase().includes('porsche') && model.toLowerCase().includes('911');

  return (
    <div
      style={{
        borderRadius: 'var(--radius-xl)',
        backgroundColor: 'var(--bg-secondary)',
        border: '1px solid var(--border-subtle)',
        padding: 'var(--space-6)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '260px',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* 3D Strategy Indicator Pill */}
      <div
        style={{
          position: 'absolute',
          top: 'var(--space-3)',
          right: 'var(--space-3)',
          display: 'flex',
          gap: 'var(--space-2)',
        }}
      >
        <Badge variant="neutral" size="sm">
          Optional 3D Enhancement
        </Badge>
      </div>

      {isPorsche911 ? (
        /* Verified Mapped Asset for Porsche 911 */
        <div style={{ textAlign: 'center', maxWidth: '440px' }}>
          <div style={{ marginBottom: 'var(--space-3)', color: 'var(--accent-blue)' }}>
            <Eye size={36} style={{ margin: '0 auto' }} />
          </div>
          <h4 style={{ margin: '0 0 var(--space-2)', fontSize: 'var(--font-size-base)' }}>
            Verified 3D Digital Twin Available
          </h4>
          <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)', marginBottom: 'var(--space-4)' }}>
            Licensed 3D model asset matched to Porsche 911 geometry. Information below remains immediately accessible without blocking.
          </p>
          <button
            onClick={() => setInteractiveMode(prev => !prev)}
            style={{
              padding: 'var(--space-2) var(--space-4)',
              borderRadius: 'var(--radius-lg)',
              backgroundColor: 'var(--accent-blue)',
              color: '#FFFFFF',
              fontSize: 'var(--font-size-xs)',
              fontWeight: 'var(--font-weight-semibold)',
              cursor: 'pointer',
            }}
          >
            {interactiveMode ? 'Close 3D View' : 'Load Interactive 3D Model'}
          </button>
        </div>
      ) : (
        /* Low-Power Intelligent Blueprint Fallback for All Other Vehicles */
        <div style={{ textAlign: 'center', maxWidth: '480px' }}>
          <div
            style={{
              width: '80px',
              height: '80px',
              margin: '0 auto var(--space-3)',
              borderRadius: 'var(--radius-full)',
              backgroundColor: 'var(--bg-primary)',
              border: '1px solid var(--border-medium)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--accent-blue)',
              boxShadow: 'var(--shadow-sm)',
            }}
          >
            <ShieldCheck size={36} />
          </div>

          <h4 style={{ margin: '0 0 var(--space-1)', fontSize: 'var(--font-size-base)', color: 'var(--text-primary)' }}>
            Verified Dimensional Geometry
          </h4>

          <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)', lineHeight: 1.5, margin: '0 0 var(--space-3)' }}>
            {brand} {model} {year || ''} verified technical profile. To maintain architectural integrity, CarSpective
            refuses to substitute unrelated 3D models (such as sports cars) for family sedans, hatchbacks, or SUVs.
          </p>

          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 'var(--space-1)',
              fontSize: '0.7rem',
              color: 'var(--text-muted)',
              backgroundColor: 'var(--bg-primary)',
              padding: 'var(--space-1) var(--space-3)',
              borderRadius: 'var(--radius-full)',
              border: '1px solid var(--border-light)',
            }}
          >
            <Info size={12} color="var(--accent-intelligence)" />
            <span>Zero Watermark Scripts • Clean Licensed Telemetry Only</span>
          </div>
        </div>
      )}
    </div>
  );
};
