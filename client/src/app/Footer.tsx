import React from 'react';
import { Shield, Database, Lock } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer
      style={{
        backgroundColor: 'var(--bg-primary)',
        borderTop: '1px solid var(--border-subtle)',
        marginTop: 'auto',
        padding: 'var(--space-12) 0 var(--space-8)',
      }}
    >
      <div className="container" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-8)' }}>
        {/* Top Grid */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
            gap: 'var(--space-8)',
          }}
        >
          {/* Mission & North Star */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
            <span
              style={{
                fontSize: 'var(--font-size-xl)',
                fontWeight: 'var(--font-weight-extrabold)',
                letterSpacing: '-0.02em',
                color: 'var(--text-primary)',
              }}
            >
              CAR<span style={{ color: 'var(--accent-blue)' }}>spective</span>
            </span>

            <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)', margin: 0, fontWeight: 'var(--font-weight-medium)' }}>
              <strong>Know the car. Know the value. Know the truth.</strong>
            </p>

            <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)', margin: 0, lineHeight: 1.6 }}>
              An evidence-first automotive intelligence platform engineered to eliminate information asymmetry in the
              Indian used car market.
            </p>
          </div>

          {/* Governance Disclosures */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
            <h4 style={{ fontSize: 'var(--font-size-sm)', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)' }}>
              Analytical Governance
            </h4>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 'var(--space-2)', fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              <Database size={14} color="var(--accent-blue)" style={{ marginTop: '3px', flexShrink: 0 }} />
              <span>
                Valuations represent statistical model estimates of the historical market asking-price baseline trained on
                57,480 verified historical Indian listings.
              </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 'var(--space-2)', fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              <Shield size={14} color="var(--status-pass)" style={{ marginTop: '3px', flexShrink: 0 }} />
              <span>
                CarSpective scores evaluate intrinsic vehicle proposition separately from asking-price deal quality.
              </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 'var(--space-2)', fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              <Lock size={14} color="var(--accent-intelligence)" style={{ marginTop: '3px', flexShrink: 0 }} />
              <span>
                Privacy first: Anonymous session operation with zero third-party telemetry, ads, or tracking cookies.
              </span>
            </div>
          </div>
        </div>

        {/* Bottom Copyright & Disclaimer */}
        <div
          style={{
            borderTop: '1px solid var(--border-light)',
            paddingTop: 'var(--space-6)',
            display: 'flex',
            flexWrap: 'wrap',
            justifyContent: 'space-between',
            alignItems: 'center',
            gap: 'var(--space-4)',
            fontSize: 'var(--font-size-xs)',
            color: 'var(--text-muted)',
          }}
        >
          <span>© 2026 CARspective Technologies. All rights reserved.</span>
          <span>Decision support platform. Does not constitute commercial warranty or financial advice.</span>
        </div>
      </div>
    </footer>
  );
};
