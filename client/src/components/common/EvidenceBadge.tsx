import React from 'react';
import { EvidenceState } from '../../types';
import { CheckCircle2, ShieldCheck, Database, Cpu, User, AlertCircle, HelpCircle } from 'lucide-react';

export interface EvidenceBadgeProps {
  state: EvidenceState | string;
  size?: 'sm' | 'md';
  className?: string;
  showIcon?: boolean;
}

export const EvidenceBadge: React.FC<EvidenceBadgeProps> = ({
  state,
  size = 'md',
  className = '',
  showIcon = true,
}) => {
  const normState = (state || 'UNVERIFIED').toUpperCase() as EvidenceState;

  const config: Record<
    EvidenceState,
    { label: string; icon: React.ReactNode; bg: string; color: string; border: string }
  > = {
    VERIFIED: {
      label: 'Verified Evidence',
      icon: <CheckCircle2 size={13} />,
      bg: '#ECFDF5',
      color: '#047857',
      border: '#A7F3D0',
    },
    SUPPORTED: {
      label: 'Supported',
      icon: <ShieldCheck size={13} />,
      bg: '#EFF6FF',
      color: '#1D4ED8',
      border: '#BFDBFE',
    },
    EMPIRICAL: {
      label: 'Empirical Baseline',
      icon: <Database size={13} />,
      bg: '#F0FDFA',
      color: '#0F766E',
      border: '#99F6E4',
    },
    MODEL_ESTIMATE: {
      label: 'Model Estimate',
      icon: <Cpu size={13} />,
      bg: '#F8FAFC',
      color: '#334155',
      border: '#CBD5E1',
    },
    USER_STATED: {
      label: 'User Stated',
      icon: <User size={13} />,
      bg: '#FFFBEB',
      color: '#B45309',
      border: '#FDE68A',
    },
    INSUFFICIENT_DATA: {
      label: 'Insufficient Data',
      icon: <AlertCircle size={13} />,
      bg: '#F1F5F9',
      color: '#64748B',
      border: '#CBD5E1',
    },
    UNVERIFIED: {
      label: 'Unverified Claim',
      icon: <HelpCircle size={13} />,
      bg: '#F1F5F9',
      color: '#475569',
      border: '#E2E8F0',
    },
    DEPRECATED: {
      label: 'Deprecated',
      icon: <AlertCircle size={13} />,
      bg: '#FEF2F2',
      color: '#B91C1C',
      border: '#FECACA',
    },
  };

  const current = config[normState] || config.UNVERIFIED;

  const fontSizes = {
    sm: 'var(--font-size-xs)',
    md: 'var(--font-size-sm)',
  };

  const paddings = {
    sm: '0.15rem 0.45rem',
    md: '0.25rem 0.65rem',
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
        borderRadius: 'var(--radius-md)',
        fontSize: fontSizes[size],
        padding: paddings[size],
        fontWeight: 'var(--font-weight-medium)',
        lineHeight: 1.2,
      }}
      className={`evidence-badge evidence-${normState.toLowerCase()} ${className}`}
      title={`Provenance Status: ${current.label}`}
    >
      {showIcon && <span aria-hidden="true">{current.icon}</span>}
      <span>{current.label}</span>
    </span>
  );
};
