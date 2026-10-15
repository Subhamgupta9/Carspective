import React, { useEffect } from 'react';
import { CheckCircle2, AlertCircle, Info, X } from 'lucide-react';

export interface ToastProps {
  id: string;
  type?: 'success' | 'error' | 'info';
  message: string;
  onDismiss: (id: string) => void;
  duration?: number;
}

export const Toast: React.FC<ToastProps> = ({
  id,
  type = 'info',
  message,
  onDismiss,
  duration = 4000,
}) => {
  useEffect(() => {
    const timer = setTimeout(() => onDismiss(id), duration);
    return () => clearTimeout(timer);
  }, [id, duration, onDismiss]);

  const icons = {
    success: <CheckCircle2 size={16} color="var(--status-pass)" />,
    error: <AlertCircle size={16} color="var(--status-fail)" />,
    info: <Info size={16} color="var(--accent-blue)" />,
  };

  return (
    <div
      role="status"
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 'var(--space-3)',
        backgroundColor: 'var(--bg-primary)',
        border: '1px solid var(--border-medium)',
        boxShadow: 'var(--shadow-lg)',
        borderRadius: 'var(--radius-lg)',
        padding: 'var(--space-3) var(--space-4)',
        minWidth: '280px',
        maxWidth: '400px',
        animation: 'slideUp 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
      }}
    >
      {icons[type]}
      <span style={{ flex: 1, fontSize: 'var(--font-size-sm)', color: 'var(--text-primary)' }}>
        {message}
      </span>
      <button
        onClick={() => onDismiss(id)}
        aria-label="Dismiss toast"
        style={{ color: 'var(--text-muted)', cursor: 'pointer', display: 'flex' }}
      >
        <X size={14} />
      </button>
    </div>
  );
};
