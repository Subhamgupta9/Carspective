import React from 'react';
import { DecisionEvaluationResponse, PersonalizedAlternative } from '../../types';
import {
  CheckCircle,
  AlertTriangle,
  XCircle,
  Sparkles,
  HelpCircle,
  ArrowRight,
  ShieldAlert,
  Scale,
  Check,
  X,
  SearchCheck,
} from 'lucide-react';

export interface PersonalizedDecisionCardProps {
  decision: DecisionEvaluationResponse;
  onSelectAlternative?: (alt: PersonalizedAlternative) => void;
  onEditRequirements?: () => void;
}

export const PersonalizedDecisionCard: React.FC<PersonalizedDecisionCardProps> = ({
  decision,
  onSelectAlternative,
  onEditRequirements,
}) => {
  const isConstraintFail = decision.hard_constraint_status === 'FAIL';

  const getVerdictStyle = () => {
    if (isConstraintFail) {
      return {
        bg: '#fef2f2',
        border: '#f87171',
        text: '#991b1b',
        icon: <XCircle size={22} color="#dc2626" />,
      };
    }
    if (decision.user_fit_score >= 80) {
      return {
        bg: '#f0fdf4',
        border: '#86efac',
        text: '#166534',
        icon: <CheckCircle size={22} color="#16a34a" />,
      };
    }
    if (decision.user_fit_score >= 65) {
      return {
        bg: '#eff6ff',
        border: '#93c5fd',
        text: '#1e40af',
        icon: <CheckCircle size={22} color="#2563eb" />,
      };
    }
    return {
      bg: '#fffbeb',
      border: '#fde68a',
      text: '#92400e',
      icon: <AlertTriangle size={22} color="#d97706" />,
    };
  };

  const verdictStyle = getVerdictStyle();

  return (
    <div
      style={{
        background: 'var(--bg-surface, #ffffff)',
        border: `1px solid ${verdictStyle.border}`,
        borderRadius: 'var(--radius-lg, 12px)',
        overflow: 'hidden',
        boxShadow: 'var(--shadow-md, 0 4px 6px -1px rgba(0,0,0,0.1))',
        marginBottom: 'var(--space-6, 24px)',
      }}
      data-testid="personalized-decision-card"
    >
      {/* Header Banner */}
      <div
        style={{
          background: verdictStyle.bg,
          padding: '16px 20px',
          borderBottom: `1px solid ${verdictStyle.border}`,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '12px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {verdictStyle.icon}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span
                style={{
                  fontSize: '0.8rem',
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                  color: verdictStyle.text,
                }}
              >
                {decision.recommendation_verdict}
              </span>
              <span
                style={{
                  fontSize: '0.75rem',
                  padding: '2px 8px',
                  borderRadius: '12px',
                  background: decision.decision_quality === 'HIGH' ? '#dcfce7' : '#fef9c3',
                  color: decision.decision_quality === 'HIGH' ? '#15803d' : '#854d0e',
                  fontWeight: 600,
                }}
              >
                Quality: {decision.decision_quality}
              </span>
            </div>
            <h4 style={{ margin: '2px 0 0', fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-primary, #0f172a)' }}>
              {decision.verdict_label}
            </h4>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
          <div style={{ textAlign: 'right' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted, #64748b)', display: 'block' }}>
              Personalized User Fit
            </span>
            <span
              style={{
                fontSize: '1.8rem',
                fontWeight: 800,
                color: isConstraintFail ? '#dc2626' : verdictStyle.text,
              }}
            >
              {decision.user_fit_score}
              <span style={{ fontSize: '1rem', fontWeight: 500, color: '#94a3b8' }}>/100</span>
            </span>
          </div>
          {onEditRequirements && (
            <button
              onClick={onEditRequirements}
              style={{
                padding: '6px 12px',
                borderRadius: '6px',
                border: '1px solid var(--border-default, #cbd5e1)',
                background: '#ffffff',
                fontSize: '0.85rem',
                fontWeight: 500,
                cursor: 'pointer',
              }}
            >
              Adjust Profile
            </button>
          )}
        </div>
      </div>

      <div style={{ padding: '20px' }}>
        {/* Layer Distinction: Vehicle Fit vs Deal Fit vs Intrinsic */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: '12px',
            marginBottom: '20px',
            background: 'var(--bg-subtle, #f8fafc)',
            padding: '12px 16px',
            borderRadius: '8px',
            border: '1px solid var(--border-subtle, #e2e8f0)',
          }}
        >
          <div>
            <span style={{ fontSize: '0.75rem', color: '#64748b', display: 'block' }}>Vehicle Fit (Suitability)</span>
            <span style={{ fontSize: '1.1rem', fontWeight: 700, color: '#1e293b' }}>
              {decision.vehicle_fit_score}/100
            </span>
            <span style={{ fontSize: '0.7rem', color: '#94a3b8', display: 'block' }}>Matches your usage & priorities</span>
          </div>

          <div>
            <span style={{ fontSize: '0.75rem', color: '#64748b', display: 'block' }}>Intrinsic Vehicle Truth</span>
            <span style={{ fontSize: '1.1rem', fontWeight: 700, color: '#1e293b' }}>
              {decision.intrinsic_score ? `${decision.intrinsic_score}/100` : 'N/A'}
            </span>
            <span style={{ fontSize: '0.7rem', color: '#94a3b8', display: 'block' }}>Platform engineering merit</span>
          </div>

          {decision.deal_fit_score !== null && decision.deal_fit_score !== undefined && (
            <div>
              <span style={{ fontSize: '0.75rem', color: '#64748b', display: 'block' }}>Deal Fit (Asking Price)</span>
              <span style={{ fontSize: '1.1rem', fontWeight: 700, color: '#1e293b' }}>
                {decision.deal_fit_score}/100
              </span>
              <span style={{ fontSize: '0.7rem', color: '#94a3b8', display: 'block' }}>Price vs fair market range</span>
            </div>
          )}
        </div>

        {/* Hard Constraint Failure Alert if any */}
        {isConstraintFail && (
          <div
            style={{
              padding: '12px 16px',
              background: '#fef2f2',
              border: '1px solid #fca5a5',
              borderRadius: '8px',
              marginBottom: '16px',
              color: '#991b1b',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 600, fontSize: '0.9rem' }}>
              <ShieldAlert size={18} /> Hard Constraint Violation
            </div>
            <ul style={{ margin: '6px 0 0', paddingLeft: '20px', fontSize: '0.85rem' }}>
              {decision.why_it_may_not_fit.map((fail, i) => (
                <li key={i}>{fail}</li>
              ))}
            </ul>
          </div>
        )}

        {/* 3-Part Section 10 Explanation: Matches your needs, Doesn't fully match, Missing information */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '20px' }}>
          {/* Matches your needs */}
          <div>
            <h5
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                margin: '0 0 10px',
                fontSize: '0.95rem',
                color: '#166534',
                fontWeight: 600,
              }}
            >
              <Check size={16} /> Matches your needs
            </h5>
            <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '0.85rem', color: '#334155', lineHeight: 1.6 }}>
              {decision.why_it_fits.map((reason, i) => (
                <li key={i} style={{ marginBottom: '6px' }}>
                  {reason}
                </li>
              ))}
            </ul>
          </div>

          {/* Doesn't fully match */}
          <div>
            <h5
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                margin: '0 0 10px',
                fontSize: '0.95rem',
                color: '#854d0e',
                fontWeight: 600,
              }}
            >
              <Scale size={16} /> Doesn&apos;t fully match
            </h5>
            <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '0.85rem', color: '#334155', lineHeight: 1.6 }}>
              {decision.tradeoffs.slice(0, 5).map((t, i) => (
                <li key={i} style={{ marginBottom: '6px' }}>
                  {t}
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Missing information (Section 10) */}
        <div
          style={{
            marginTop: '16px',
            padding: '12px 16px',
            backgroundColor: '#f8fafc',
            borderRadius: '8px',
            border: '1px solid #e2e8f0',
            fontSize: '0.85rem',
            color: '#64748b',
          }}
        >
          <div style={{ fontWeight: 600, color: '#334155', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <HelpCircle size={15} color="#64748b" /> Missing information
          </div>
          {decision.limitations && decision.limitations.length > 0 ? (
            <ul style={{ margin: 0, paddingLeft: '18px', lineHeight: 1.5 }}>
              {decision.limitations.map((lim, i) => (
                <li key={i}>{lim}</li>
              ))}
            </ul>
          ) : (
            <div>
              Preferences not explicitly configured use conservative deterministic defaults. You can specify annual mileage, body type, or budget ceiling anytime.
            </div>
          )}
        </div>

        {/* What To Verify Before Buying */}
        {decision.what_to_verify_before_buying && decision.what_to_verify_before_buying.length > 0 && (
          <div
            style={{
              marginTop: '20px',
              padding: '14px 16px',
              background: '#f8fafc',
              borderRadius: '8px',
              border: '1px solid #e2e8f0',
            }}
          >
            <h5
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                margin: '0 0 8px',
                fontSize: '0.9rem',
                color: '#0f172a',
                fontWeight: 600,
              }}
            >
              <SearchCheck size={16} color="#2563eb" /> Prioritized Verification For Your Profile
            </h5>
            <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '0.85rem', color: '#475569', lineHeight: 1.5 }}>
              {decision.what_to_verify_before_buying.map((check, i) => (
                <li key={i}>{check}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Personalized Alternatives */}
        {decision.alternatives && decision.alternatives.length > 0 && (
          <div style={{ marginTop: '20px' }}>
            <h5 style={{ margin: '0 0 10px', fontSize: '0.95rem', fontWeight: 600, color: '#1e293b' }}>
              Alternative Vehicles Tailored To Your Needs
            </h5>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '12px' }}>
              {decision.alternatives.map((alt) => (
                <div
                  key={alt.canonical_vehicle_id}
                  style={{
                    padding: '12px',
                    borderRadius: '8px',
                    border: '1px solid #e2e8f0',
                    background: '#ffffff',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                  }}
                >
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontWeight: 600, fontSize: '0.95rem', color: '#0f172a' }}>
                        {alt.vehicle_summary}
                      </span>
                      <span
                        style={{
                          fontSize: '0.75rem',
                          padding: '2px 6px',
                          borderRadius: '4px',
                          background: '#eff6ff',
                          color: '#1d4ed8',
                          fontWeight: 600,
                        }}
                      >
                        {alt.user_fit_score}/100 Fit
                      </span>
                    </div>
                    <p style={{ margin: '6px 0 2px', fontSize: '0.8rem', color: '#16a34a' }}>
                      ✓ {alt.advantage_over_target}
                    </p>
                    <p style={{ margin: '2px 0 8px', fontSize: '0.8rem', color: '#d97706' }}>
                      ⚠ {alt.tradeoff_vs_target}
                    </p>
                  </div>
                  {onSelectAlternative && (
                    <button
                      onClick={() => onSelectAlternative(alt)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '6px',
                        padding: '6px 12px',
                        borderRadius: '6px',
                        border: '1px solid #cbd5e1',
                        background: '#f8fafc',
                        color: '#1e293b',
                        fontSize: '0.8rem',
                        fontWeight: 500,
                        cursor: 'pointer',
                      }}
                    >
                      Compare This Alternative <ArrowRight size={14} />
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
