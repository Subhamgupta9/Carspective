import React from 'react';
import { WorkspaceInspectionSummary } from '../../../types';
import { Badge } from '../../../components/common/Badge';
import { Button } from '../../../components/common/Button';
import { ClipboardCheck, ShieldAlert, FileText, ArrowRight, CheckCircle2 } from 'lucide-react';

export interface InspectionCalloutSectionProps {
  summary: WorkspaceInspectionSummary;
  onOpenChecklist: () => void;
}

export const InspectionCalloutSection: React.FC<InspectionCalloutSectionProps> = ({
  summary,
  onOpenChecklist,
}) => {
  const getReadinessVariant = (readiness: string) => {
    switch (readiness) {
      case 'READY_FOR_NEXT_STEP':
        return 'success';
      case 'VERIFY_BEFORE_NEGOTIATING':
        return 'warning';
      case 'HIGH_RISK_DO_NOT_PROCEED_YET':
        return 'danger';
      case 'INSUFFICIENT_EVIDENCE':
      default:
        return 'info';
    }
  };

  return (
    <div
      style={{
        borderRadius: 'var(--radius-xl)',
        backgroundColor: 'var(--bg-secondary)',
        border: '1px solid var(--border-medium)',
        padding: 'var(--space-6)',
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-5)',
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            <ClipboardCheck size={20} style={{ color: 'var(--color-primary)' }} />
            <h3 style={{ margin: 0, fontSize: 'var(--font-size-xl)' }}>
              Pre-Purchase Physical Inspection Intelligence
            </h3>
          </div>
          <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
            Phase 7 Adaptive Inspection Protocol ({summary.total_applicable_items} items calibrated for this vehicle)
          </span>
        </div>

        <Badge variant={getReadinessVariant(summary.purchase_readiness)} size="md">
          Readiness: {summary.purchase_readiness.replace(/_/g, ' ')}
        </Badge>
      </div>

      {/* Overview Cards */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: 'var(--space-4)',
        }}
      >
        {/* Watchpoints */}
        <div
          style={{
            padding: 'var(--space-4)',
            backgroundColor: 'var(--bg-primary)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--border-subtle)',
            display: 'flex',
            flexDirection: 'column',
            gap: 'var(--space-2)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', color: 'var(--color-warning)', fontWeight: 'var(--font-weight-semibold)', fontSize: 'var(--font-size-sm)' }}>
            <ShieldAlert size={16} />
            <span>High-Priority Mechanical Watchpoints</span>
          </div>
          <ul style={{ margin: 0, paddingLeft: 'var(--space-4)', fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: 'var(--space-1)' }}>
            {summary.top_watchpoints.map((wp, idx) => (
              <li key={idx}>{wp}</li>
            ))}
          </ul>
        </div>

        {/* Documentation Requirements */}
        <div
          style={{
            padding: 'var(--space-4)',
            backgroundColor: 'var(--bg-primary)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--border-subtle)',
            display: 'flex',
            flexDirection: 'column',
            gap: 'var(--space-2)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', color: 'var(--accent-blue)', fontWeight: 'var(--font-weight-semibold)', fontSize: 'var(--font-size-sm)' }}>
            <FileText size={16} />
            <span>Mandatory Document Verifications</span>
          </div>
          <ul style={{ margin: 0, paddingLeft: 'var(--space-4)', fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: 'var(--space-1)' }}>
            {summary.documentation_requirements.map((doc, idx) => (
              <li key={idx}>{doc}</li>
            ))}
          </ul>
        </div>
      </div>

      {/* Action Footer */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 'var(--space-3)',
          paddingTop: 'var(--space-2)',
          borderTop: '1px solid var(--border-subtle)',
        }}
      >
        <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
          This checklist supports decision-making and does not replace a professional inspection.
        </span>

        <Button
          variant="primary"
          size="md"
          leftIcon={<ClipboardCheck size={16} />}
          rightIcon={<ArrowRight size={16} />}
          onClick={onOpenChecklist}
        >
          Open Full Interactive Checklist ({summary.total_applicable_items} items)
        </Button>
      </div>
    </div>
  );
};
