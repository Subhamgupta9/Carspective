import React, { useState } from 'react';
import { InspectionEvaluationResponse, InspectionChecklistItem, InspectionStatus } from '../../types';
import { StatusBadge } from '../../components/common/StatusBadge';
import { EvidenceBadge } from '../../components/common/EvidenceBadge';
import { Badge } from '../../components/common/Badge';
import {
  ClipboardCheck,
  AlertOctagon,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  ShieldAlert,
  HelpCircle,
  FileText,
  Car,
  Wrench,
  Compass,
} from 'lucide-react';

export interface InspectionChecklistProps {
  inspection?: InspectionEvaluationResponse | null;
  onItemStatusChange?: (itemId: string, newStatus: InspectionStatus) => void;
  isLoading?: boolean;
}

export const InspectionChecklist: React.FC<InspectionChecklistProps> = ({
  inspection,
  onItemStatusChange,
  isLoading,
}) => {
  const [expandedCategories, setExpandedCategories] = useState<Record<string, boolean>>({
    Documentation: true,
    'Engine & Powertrain': true,
    'Underbody & Structure': true,
  });

  if (isLoading) {
    return (
      <div style={{ padding: 'var(--space-8)', textAlign: 'center' }}>
        <p style={{ color: 'var(--text-muted)' }}>Generating adaptive inspection checklist & risk analysis...</p>
      </div>
    );
  }

  if (!inspection) return null;

  const toggleCategory = (cat: string) => {
    setExpandedCategories(prev => ({ ...prev, [cat]: !prev[cat] }));
  };

  const getReadinessConfig = (readiness: string) => {
    switch (readiness) {
      case 'READY_FOR_NEXT_STEP':
        return {
          label: 'Ready for Next Step',
          badgeVariant: 'success' as const,
          color: 'var(--status-pass)',
          bg: 'var(--status-pass-bg)',
          desc: 'Essential documentation and baseline inspection checks passed.',
        };
      case 'VERIFY_BEFORE_NEGOTIATING':
        return {
          label: 'Verify Before Negotiating',
          badgeVariant: 'warning' as const,
          color: 'var(--status-attention)',
          bg: 'var(--status-attention-bg)',
          desc: 'Attention items or pending verifications must be clarified with seller first.',
        };
      case 'PROFESSIONAL_INSPECTION_RECOMMENDED':
        return {
          label: 'Professional Inspection Recommended',
          badgeVariant: 'danger' as const,
          color: 'var(--status-fail)',
          bg: 'var(--status-fail-bg)',
          desc: 'Structural, mechanical, or safety risk signals indicate need for certified mechanic check.',
        };
      case 'INSUFFICIENT_EVIDENCE':
      default:
        return {
          label: 'Insufficient Evidence',
          badgeVariant: 'neutral' as const,
          color: 'var(--text-muted)',
          bg: 'var(--bg-tertiary)',
          desc: 'Multiple critical inspection checkpoints remain unverified/unknown.',
        };
    }
  };

  const rConfig = getReadinessConfig(inspection.purchase_readiness);

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-6)',
        backgroundColor: 'var(--bg-primary)',
        borderRadius: 'var(--radius-xl)',
        border: '1px solid var(--border-subtle)',
        padding: 'var(--space-6)',
        boxShadow: 'var(--shadow-sm)',
      }}
    >
      {/* Header & Purchase Readiness Banner */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: 'var(--space-4)',
          borderBottom: '1px solid var(--border-light)',
          paddingBottom: 'var(--space-5)',
        }}
      >
        <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: 'var(--space-3)' }}>
          <div>
            <h3 style={{ fontSize: 'var(--font-size-2xl)', margin: 0 }}>Inspection Intelligence</h3>
            <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-muted)', margin: 'var(--space-1) 0 0 0' }}>
              Adaptive inspection checklist tailored to powertrain, fuel type, and age.
            </p>
          </div>

          <Badge variant={rConfig.badgeVariant} size="md">
            {rConfig.label}
          </Badge>
        </div>

        {/* Readiness Alert Bar */}
        <div
          style={{
            backgroundColor: rConfig.bg,
            borderRadius: 'var(--radius-lg)',
            padding: 'var(--space-4)',
            display: 'flex',
            alignItems: 'flex-start',
            gap: 'var(--space-3)',
          }}
        >
          {inspection.professional_inspection_recommended ? (
            <AlertOctagon size={20} color="var(--status-fail)" style={{ flexShrink: 0, marginTop: '2px' }} />
          ) : (
            <ClipboardCheck size={20} color={rConfig.color} style={{ flexShrink: 0, marginTop: '2px' }} />
          )}
          <div>
            <div style={{ fontWeight: 'var(--font-weight-bold)', fontSize: 'var(--font-size-sm)', color: 'var(--text-primary)' }}>
              {inspection.readiness_summary || rConfig.desc}
            </div>
            <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)', marginTop: '2px' }}>
              <strong>Important Disclaimer:</strong> This checklist supports decision-making and does not replace a professional inspection. Physical verification of critical components by a certified mechanic is always recommended.
            </div>
          </div>
        </div>
      </div>

      {/* Critical & High-Risk Findings Warnings */}
      {(inspection.critical_findings?.length > 0 || inspection.high_risk_findings?.length > 0) && (
        <div
          style={{
            backgroundColor: 'var(--status-fail-bg)',
            border: '1px solid var(--status-fail-border)',
            borderRadius: 'var(--radius-lg)',
            padding: 'var(--space-4)',
            display: 'flex',
            flexDirection: 'column',
            gap: 'var(--space-2)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', color: 'var(--status-fail)' }}>
            <AlertOctagon size={18} />
            <h4 style={{ margin: 0, fontSize: 'var(--font-size-sm)', fontWeight: 'var(--font-weight-bold)' }}>
              Critical Risk Signals Detected
            </h4>
          </div>
          <ul style={{ margin: 0, paddingLeft: 'var(--space-4)', fontSize: 'var(--font-size-xs)', color: 'var(--text-primary)' }}>
            {inspection.critical_findings?.map((crit, i) => (
              <li key={`crit-${i}`}>
                <strong>CRITICAL:</strong> {crit}
              </li>
            ))}
            {inspection.high_risk_findings?.map((high, i) => (
              <li key={`high-${i}`}>
                <strong>HIGH RISK:</strong> {high}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Progress Tally Pills */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-3)', fontSize: 'var(--font-size-xs)' }}>
        <span style={{ backgroundColor: 'var(--status-pass-bg)', color: 'var(--status-pass)', padding: 'var(--space-1) var(--space-3)', borderRadius: 'var(--radius-full)', fontWeight: 'var(--font-weight-semibold)' }}>
          {inspection.pass_count} Passed
        </span>
        <span style={{ backgroundColor: 'var(--status-attention-bg)', color: 'var(--status-attention)', padding: 'var(--space-1) var(--space-3)', borderRadius: 'var(--radius-full)', fontWeight: 'var(--font-weight-semibold)' }}>
          {inspection.attention_count} Attention
        </span>
        <span style={{ backgroundColor: 'var(--status-fail-bg)', color: 'var(--status-fail)', padding: 'var(--space-1) var(--space-3)', borderRadius: 'var(--radius-full)', fontWeight: 'var(--font-weight-semibold)' }}>
          {inspection.fail_count} Failed
        </span>
        <span style={{ backgroundColor: 'var(--status-unknown-bg)', color: 'var(--status-unknown)', padding: 'var(--space-1) var(--space-3)', borderRadius: 'var(--radius-full)', fontWeight: 'var(--font-weight-semibold)' }}>
          {inspection.unknown_count} Unknown / Pending
        </span>
      </div>

      {/* Checklist Category Groups */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
        {inspection.categories.map(cat => {
          const isExpanded = expandedCategories[cat.category] ?? false;
          return (
            <div
              key={cat.category}
              style={{
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-lg)',
                overflow: 'hidden',
              }}
            >
              {/* Category Header Accordion */}
              <div
                onClick={() => toggleCategory(cat.category)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: 'var(--space-3) var(--space-4)',
                  backgroundColor: 'var(--bg-secondary)',
                  cursor: 'pointer',
                  userSelect: 'none',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
                  <span style={{ fontWeight: 'var(--font-weight-bold)', fontSize: 'var(--font-size-base)', color: 'var(--text-primary)' }}>
                    {cat.category}
                  </span>
                  <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
                    ({cat.items.length} items)
                  </span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
                  <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
                    {cat.fail_count > 0 && <StatusBadge status="FAIL" size="sm" />}
                    {cat.attention_count > 0 && <StatusBadge status="ATTENTION" size="sm" />}
                    {cat.unknown_count > 0 && <StatusBadge status="UNKNOWN" size="sm" />}
                    {cat.pass_count > 0 && <StatusBadge status="PASS" size="sm" />}
                  </div>
                  {isExpanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                </div>
              </div>

              {/* Items Table / Cards */}
              {isExpanded && (
                <div style={{ display: 'flex', flexDirection: 'column', padding: 'var(--space-2)' }}>
                  {cat.items.map(item => (
                    <div
                      key={item.item_id}
                      style={{
                        padding: 'var(--space-3) var(--space-4)',
                        borderBottom: '1px solid var(--border-light)',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: 'var(--space-2)',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 'var(--space-2)' }}>
                        <div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                            <span style={{ fontWeight: 'var(--font-weight-semibold)', fontSize: 'var(--font-size-sm)', color: 'var(--text-primary)' }}>
                              {item.title}
                            </span>
                            {item.importance === 'CRITICAL' && (
                              <Badge variant="danger" size="sm">
                                Critical
                              </Badge>
                            )}
                            <EvidenceBadge state={item.evidence_state} size="sm" />
                          </div>
                          <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)', marginTop: '2px' }}>
                            <strong>Why it matters:</strong> {item.what_to_look_for}
                          </div>
                        </div>

                        {/* Interactive Status Selector */}
                        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                          <StatusBadge status={item.status} size="sm" />
                          {onItemStatusChange && (
                            <select
                              value={item.status}
                              onChange={e => onItemStatusChange(item.item_id, e.target.value as InspectionStatus)}
                              aria-label={`Change status for ${item.title}`}
                              style={{
                                fontSize: 'var(--font-size-xs)',
                                padding: 'var(--space-1)',
                                borderRadius: 'var(--radius-sm)',
                                border: '1px solid var(--border-medium)',
                                backgroundColor: 'var(--bg-primary)',
                              }}
                            >
                              <option value="UNKNOWN">UNKNOWN</option>
                              <option value="PASS">PASS</option>
                              <option value="ATTENTION">ATTENTION</option>
                              <option value="FAIL">FAIL</option>
                              <option value="NOT_APPLICABLE">N/A</option>
                            </select>
                          )}
                        </div>
                      </div>

                      {/* Verification Action Box */}
                      <div
                        style={{
                          backgroundColor: 'var(--bg-tertiary)',
                          padding: 'var(--space-2) var(--space-3)',
                          borderRadius: 'var(--radius-md)',
                          fontSize: 'var(--font-size-xs)',
                          color: 'var(--text-secondary)',
                        }}
                      >
                        <strong>Verification Action:</strong> {item.verification_action}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
