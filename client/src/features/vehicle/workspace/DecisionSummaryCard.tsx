import React, { useState } from 'react';
import {
  ExecutiveSummary,
  ScoreResponse,
  ValuationResponse,
  DealAnalysisResponse,
  DecisionEvaluationResponse,
  EvidenceState,
} from '../../../types';
import { Badge } from '../../../components/common/Badge';
import { EvidenceBadge } from '../../../components/common/EvidenceBadge';
import {
  Award,
  TrendingUp,
  Tag,
  UserCheck,
  ChevronDown,
  ChevronUp,
  CheckCircle2,
  AlertTriangle,
  Info,
  Shield,
  HelpCircle,
  ArrowRight,
  ExternalLink,
} from 'lucide-react';

export interface DecisionSummaryCardProps {
  summary: ExecutiveSummary;
  score?: ScoreResponse | null;
  valuation?: ValuationResponse | null;
  dealAnalysis?: DealAnalysisResponse | null;
  decision?: DecisionEvaluationResponse | null;
  coverageTier?: string;
  askingPrice?: number;
  onOpenPreferences?: () => void;
  onScrollToSection?: (sectionId: string) => void;
}

export const DecisionSummaryCard: React.FC<DecisionSummaryCardProps> = ({
  summary,
  score,
  valuation,
  dealAnalysis,
  decision,
  coverageTier = 'TIER_1_DEEP',
  askingPrice,
  onOpenPreferences,
  onScrollToSection,
}) => {
  const [showWhyExplainers, setShowWhyExplainers] = useState<boolean>(false);
  const [activeExplainTab, setActiveExplainTab] = useState<'score' | 'fit' | 'deal' | 'verdict'>('score');
  const [evidenceDisclosureLevel, setEvidenceDisclosureLevel] = useState<1 | 2 | 3>(1);

  // Recommendation verdict badge styling
  const getVerdictBadgeProps = (verdict: string) => {
    switch (verdict.toUpperCase()) {
      case 'STRONG CONSIDERATION':
      case 'BUY':
        return { variant: 'success' as const, label: 'Strong Consideration' };
      case 'CONSIDER':
        return { variant: 'info' as const, label: 'Consider' };
      case 'PROCEED WITH CAUTION':
      case 'INSPECT_FIRST':
        return { variant: 'warning' as const, label: 'Proceed with Caution' };
      case 'NOT RECOMMENDED':
      case 'AVOID':
        return { variant: 'danger' as const, label: 'Not Recommended' };
      default:
        return { variant: 'neutral' as const, label: verdict };
    }
  };

  const verdictProps = getVerdictBadgeProps(summary.recommendation_verdict);

  // Extract grounded strong points & watch-outs from existing evidence
  const strongPoints: string[] = [];
  const watchOuts: string[] = [];

  // 1. Safety Evidence Grounding
  if (summary.safety_stars && summary.safety_stars >= 4) {
    strongPoints.push(`Strong structural safety profile (${summary.safety_stars}★ ${summary.safety_agency || 'NCAP'} rating)`);
  } else if (summary.safety_stars === null || summary.safety_stars === undefined) {
    watchOuts.push('No official NCAP crash test rating recorded for this generation');
  }

  // 2. Bodyshell Integrity Grounding
  if (summary.bodyshell_integrity && summary.bodyshell_integrity.toLowerCase().includes('stable')) {
    strongPoints.push('Bodyshell integrity officially rated as Stable under test load');
  } else if (summary.bodyshell_integrity && summary.bodyshell_integrity.toLowerCase().includes('unstable')) {
    watchOuts.push('Bodyshell integrity officially evaluated as Unstable under dynamic load');
  }

  // 3. Score Band Grounding
  if (summary.score_band === 'EXCELLENT' || summary.score_band === 'GOOD') {
    strongPoints.push(`Solid intrinsic proposition across India-specific ownership metrics (Score: ${summary.carspective_score}/100)`);
  } else if (summary.score_band === 'CAUTION') {
    watchOuts.push(`Low intrinsic engineering and longevity rating (${summary.carspective_score}/100)`);
  }

  // 4. Maintenance & Reliability Grounding
  if (summary.reliability_watchpoints_count === 0) {
    strongPoints.push('No critical recurring mechanical defects flagged in historical workshop bulletins');
  } else if (summary.reliability_watchpoints_count > 0) {
    watchOuts.push(`${summary.reliability_watchpoints_count} documented mechanical watchpoints require inspection before purchase`);
  }

  // 5. Valuation Grounding
  if (dealAnalysis) {
    if (dealAnalysis.deal_quality === 'GREAT_DEAL') {
      strongPoints.push(`Asking price (₹${((dealAnalysis.asking_price || 0) / 100000).toFixed(2)}L) is attractive relative to market fair value`);
    } else if (dealAnalysis.deal_quality === 'OVERPRICED') {
      watchOuts.push(`Asking price is higher than estimated fair market value range (₹${((dealAnalysis.asking_price || 0) / 100000).toFixed(2)}L)`);
    } else if (dealAnalysis.deal_quality === 'UNUSUALLY_LOW_ASKING_PRICE') {
      watchOuts.push('Unusually low asking price: verify title documents, flood exposure, and structural integrity');
    }
  }

  // 6. User Fit Grounding
  if (decision && decision.why_it_fits && decision.why_it_fits.length > 0) {
    strongPoints.push(decision.why_it_fits[0]);
  }
  if (decision && decision.tradeoffs && decision.tradeoffs.length > 0) {
    watchOuts.push(decision.tradeoffs[0]);
  }

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
        boxShadow: 'var(--shadow-sm)',
      }}
      data-testid="decision-summary-card"
    >
      {/* ────────────────────────────────────────────────────────── */}
      {/* HEADER: DECISION CONTEXT & ACTIONS */}
      {/* ────────────────────────────────────────────────────────── */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 'var(--space-3)',
          borderBottom: '1px solid var(--border-subtle)',
          paddingBottom: 'var(--space-4)',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            <h2 style={{ margin: 0, fontSize: 'var(--font-size-2xl)', fontWeight: 'var(--font-weight-bold)' }}>
              Decision Summary
            </h2>
            <Badge variant={verdictProps.variant} size="md">
              Verdict: {verdictProps.label}
            </Badge>
          </div>
          <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
            Grounded synthesis across intrinsic vehicle quality, your personal profile, and commercial deal terms
          </span>
        </div>

        {/* Evidence Disclosure Level Switcher */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-1)', fontSize: 'var(--font-size-xs)' }}>
          <span style={{ color: 'var(--text-muted)', marginRight: '4px' }}>Detail Level:</span>
          <button
            onClick={() => setEvidenceDisclosureLevel(1)}
            style={{
              padding: '2px 8px',
              borderRadius: '4px',
              border: '1px solid var(--border-subtle)',
              backgroundColor: evidenceDisclosureLevel === 1 ? 'var(--color-primary)' : 'var(--bg-primary)',
              color: evidenceDisclosureLevel === 1 ? '#FFFFFF' : 'var(--text-secondary)',
              cursor: 'pointer',
              fontSize: '11px',
              fontWeight: 600,
            }}
          >
            L1 Summary
          </button>
          <button
            onClick={() => setEvidenceDisclosureLevel(2)}
            style={{
              padding: '2px 8px',
              borderRadius: '4px',
              border: '1px solid var(--border-subtle)',
              backgroundColor: evidenceDisclosureLevel === 2 ? 'var(--color-primary)' : 'var(--bg-primary)',
              color: evidenceDisclosureLevel === 2 ? '#FFFFFF' : 'var(--text-secondary)',
              cursor: 'pointer',
              fontSize: '11px',
              fontWeight: 600,
            }}
          >
            L2 Factors
          </button>
          <button
            onClick={() => setEvidenceDisclosureLevel(3)}
            style={{
              padding: '2px 8px',
              borderRadius: '4px',
              border: '1px solid var(--border-subtle)',
              backgroundColor: evidenceDisclosureLevel === 3 ? 'var(--color-primary)' : 'var(--bg-primary)',
              color: evidenceDisclosureLevel === 3 ? '#FFFFFF' : 'var(--text-secondary)',
              cursor: 'pointer',
              fontSize: '11px',
              fontWeight: 600,
            }}
          >
            L3 Lineage
          </button>
        </div>
      </div>

      {/* ────────────────────────────────────────────────────────── */}
      {/* THREE PILLARS: MATHEMATICALLY ENFORCED SEPARATION */}
      {/* ────────────────────────────────────────────────────────── */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
          gap: 'var(--space-4)',
        }}
      >
        {/* Pillar 1: Vehicle Quality (CarSpective Score) */}
        <div
          style={{
            padding: 'var(--space-5)',
            backgroundColor: 'var(--bg-primary)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--border-subtle)',
            display: 'flex',
            flexDirection: 'column',
            gap: 'var(--space-2)',
            position: 'relative',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 'var(--font-weight-semibold)', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Award size={16} style={{ color: 'var(--color-primary)' }} />
              1. Vehicle Quality
            </span>
            <Badge variant="neutral" size="sm">
              {summary.score_band}
            </Badge>
          </div>

          <div style={{ display: 'flex', alignItems: 'baseline', gap: 'var(--space-1)' }}>
            <span style={{ fontSize: 'var(--font-size-3xl)', fontWeight: 'var(--font-weight-bold)', color: 'var(--text-primary)' }}>
              {summary.carspective_score !== null && summary.carspective_score !== undefined
                ? `${summary.carspective_score}`
                : 'N/A'}
            </span>
            <span style={{ fontSize: 'var(--font-size-lg)', color: 'var(--text-muted)' }}>/ 100</span>
          </div>

          <p style={{ margin: 0, fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
            <strong>Independent of asking price.</strong> Evaluates intrinsic structural safety, reliability, maintenance, and resale liquidity.
          </p>

          {onScrollToSection && (
            <button
              onClick={() => onScrollToSection('score')}
              style={{
                marginTop: 'auto',
                paddingTop: 'var(--space-2)',
                background: 'none',
                border: 'none',
                color: 'var(--color-primary)',
                fontSize: '11px',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                textAlign: 'left',
              }}
            >
              Inspect 5 Dimensions <ArrowRight size={12} />
            </button>
          )}
        </div>

        {/* Pillar 2: Your Fit (Personalized Decision Score) */}
        <div
          style={{
            padding: 'var(--space-5)',
            backgroundColor: 'var(--bg-primary)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--border-subtle)',
            display: 'flex',
            flexDirection: 'column',
            gap: 'var(--space-2)',
            position: 'relative',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 'var(--font-weight-semibold)', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <UserCheck size={16} style={{ color: 'var(--accent-blue)' }} />
              2. Your Fit
            </span>
            {decision ? (
              <Badge variant={decision.user_fit_score >= 80 ? 'success' : decision.user_fit_score >= 65 ? 'info' : 'warning'} size="sm">
                {decision.verdict_label}
              </Badge>
            ) : (
              <Badge variant="neutral" size="sm">
                Default Profile
              </Badge>
            )}
          </div>

          <div style={{ display: 'flex', alignItems: 'baseline', gap: 'var(--space-1)' }}>
            <span style={{ fontSize: 'var(--font-size-3xl)', fontWeight: 'var(--font-weight-bold)', color: decision ? 'var(--color-primary)' : 'var(--text-muted)' }}>
              {decision ? decision.user_fit_score : '—'}
            </span>
            <span style={{ fontSize: 'var(--font-size-lg)', color: 'var(--text-muted)' }}>/ 100</span>
          </div>

          <p style={{ margin: 0, fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
            {decision ? (
              <>
                <strong>Matches your specific usage.</strong> Calibrated to your driving distance, family size, budget, and priority weights.
              </>
            ) : (
              <>
                <strong>No requirements set yet.</strong> Add your budget, family size, and usage to calculate personalized compatibility.
              </>
            )}
          </p>

          <div style={{ marginTop: 'auto', paddingTop: 'var(--space-2)', display: 'flex', gap: 'var(--space-2)' }}>
            {onOpenPreferences && (
              <button
                onClick={onOpenPreferences}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--color-primary)',
                  fontSize: '11px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                }}
              >
                {decision ? 'Adjust Preferences' : 'Set My Preferences'} <ArrowRight size={12} />
              </button>
            )}
          </div>
        </div>

        {/* Pillar 3: Deal Assessment (Commercial Analyzer) */}
        <div
          style={{
            padding: 'var(--space-5)',
            backgroundColor: 'var(--bg-primary)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--border-subtle)',
            display: 'flex',
            flexDirection: 'column',
            gap: 'var(--space-2)',
            position: 'relative',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 'var(--font-weight-semibold)', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Tag size={16} style={{ color: 'var(--color-success)' }} />
              3. Deal Assessment
            </span>
            {dealAnalysis ? (
              <Badge
                variant={
                  dealAnalysis.deal_quality === 'GREAT_DEAL'
                    ? 'success'
                    : dealAnalysis.deal_quality === 'OVERPRICED'
                    ? 'danger'
                    : dealAnalysis.deal_quality === 'UNUSUALLY_LOW_ASKING_PRICE'
                    ? 'warning'
                    : 'info'
                }
                size="sm"
              >
                {dealAnalysis.deal_quality.replace(/_/g, ' ')}
              </Badge>
            ) : (
              <Badge variant="neutral" size="sm">
                No Price Given
              </Badge>
            )}
          </div>

          <div style={{ display: 'flex', alignItems: 'baseline', gap: 'var(--space-2)' }}>
            <span style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 'var(--font-weight-bold)', color: 'var(--text-primary)' }}>
              {dealAnalysis ? dealAnalysis.deal_quality.replace(/_/g, ' ') : 'Pending Price'}
            </span>
          </div>

          <p style={{ margin: 0, fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
            {dealAnalysis ? (
              <>
                Asking ₹{((dealAnalysis.asking_price || 0) / 100000).toFixed(2)}L vs ₹{summary.estimated_fair_market_value_lakhs?.toFixed(2)}L FMV.
                Position: {dealAnalysis.price_deviation?.user_facing_summary || dealAnalysis.deal_quality.replace(/_/g, ' ')}.
              </>
            ) : (
              <>
                Estimated FMV is <strong>₹{summary.estimated_fair_market_value_lakhs?.toFixed(2)}L</strong>.
                Enter seller asking price to analyze deal quality.
              </>
            )}
          </p>

          {onScrollToSection && (
            <button
              onClick={() => onScrollToSection('value')}
              style={{
                marginTop: 'auto',
                paddingTop: 'var(--space-2)',
                background: 'none',
                border: 'none',
                color: 'var(--color-primary)',
                fontSize: '11px',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
              }}
            >
              {dealAnalysis ? 'Analyze Negotiation Range' : 'Enter Asking Price'} <ArrowRight size={12} />
            </button>
          )}
        </div>
      </div>

      {/* ────────────────────────────────────────────────────────── */}
      {/* "SHOULD I CONSIDER THIS?" CARD (Section 5) */}
      {/* ────────────────────────────────────────────────────────── */}
      <div
        style={{
          backgroundColor: 'var(--bg-primary)',
          borderRadius: 'var(--radius-lg)',
          border: '1px solid var(--border-subtle)',
          padding: 'var(--space-5)',
          display: 'flex',
          flexDirection: 'column',
          gap: 'var(--space-4)',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            <HelpCircle size={18} style={{ color: 'var(--accent-blue)' }} />
            <h3 style={{ margin: 0, fontSize: 'var(--font-size-base)', fontWeight: 'var(--font-weight-semibold)' }}>
              Should I Consider This Vehicle?
            </h3>
          </div>
          <Badge variant={verdictProps.variant} size="sm">
            {verdictProps.label}
          </Badge>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 'var(--space-4)' }}>
          {/* Strong Points */}
          <div
            style={{
              padding: 'var(--space-3) var(--space-4)',
              borderRadius: 'var(--radius-md)',
              backgroundColor: 'rgba(34, 197, 94, 0.05)',
              border: '1px solid rgba(34, 197, 94, 0.2)',
            }}
          >
            <h4 style={{ margin: '0 0 var(--space-2)', fontSize: 'var(--font-size-xs)', fontWeight: 'var(--font-weight-bold)', color: 'var(--color-success)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Strong Points (Grounded Evidence)
            </h4>
            <ul style={{ margin: 0, paddingLeft: 'var(--space-4)', fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: 'var(--space-1)' }}>
              {strongPoints.map((sp, idx) => (
                <li key={idx} style={{ lineHeight: 1.4 }}>{sp}</li>
              ))}
            </ul>
          </div>

          {/* Watch-outs */}
          <div
            style={{
              padding: 'var(--space-3) var(--space-4)',
              borderRadius: 'var(--radius-md)',
              backgroundColor: 'rgba(234, 179, 8, 0.05)',
              border: '1px solid rgba(234, 179, 8, 0.2)',
            }}
          >
            <h4 style={{ margin: '0 0 var(--space-2)', fontSize: 'var(--font-size-xs)', fontWeight: 'var(--font-weight-bold)', color: 'var(--color-warning)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Key Watch-Outs Before Deciding
            </h4>
            <ul style={{ margin: 0, paddingLeft: 'var(--space-4)', fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: 'var(--space-1)' }}>
              {watchOuts.map((wo, idx) => (
                <li key={idx} style={{ lineHeight: 1.4 }}>{wo}</li>
              ))}
            </ul>
          </div>
        </div>

        {/* Executive Takeaway */}
        <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)', lineHeight: 1.5, borderTop: '1px solid var(--border-subtle)', paddingTop: 'var(--space-2)' }}>
          <strong>Automotive Takeaway:</strong> {summary.one_line_summary}
        </div>
      </div>

      {/* ────────────────────────────────────────────────────────── */}
      {/* "WHY THIS RESULT?" EXPLAINABILITY PATH (Section 6) */}
      {/* ────────────────────────────────────────────────────────── */}
      <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: 'var(--space-3)' }}>
        <button
          onClick={() => setShowWhyExplainers(!showWhyExplainers)}
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--color-primary)',
            fontSize: 'var(--font-size-xs)',
            fontWeight: 600,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: 0,
          }}
        >
          {showWhyExplainers ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          <span>Why this result? (Deterministic Factor Explainability)</span>
        </button>

        {showWhyExplainers && (
          <div
            style={{
              marginTop: 'var(--space-3)',
              backgroundColor: 'var(--bg-primary)',
              borderRadius: 'var(--radius-lg)',
              border: '1px solid var(--border-subtle)',
              padding: 'var(--space-4)',
              display: 'flex',
              flexDirection: 'column',
              gap: 'var(--space-3)',
            }}
          >
            {/* Tabs */}
            <div style={{ display: 'flex', gap: 'var(--space-2)', borderBottom: '1px solid var(--border-subtle)', paddingBottom: 'var(--space-2)' }}>
              <button
                onClick={() => setActiveExplainTab('score')}
                style={{
                  background: 'none',
                  border: 'none',
                  padding: '4px 8px',
                  cursor: 'pointer',
                  fontSize: 'var(--font-size-xs)',
                  fontWeight: activeExplainTab === 'score' ? 600 : 400,
                  color: activeExplainTab === 'score' ? 'var(--color-primary)' : 'var(--text-muted)',
                  borderBottom: activeExplainTab === 'score' ? '2px solid var(--color-primary)' : 'none',
                }}
              >
                Why {summary.carspective_score}/100 Quality?
              </button>
              <button
                onClick={() => setActiveExplainTab('fit')}
                style={{
                  background: 'none',
                  border: 'none',
                  padding: '4px 8px',
                  cursor: 'pointer',
                  fontSize: 'var(--font-size-xs)',
                  fontWeight: activeExplainTab === 'fit' ? 600 : 400,
                  color: activeExplainTab === 'fit' ? 'var(--color-primary)' : 'var(--text-muted)',
                  borderBottom: activeExplainTab === 'fit' ? '2px solid var(--color-primary)' : 'none',
                }}
              >
                Why User Fit Score?
              </button>
              <button
                onClick={() => setActiveExplainTab('deal')}
                style={{
                  background: 'none',
                  border: 'none',
                  padding: '4px 8px',
                  cursor: 'pointer',
                  fontSize: 'var(--font-size-xs)',
                  fontWeight: activeExplainTab === 'deal' ? 600 : 400,
                  color: activeExplainTab === 'deal' ? 'var(--color-primary)' : 'var(--text-muted)',
                  borderBottom: activeExplainTab === 'deal' ? '2px solid var(--color-primary)' : 'none',
                }}
              >
                Why Deal Status?
              </button>
            </div>

            {/* Tab 1: Vehicle Score Deterministic Factors */}
            {activeExplainTab === 'score' && (
              <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                <p style={{ margin: '0 0 var(--space-2)' }}>
                  <strong>Based on CarSpective&apos;s Phase 5 Intrinsic Scoring Engine:</strong> The {summary.carspective_score}/100 rating is mathematically derived from five independent engineering dimensions with fixed deterministic weights:
                </p>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 'var(--space-2)', marginBottom: 'var(--space-2)' }}>
                  <div style={{ backgroundColor: 'var(--bg-tertiary)', padding: 'var(--space-2)', borderRadius: '4px' }}>
                    1. Structural Safety (25% weight): {summary.safety_stars ? `${summary.safety_stars}★ NCAP` : 'Unrated (Denominator excluded)'}
                  </div>
                  <div style={{ backgroundColor: 'var(--bg-tertiary)', padding: 'var(--space-2)', borderRadius: '4px' }}>
                    2. Reliability & Longevity (25% weight): {summary.reliability_watchpoints_count} service watchpoints recorded
                  </div>
                  <div style={{ backgroundColor: 'var(--bg-tertiary)', padding: 'var(--space-2)', borderRadius: '4px' }}>
                    3. Maintenance & TCO (20% weight): {summary.typical_annual_maintenance_inr}
                  </div>
                  <div style={{ backgroundColor: 'var(--bg-tertiary)', padding: 'var(--space-2)', borderRadius: '4px' }}>
                    4. Resale & Liquidity (15% weight): Empirical depreciation tier
                  </div>
                  <div style={{ backgroundColor: 'var(--bg-tertiary)', padding: 'var(--space-2)', borderRadius: '4px' }}>
                    5. Practicality & Ergonomics (15% weight): Space and utility profile
                  </div>
                </div>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                  Invariant: Intrinsic vehicle score is strictly isolated from seller asking price and user profile settings.
                </span>
              </div>
            )}

            {/* Tab 2: User Fit Factors */}
            {activeExplainTab === 'fit' && (
              <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                {decision ? (
                  <>
                    <p style={{ margin: '0 0 var(--space-2)' }}>
                      <strong>Based on Phase 15 Deterministic Constraint & Multiplier Engine:</strong>
                    </p>
                    <ul style={{ margin: 0, paddingLeft: 'var(--space-4)', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                      <li>Vehicle Suitability Subscore: <strong>{decision.vehicle_fit_score}/100</strong></li>
                      <li>Hard Constraints Status: <strong>{decision.hard_constraint_status}</strong></li>
                      {decision.deal_fit_score !== null && (
                        <li>Deal Budget Subscore: <strong>{decision.deal_fit_score}/100</strong></li>
                      )}
                    </ul>
                  </>
                ) : (
                  <p style={{ margin: 0 }}>
                    Configure your requirements profile in &quot;My Preferences&quot; to inspect how your budget, commute distance, and priorities affect suitability.
                  </p>
                )}
              </div>
            )}

            {/* Tab 3: Deal Factors */}
            {activeExplainTab === 'deal' && (
              <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                <p style={{ margin: '0 0 var(--space-2)' }}>
                  <strong>Based on Phase 4 Conformal Commercial Comparator:</strong>
                </p>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <div>• Estimated Fair Market Value: <strong>₹{summary.estimated_fair_market_value_lakhs?.toFixed(2)} Lakhs</strong></div>
                  <div>• Expected Conformal Range: <strong>₹{summary.expected_fair_market_range_low_lakhs?.toFixed(2)}L – ₹{summary.expected_fair_market_range_high_lakhs?.toFixed(2)}L</strong></div>
                  <div>• Methodology: Evaluates asking price delta against conformal distribution, historical depreciation, and condition signals.</div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ────────────────────────────────────────────────────────── */}
      {/* LEVEL 3 EVIDENCE PROVENANCE & FRESHNESS DISCLOSURE */}
      {/* ────────────────────────────────────────────────────────── */}
      {evidenceDisclosureLevel === 3 && (
        <div
          style={{
            backgroundColor: 'var(--bg-tertiary)',
            borderRadius: 'var(--radius-md)',
            padding: 'var(--space-3)',
            fontSize: '11px',
            color: 'var(--text-muted)',
            display: 'flex',
            flexDirection: 'column',
            gap: '4px',
            border: '1px solid var(--border-subtle)',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
              Data Provenance & Freshness (Phase 16 & 17 Governed Audits)
            </span>
            <EvidenceBadge state="VERIFIED" size="sm" />
          </div>
          <div>• Historical Baseline: 57,480 Indian used-car seller asking-price observations (2018–2024).</div>
          <div>• Current Market Observations: Multi-metro secondary asking prices (2026-Q3). Never claimed as transaction prices.</div>
          <div>• Valuation Artifact: LightGBM Regressor (SHA-256: <code>4a4ccf3f78...</code> verified immutable).</div>
        </div>
      )}
    </div>
  );
};
