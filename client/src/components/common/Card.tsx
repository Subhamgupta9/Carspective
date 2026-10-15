import React from 'react';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'flat' | 'elevated' | 'glass';
  padding?: 'none' | 'sm' | 'md' | 'lg';
  interactive?: boolean;
}

export const Card: React.FC<CardProps> = ({
  children,
  variant = 'default',
  padding = 'md',
  interactive = false,
  className = '',
  style,
  ...props
}) => {
  const paddingMap = {
    none: '0',
    sm: 'var(--space-3)',
    md: 'var(--space-5)',
    lg: 'var(--space-8)',
  };

  const variantStyles: Record<string, React.CSSProperties> = {
    default: {
      backgroundColor: 'var(--bg-primary)',
      border: '1px solid var(--border-subtle)',
      boxShadow: 'var(--shadow-sm)',
    },
    flat: {
      backgroundColor: 'var(--bg-secondary)',
      border: '1px solid var(--border-light)',
      boxShadow: 'none',
    },
    elevated: {
      backgroundColor: 'var(--bg-primary)',
      border: '1px solid var(--border-subtle)',
      boxShadow: 'var(--shadow-md)',
    },
    glass: {
      backgroundColor: 'rgba(255, 255, 255, 0.92)',
      backdropFilter: 'blur(12px)',
      border: '1px solid var(--border-subtle)',
      boxShadow: 'var(--shadow-sm)',
    },
  };

  return (
    <div
      style={{
        borderRadius: 'var(--radius-xl)',
        padding: paddingMap[padding],
        transition: 'all var(--transition-normal)',
        cursor: interactive ? 'pointer' : 'default',
        ...variantStyles[variant],
        ...(interactive
          ? {
              ':hover': {
                boxShadow: 'var(--shadow-lg)',
                borderColor: 'var(--border-medium)',
              },
            }
          : {}),
        ...style,
      }}
      className={`carspective-card ${interactive ? 'carspective-card-interactive' : ''} ${className}`}
      {...props}
    >
      {children}
    </div>
  );
};
