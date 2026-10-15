import React from 'react';
import { HelpCircle } from 'lucide-react';

export interface EmptyStateProps {
  title: string;
  description?: string;
  missingInfo?: string;
  whyItMatters?: string;
  nextStep?: string;
  action?: React.ReactNode;
  icon?: React.ReactNode;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  missingInfo,
  whyItMatters,
  nextStep,
  action,
  icon = <HelpCircle size={36} color="var(--text-muted)" />,
}) => {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 'var(--space-8) var(--space-6)',
        textAlign: 'center',
        backgroundColor: 'var(--bg-primary)',
        borderRadius: 'var(--radius-xl)',
        border: '1px dashed var(--border-medium)',
        gap: 'var(--space-3)',
      }}
      data-testid="empty-state"
    >
      <div style={{ opacity: 0.8 }}>{icon}</div>
      <h3 style={{ fontSize: 'var(--font-size-xl)', margin: 0 }}>{title}</h3>
      {description && (
        <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-muted)', maxWidth: '480px', margin: 0 }}>
          {description}
        </p>
      )}

      {(missingInfo || whyItMatters || nextStep) && (
        <div
          style={{
            marginTop: 'var(--space-2)',
            padding: 'var(--space-4)',
            backgroundColor: 'var(--bg-secondary)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--border-subtle)',
            textAlign: 'left',
            maxWidth: '520px',
            width: '100%',
            fontSize: 'var(--font-size-xs)',
            lineHeight: 1.5,
            display: 'flex',
            flexDirection: 'column',
            gap: 'var(--space-2)',
          }}
        >
          {missingInfo && (
            <div>
              <strong style={{ color: 'var(--text-primary)' }}>1. What is missing:</strong>{' '}
              <span style={{ color: 'var(--text-secondary)' }}>{missingInfo}</span>
            </div>
          )}
          {whyItMatters && (
            <div>
              <strong style={{ color: 'var(--text-primary)' }}>2. Why it matters:</strong>{' '}
              <span style={{ color: 'var(--text-secondary)' }}>{whyItMatters}</span>
            </div>
          )}
          {nextStep && (
            <div>
              <strong style={{ color: 'var(--color-primary)' }}>3. What you can do next:</strong>{' '}
              <span style={{ color: 'var(--text-secondary)' }}>{nextStep}</span>
            </div>
          )}
        </div>
      )}

      {action && <div style={{ marginTop: 'var(--space-2)' }}>{action}</div>}
    </div>
  );
};
