import React from 'react';

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'neutral' | 'info' | 'success' | 'warning' | 'danger';
  size?: 'sm' | 'md';
  icon?: React.ReactNode;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'default',
  size = 'md',
  icon,
  className = '',
  style,
  ...props
}) => {
  const variantMap: Record<string, React.CSSProperties> = {
    default: {
      backgroundColor: 'var(--bg-tertiary)',
      color: 'var(--text-secondary)',
      border: '1px solid var(--border-subtle)',
    },
    neutral: {
      backgroundColor: 'var(--bg-tertiary)',
      color: 'var(--text-muted)',
      border: '1px solid var(--border-subtle)',
    },
    info: {
      backgroundColor: 'var(--accent-blue-light)',
      color: 'var(--accent-blue)',
      border: '1px solid rgba(0, 102, 255, 0.2)',
    },
    success: {
      backgroundColor: 'var(--status-pass-bg)',
      color: 'var(--status-pass)',
      border: '1px solid var(--status-pass-border)',
    },
    warning: {
      backgroundColor: 'var(--status-attention-bg)',
      color: 'var(--status-attention)',
      border: '1px solid var(--status-attention-border)',
    },
    danger: {
      backgroundColor: 'var(--status-fail-bg)',
      color: 'var(--status-fail)',
      border: '1px solid var(--status-fail-border)',
    },
  };

  const sizeMap: Record<string, React.CSSProperties> = {
    sm: {
      padding: '0.15rem 0.5rem',
      fontSize: 'var(--font-size-xs)',
      borderRadius: 'var(--radius-sm)',
    },
    md: {
      padding: '0.25rem 0.65rem',
      fontSize: 'var(--font-size-sm)',
      borderRadius: 'var(--radius-md)',
    },
  };

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 'var(--space-1)',
        fontWeight: 'var(--font-weight-medium)',
        lineHeight: 1.2,
        whiteSpace: 'nowrap',
        ...sizeMap[size],
        ...variantMap[variant],
        ...style,
      }}
      className={`badge badge-${variant} ${className}`}
      {...props}
    >
      {icon && <span style={{ display: 'inline-flex', fontSize: '0.9em' }}>{icon}</span>}
      <span>{children}</span>
    </span>
  );
};
