import React from 'react';
import { InspectionStatus } from '../../types';
import { Check, AlertTriangle, X, HelpCircle, Minus } from 'lucide-react';

export interface StatusBadgeProps {
  status: InspectionStatus | string;
  size?: 'sm' | 'md';
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  size = 'md',
  className = '',
}) => {
  const normStatus = (status || 'UNKNOWN').toUpperCase() as InspectionStatus;

  const config: Record<
    InspectionStatus,
    { label: string; icon: React.ReactNode; bg: string; color: string; border: string }
  > = {
    PASS: {
      label: 'PASS',
      icon: <Check size={13} strokeWidth={2.5} />,
      bg: 'var(--status-pass-bg)',
      color: 'var(--status-pass)',
      border: 'var(--status-pass-border)',
    },
    ATTENTION: {
      label: 'ATTENTION',
      icon: <AlertTriangle size={13} strokeWidth={2.5} />,
      bg: 'var(--status-attention-bg)',
      color: 'var(--status-attention)',
      border: 'var(--status-attention-border)',
    },
    FAIL: {
      label: 'FAIL',
      icon: <X size={13} strokeWidth={2.5} />,
      bg: 'var(--status-fail-bg)',
      color: 'var(--status-fail)',
      border: 'var(--status-fail-border)',
    },
    UNKNOWN: {
      label: 'UNKNOWN',
      icon: <HelpCircle size={13} strokeWidth={2.5} />,
      bg: 'var(--status-unknown-bg)',
      color: 'var(--status-unknown)',
      border: 'var(--status-unknown-border)',
    },
    NOT_APPLICABLE: {
      label: 'N/A',
      icon: <Minus size={13} strokeWidth={2.5} />,
      bg: 'var(--bg-tertiary)',
      color: 'var(--text-muted)',
      border: 'var(--border-subtle)',
    },
  };

  const current = config[normStatus] || config.UNKNOWN;

  const fontSizes = {
    sm: 'var(--font-size-xs)',
    md: 'var(--font-size-sm)',
  };

  const paddings = {
    sm: '0.15rem 0.5rem',
    md: '0.25rem 0.75rem',
  };

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '0.35rem',
        backgroundColor: current.bg,
        color: current.color,
        border: `1px solid ${current.border}`,
        borderRadius: 'var(--radius-full)',
        fontSize: fontSizes[size],
        padding: paddings[size],
        fontWeight: 'var(--font-weight-bold)',
        letterSpacing: '0.02em',
        lineHeight: 1.2,
      }}
      className={`status-badge status-${normStatus.toLowerCase()} ${className}`}
      aria-label={`Inspection finding status: ${current.label}`}
    >
      <span aria-hidden="true">{current.icon}</span>
      <span>{current.label}</span>
    </span>
  );
};
