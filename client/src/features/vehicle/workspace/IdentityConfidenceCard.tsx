import React from 'react';
import { IdentityConfidenceInfo, SiblingVariantInfo, SiblingGenInfo } from '../../../types';
import { Badge } from '../../../components/common/Badge';
import { CheckCircle2, AlertCircle, Info, Layers, ChevronRight } from 'lucide-react';

export interface IdentityConfidenceCardProps {
  confidence: IdentityConfidenceInfo;
  onSelectCanonicalVehicle?: (canonicalId: string) => void;
}

export const IdentityConfidenceCard: React.FC<IdentityConfidenceCardProps> = ({
  confidence,
  onSelectCanonicalVehicle,
}) => {
  const getBadgeProps = () => {
    switch (confidence.level) {
      case 'exact':
        return {
          variant: 'success' as const,
          icon: <CheckCircle2 size={16} />,
          label: 'Exact Canonical Identity',
          bg: 'rgba(56, 161, 105, 0.04)',
          border: 'rgba(56, 161, 105, 0.25)',
        };
      case 'resolved':
        return {
          variant: 'info' as const,
          icon: <Info size={16} />,
          label: 'Resolved Baseline Specification',
          bg: 'rgba(49, 130, 206, 0.04)',
          border: 'rgba(49, 130, 206, 0.25)',
        };
      case 'ambiguous':
        return {
          variant: 'warning' as const,
          icon: <AlertCircle size={16} />,
          label: 'Ambiguous — Confirmation Required',
          bg: 'rgba(214, 158, 46, 0.06)',
          border: 'rgba(214, 158, 46, 0.35)',
        };
      case 'limited':
      default:
        return {
          variant: 'neutral' as const,
          icon: <Info size={16} />,
          label: 'Limited Historical Records',
          bg: 'rgba(113, 128, 150, 0.04)',
          border: 'rgba(113, 128, 150, 0.25)',
        };
    }
  };

  const badgeProps = getBadgeProps();

  return (
    <div
      style={{
        borderRadius: 'var(--radius-lg)',
        backgroundColor: badgeProps.bg,
        border: `1px solid ${badgeProps.border}`,
        padding: 'var(--space-4) var(--space-5)',
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-3)',
      }}
    >
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: 'var(--space-2)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
          <span style={{ color: `var(--color-${badgeProps.variant})` }}>{badgeProps.icon}</span>
          <span style={{ fontWeight: 'var(--font-weight-bold)', fontSize: 'var(--font-size-sm)', color: 'var(--text-primary)' }}>
            {confidence.title}
          </span>
          <Badge variant={badgeProps.variant} size="sm">
            {badgeProps.label}
          </Badge>
        </div>

        {confidence.needs_user_confirmation && (
          <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 'var(--font-weight-semibold)', color: 'var(--color-warning)' }}>
            Select your exact trim below to confirm
          </span>
        )}
      </div>

      <p style={{ margin: 0, fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
        {confidence.description}
      </p>

      {/* Sibling Generations (if model has multiple generations) */}
      {confidence.sibling_generations && confidence.sibling_generations.length > 1 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)', marginTop: 'var(--space-1)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-1)', fontSize: '11px', color: 'var(--text-muted)' }}>
            <Layers size={13} />
            <span>Select Generation:</span>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
            {confidence.sibling_generations.map((g) => (
              <button
                key={g.slug}
                onClick={() => onSelectCanonicalVehicle && onSelectCanonicalVehicle(g.canonical_id)}
                style={{
                  padding: 'var(--space-1) var(--space-3)',
                  borderRadius: 'var(--radius-full)',
                  border: g.is_current ? '1.5px solid var(--accent-blue)' : '1px solid var(--border-medium)',
                  backgroundColor: g.is_current ? 'var(--accent-blue)' : 'var(--bg-primary)',
                  color: g.is_current ? '#FFFFFF' : 'var(--text-secondary)',
                  fontSize: 'var(--font-size-xs)',
                  fontWeight: g.is_current ? 'var(--font-weight-bold)' : 'var(--font-weight-normal)',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                }}
              >
                {g.name} ({g.year_start}{g.year_end ? `–${g.year_end}` : '+'})
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Sibling Trim Variants (Trim Switcher) */}
      {confidence.sibling_variants && confidence.sibling_variants.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)', marginTop: 'var(--space-1)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-1)', fontSize: '11px', color: 'var(--text-muted)' }}>
            <span>Available Trims in this Generation:</span>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
            {confidence.sibling_variants.map((v) => (
              <button
                key={v.slug}
                onClick={() => onSelectCanonicalVehicle && onSelectCanonicalVehicle(v.canonical_id)}
                style={{
                  padding: 'var(--space-1) var(--space-3)',
                  borderRadius: 'var(--radius-full)',
                  border: v.is_current ? '1.5px solid var(--color-primary)' : '1px solid var(--border-medium)',
                  backgroundColor: v.is_current ? 'var(--color-primary)' : 'var(--bg-primary)',
                  color: v.is_current ? '#FFFFFF' : 'var(--text-secondary)',
                  fontSize: 'var(--font-size-xs)',
                  fontWeight: v.is_current ? 'var(--font-weight-bold)' : 'var(--font-weight-normal)',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 'var(--space-1)',
                }}
              >
                <span>{v.name}</span>
                {v.powertrains.length > 0 && (
                  <span style={{ opacity: 0.75, fontSize: '10px' }}>
                    ({v.powertrains[0]})
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
