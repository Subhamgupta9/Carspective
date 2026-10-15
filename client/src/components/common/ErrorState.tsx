import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { Button } from './Button';

export interface ErrorStateProps {
  title?: string;
  message: string;
  onRetry?: () => void;
  whatStillWorks?: string;
  requestId?: string;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Service Unavailable',
  message,
  onRetry,
  whatStillWorks,
  requestId,
}) => {
  return (
    <div
      role="alert"
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 'var(--space-8) var(--space-6)',
        textAlign: 'center',
        backgroundColor: 'var(--status-fail-bg)',
        border: '1px solid var(--status-fail-border)',
        borderRadius: 'var(--radius-xl)',
        maxWidth: '600px',
        margin: '0 auto',
      }}
    >
      <div style={{ color: 'var(--status-fail)', marginBottom: 'var(--space-3)' }}>
        <AlertTriangle size={36} />
      </div>

      <h3 style={{ fontSize: 'var(--font-size-xl)', color: 'var(--status-fail)', marginBottom: 'var(--space-2)' }}>
        {title}
      </h3>

      <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)', marginBottom: 'var(--space-4)' }}>
        {message}
      </p>

      {requestId && (
        <div
          style={{
            fontSize: 'var(--font-size-xs)',
            color: 'var(--text-muted)',
            fontFamily: 'monospace',
            marginBottom: 'var(--space-3)',
          }}
        >
          Reference ID: {requestId}
        </div>
      )}

      {whatStillWorks && (
        <div
          style={{
            backgroundColor: 'rgba(255, 255, 255, 0.7)',
            padding: 'var(--space-3) var(--space-4)',
            borderRadius: 'var(--radius-md)',
            fontSize: 'var(--font-size-xs)',
            color: 'var(--text-secondary)',
            marginBottom: 'var(--space-4)',
            textAlign: 'left',
            width: '100%',
          }}
        >
          <strong>What still works:</strong> {whatStillWorks}
        </div>
      )}

      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry} leftIcon={<RefreshCw size={14} />}>
          Try Again
        </Button>
      )}
    </div>
  );
};
