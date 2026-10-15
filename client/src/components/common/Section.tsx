import React from 'react';

export interface SectionProps extends React.HTMLAttributes<HTMLElement> {
  title?: string;
  subtitle?: string;
  action?: React.ReactNode;
}

export const Section: React.FC<SectionProps> = ({
  title,
  subtitle,
  action,
  children,
  className = '',
  style,
  ...props
}) => {
  return (
    <section
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-4)',
        marginTop: 'var(--space-8)',
        marginBottom: 'var(--space-8)',
        ...style,
      }}
      className={`carspective-section ${className}`}
      {...props}
    >
      {(title || action) && (
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'flex-end',
            justifyContent: 'space-between',
            gap: 'var(--space-3)',
            borderBottom: '1px solid var(--border-light)',
            paddingBottom: 'var(--space-3)',
          }}
        >
          <div>
            {title && <h3 style={{ fontSize: 'var(--font-size-2xl)', margin: 0 }}>{title}</h3>}
            {subtitle && (
              <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-muted)', margin: 'var(--space-1) 0 0 0' }}>
                {subtitle}
              </p>
            )}
          </div>
          {action && <div>{action}</div>}
        </div>
      )}
      {children}
    </section>
  );
};
