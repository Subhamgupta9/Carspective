import React from 'react';
import { ReliabilityIssue, EvidenceState } from '../../../types';
import { Badge } from '../../../components/common/Badge';
import { EvidenceBadge } from '../../../components/common/EvidenceBadge';
import { AlertTriangle, CheckCircle2, ShieldAlert, Wrench, Search } from 'lucide-react';

export interface ReliabilitySectionProps {
  issues?: ReliabilityIssue[];
  generationName?: string;
}

export const ReliabilitySection: React.FC<ReliabilitySectionProps> = ({
  issues = [],
  generationName = 'this generation',
}) => {
  const getSeverityVariant = (sev: string) => {
    switch (sev.toUpperCase()) {
      case 'CRITICAL':
      case 'HIGH':
        return 'danger';
      case 'MODERATE':
        return 'warning';
      case 'LOW':
      case 'ADVISORY':
      default:
        return 'info';
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
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            <AlertTriangle size={20} style={{ color: issues.length > 0 ? 'var(--color-warning)' : 'var(--color-success)' }} />
            <h3 style={{ margin: 0, fontSize: 'var(--font-size-xl)' }}>
              Known Reliability Watchpoints & Issues
            </h3>
          </div>
          <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
            Empirically documented mechanical, electrical, and systemic design watchpoints
          </span>
        </div>

        <Badge variant={issues.length > 0 ? 'warning' : 'success'} size="md">
          {issues.length} {issues.length === 1 ? 'Issue Documented' : 'Issues Documented'}
        </Badge>
      </div>

      {/* Issues List */}
      {issues.length === 0 ? (
        <div
          style={{
            padding: 'var(--space-4)',
            backgroundColor: 'rgba(56, 161, 105, 0.04)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid rgba(56, 161, 105, 0.2)',
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--space-3)',
            fontSize: 'var(--font-size-sm)',
            color: 'var(--text-secondary)',
          }}
        >
          <CheckCircle2 size={24} style={{ color: 'var(--color-success)', flexShrink: 0 }} />
          <span>
            No chronic mechanical defects or manufacturer recall advisories are documented for {generationName}.
          </span>
        </div>
      ) : (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
            gap: 'var(--space-4)',
          }}
        >
          {issues.map((issue) => (
            <div
              key={issue.issue_key}
              style={{
                padding: 'var(--space-4)',
                backgroundColor: 'var(--bg-primary)',
                borderRadius: 'var(--radius-lg)',
                border: '1px solid var(--border-subtle)',
                display: 'flex',
                flexDirection: 'column',
                gap: 'var(--space-2)',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 'var(--space-2)' }}>
                <span style={{ fontWeight: 'var(--font-weight-bold)', fontSize: 'var(--font-size-sm)', color: 'var(--text-primary)' }}>
                  {issue.title}
                </span>
                <Badge variant={getSeverityVariant(issue.severity)} size="sm">
                  {issue.severity}
                </Badge>
              </div>

              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-2)', fontSize: '11px', color: 'var(--text-muted)' }}>
                <span>Category: <strong>{issue.category}</strong></span>
                {issue.affected_years && <span>• Years: <strong>{issue.affected_years}</strong></span>}
                {issue.affected_powertrains && <span>• Trims: <strong>{issue.affected_powertrains}</strong></span>}
              </div>

              <p style={{ margin: 0, fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                {issue.description}
              </p>

              <div
                style={{
                  marginTop: 'auto',
                  paddingTop: 'var(--space-2)',
                  borderTop: '1px solid var(--border-subtle)',
                  fontSize: '11px',
                  color: 'var(--text-tertiary)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 'var(--space-1)',
                }}
              >
                <Search size={12} />
                <span>Verification: {issue.verification_status.replace('_', ' ')}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
