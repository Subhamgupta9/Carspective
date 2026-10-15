import React from 'react';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Input: React.FC<InputProps> = ({
  label,
  error,
  helperText,
  leftIcon,
  rightIcon,
  id,
  className = '',
  style,
  ...props
}) => {
  const inputId = id || (label ? `input-${label.toLowerCase().replace(/\s+/g, '-')}` : undefined);
  const errorId = inputId && error ? `${inputId}-error` : undefined;
  const helperId = inputId && helperText ? `${inputId}-helper` : undefined;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-1)', width: '100%', ...style }}>
      {label && (
        <label
          htmlFor={inputId}
          style={{
            fontSize: 'var(--font-size-sm)',
            fontWeight: 'var(--font-weight-medium)',
            color: 'var(--text-secondary)',
          }}
        >
          {label}
        </label>
      )}

      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          backgroundColor: 'var(--bg-primary)',
          border: `1px solid ${error ? 'var(--status-fail)' : 'var(--border-medium)'}`,
          borderRadius: 'var(--radius-lg)',
          padding: '0 var(--space-3)',
          transition: 'border-color var(--transition-fast), box-shadow var(--transition-fast)',
        }}
      >
        {leftIcon && <span style={{ marginRight: 'var(--space-2)', color: 'var(--text-muted)' }}>{leftIcon}</span>}
        <input
          id={inputId}
          aria-invalid={Boolean(error)}
          aria-describedby={[errorId, helperId].filter(Boolean).join(' ') || undefined}
          style={{
            flex: 1,
            border: 'none',
            outline: 'none',
            padding: 'var(--space-2) 0',
            fontSize: 'var(--font-size-base)',
            fontFamily: 'inherit',
            color: 'var(--text-primary)',
            background: 'transparent',
          }}
          className={className}
          {...props}
        />
        {rightIcon && <span style={{ marginLeft: 'var(--space-2)', color: 'var(--text-muted)' }}>{rightIcon}</span>}
      </div>

      {error ? (
        <span
          id={errorId}
          role="alert"
          style={{
            fontSize: 'var(--font-size-xs)',
            color: 'var(--status-fail)',
            fontWeight: 'var(--font-weight-medium)',
          }}
        >
          {error}
        </span>
      ) : helperText ? (
        <span
          id={helperId}
          style={{
            fontSize: 'var(--font-size-xs)',
            color: 'var(--text-muted)',
          }}
        >
          {helperText}
        </span>
      ) : null}
    </div>
  );
};
