import React from 'react';
import { VehicleSafetyRating, EvidenceState } from '../../../types';
import { Badge } from '../../../components/common/Badge';
import { EvidenceBadge } from '../../../components/common/EvidenceBadge';
import { Shield, ShieldAlert, ShieldCheck, CheckCircle2, AlertTriangle, Info } from 'lucide-react';

export interface SafetySectionProps {
  safety?: VehicleSafetyRating | null;
  generationName?: string;
}

export const SafetySection: React.FC<SafetySectionProps> = ({
  safety,
  generationName = 'this generation',
}) => {
  if (!safety) {
    return (
      <div
        style={{
          borderRadius: 'var(--radius-xl)',
          backgroundColor: 'var(--bg-secondary)',
          border: '1px solid var(--border-subtle)',
          padding: 'var(--space-6)',
          display: 'flex',
          flexDirection: 'column',
          gap: 'var(--space-3)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
          <Shield size={20} style={{ color: 'var(--text-muted)' }} />
          <h3 style={{ margin: 0, fontSize: 'var(--font-size-xl)' }}>
            Safety & Crash Test Assessment
          </h3>
        </div>
        <div
          style={{
            padding: 'var(--space-4)',
            backgroundColor: 'var(--bg-primary)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--border-subtle)',
            fontSize: 'var(--font-size-sm)',
            color: 'var(--text-secondary)',
          }}
        >
          No independent crash test rating has been published for {generationName}. CarSpective does not extrapolate safety ratings across unverified model iterations.
        </div>
      </div>
    );
  }

  const isStable = safety.bodyshell_integrity?.toLowerCase().includes('stable') && !safety.bodyshell_integrity?.toLowerCase().includes('unstable');

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
            <Shield size={20} style={{ color: isStable ? 'var(--color-success)' : 'var(--color-warning)' }} />
            <h3 style={{ margin: 0, fontSize: 'var(--font-size-xl)' }}>
              Safety & Crash Test Assessment
            </h3>
          </div>
          <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
            Official {safety.organization} ({safety.test_year}) Protocol
          </span>
        </div>

        <EvidenceBadge state={(safety.evidence_state as EvidenceState) || 'VERIFIED'} size="sm" />
      </div>

      {/* Star Ratings Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: 'var(--space-4)',
        }}
      >
        {/* Adult Occupant Safety */}
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
          <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
            Adult Occupant Protection
          </span>
          <div style={{ fontSize: 'var(--font-size-3xl)', fontWeight: 'var(--font-weight-bold)', color: 'var(--text-primary)' }}>
            {'★'.repeat(safety.adult_stars)}{'☆'.repeat(5 - safety.adult_stars)}
          </div>
          <span style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>
            {safety.adult_stars} of 5 Stars {safety.adult_score ? `(${safety.adult_score} pts)` : ''}
          </span>
        </div>

        {/* Child Occupant Safety */}
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
          <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
            Child Occupant Protection
          </span>
          <div style={{ fontSize: 'var(--font-size-3xl)', fontWeight: 'var(--font-weight-bold)', color: 'var(--text-primary)' }}>
            {safety.child_stars !== undefined && safety.child_stars !== null
              ? `${'★'.repeat(safety.child_stars)}${'☆'.repeat(5 - safety.child_stars)}`
              : 'Not Tested'}
          </div>
          <span style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>
            {safety.child_stars !== null ? `${safety.child_stars} of 5 Stars` : 'Protocol without child rig'}
          </span>
        </div>

        {/* Bodyshell Integrity */}
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
          <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
            Bodyshell Structural Integrity
          </span>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginTop: 'var(--space-1)' }}>
            <Badge variant={isStable ? 'success' : 'danger'} size="md">
              {safety.bodyshell_integrity || 'Unrated'}
            </Badge>
          </div>
          <span style={{ fontSize: '11px', color: 'var(--text-tertiary)', marginTop: 'var(--space-1)' }}>
            {isStable ? 'Capable of withstanding further loadings' : 'Not capable of withstanding further structural loads'}
          </span>
        </div>
      </div>

      {/* Standard Safety Equipment */}
      {safety.standard_safety_equipment && (
        <div
          style={{
            padding: 'var(--space-3) var(--space-4)',
            backgroundColor: 'var(--bg-primary)',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--border-subtle)',
            fontSize: 'var(--font-size-xs)',
            color: 'var(--text-secondary)',
          }}
        >
          <strong>Tested Standard Equipment:</strong> {safety.standard_safety_equipment}
        </div>
      )}

      {/* Generation Isolation Boundary */}
      <div
        style={{
          display: 'flex',
          gap: 'var(--space-2)',
          padding: 'var(--space-3)',
          backgroundColor: 'rgba(49, 130, 206, 0.04)',
          borderRadius: 'var(--radius-md)',
          border: '1px solid rgba(49, 130, 206, 0.2)',
          fontSize: '11px',
          color: 'var(--text-tertiary)',
        }}
      >
        <Info size={16} style={{ flexShrink: 0, color: 'var(--accent-blue)', marginTop: '1px' }} />
        <span>
          <strong>Generation Scoping:</strong> This crash rating applies exclusively to {generationName}. Safety ratings do not carry over across facelifts, major platform changes, or different vehicle generations.
        </span>
      </div>
    </div>
  );
};
