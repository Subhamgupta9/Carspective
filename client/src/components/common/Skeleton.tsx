import React from 'react';

export interface SkeletonProps {
  width?: string | number;
  height?: string | number;
  borderRadius?: string;
  className?: string;
  style?: React.CSSProperties;
}

export const Skeleton: React.FC<SkeletonProps> = ({
  width = '100%',
  height = '1rem',
  borderRadius = 'var(--radius-md)',
  className = '',
  style,
}) => {
  return (
    <div
      style={{
        width,
        height,
        borderRadius,
        backgroundColor: 'var(--border-subtle)',
        opacity: 0.7,
        animation: 'pulse 1.5s ease-in-out infinite',
        ...style,
      }}
      className={`skeleton-loader ${className}`}
      aria-hidden="true"
    />
  );
};
