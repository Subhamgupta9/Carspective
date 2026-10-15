import React, { useState } from 'react';
import { DealAnalysisResponse } from '../../types';
import { formatINR, formatINRFull, formatPercent } from '../../utils/formatters';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import { Input } from '../../components/common/Input';
import {
  TrendingDown,
  TrendingUp,
  AlertTriangle,
  ShieldAlert,
  Target,
  ArrowRight,
  CheckCircle2,
} from 'lucide-react';

export interface DealAnalyzerCardProps {
  dealAnalysis?: DealAnalysisResponse | null;
  onAnalyze: (askingPrice: number) => void;
  isLoading?: boolean;
}

export const DealAnalyzerCard: React.FC<DealAnalyzerCardProps> = ({
  dealAnalysis,
  onAnalyze,
  isLoading,
}) => {
  const [inputPrice, setInputPrice] = useState(
    dealAnalysis?.asking_price ? String(dealAnalysis.asking_price) : ''
  );

  const handlePriceSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const parsed = parseFloat(inputPrice);
    if (!isNaN(parsed) && parsed > 0) {
      onAnalyze(parsed);
    }
  };

  const getDealConfig = (quality?: string) => {
    switch (quality) {
      case 'GREAT_DEAL':
        return {
          label: 'Great Deal',
          badgeVariant: 'success' as const,
          color: 'var(--deal-great)',
          bg: 'var(--deal-great-bg)',
          icon: <TrendingDown size={18} />,
          summary: 'Asking price is below the expected fair market range for this vehicle.',
          actionAdvice: 'Verify title, odometer, and mechanical condition before committing.',
        };
      case 'FAIR_DEAL':
        return {
          label: 'Fair Deal',
          badgeVariant: 'info' as const,
          color: 'var(--deal-fair)',
          bg: 'var(--deal-fair-bg)',
          icon: <CheckCircle2 size={18} />,
          summary: 'Asking price is well within the calibrated fair-market asking-price range.',
          actionAdvice: 'Standard inspection and documentation verification recommended.',
        };
      case 'OVERPRICED':
        return {
          label: 'Overpriced',
          badgeVariant: 'danger' as const,
          color: 'var(--deal-overpriced)',
          bg: 'var(--deal-overpriced-bg)',
          icon: <TrendingUp size={18} />,
          summary: "Asking price is above CarSpective's expected fair-market range.",
          actionAdvice: 'Use the target negotiation price below or request proof of exceptional maintenance.',
        };
      case 'UNUSUALLY_LOW_ASKING_PRICE':
        return {
          label: 'Unusually Low Price',
          badgeVariant: 'warning' as const,
          color: 'var(--deal-low)',
          bg: 'var(--deal-low-bg)',
          icon: <AlertTriangle size={18} />,
          summary: 'Asking price is statistically anomalous and far below market baseline.',
          actionAdvice:
            'Caution: Low price does not guarantee a good purchase. High risk of hidden defects, salvage, or paperwork issues.',
        };
      default:
        return {
          label: 'Limited Data',
          badgeVariant: 'neutral' as const,
          color: 'var(--text-muted)',
          bg: 'var(--bg-tertiary)',
          icon: <AlertTriangle size={18} />,
          summary: 'Insufficient data to evaluate commercial deal quality.',
          actionAdvice: 'Provide additional listing attributes to enable deal evaluation.',
        };
    }
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-5)',
        backgroundColor: 'var(--bg-primary)',
        borderRadius: 'var(--radius-xl)',
        border: '1px solid var(--border-subtle)',
        padding: 'var(--space-6)',
        boxShadow: 'var(--shadow-sm)',
      }}
    >
      {/* Header & Asking Price Input */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 'var(--space-4)',
          borderBottom: '1px solid var(--border-light)',
          paddingBottom: 'var(--space-4)',
        }}
      >
        <div>
          <h3 style={{ fontSize: 'var(--font-size-2xl)', margin: 0 }}>Deal Analyzer</h3>
          <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-muted)', margin: 'var(--space-1) 0 0 0' }}>
            Evidence-based evaluation of seller asking price against fair market valuation.
          </p>
        </div>

        {/* Asking Price Form */}
        <form
          onSubmit={handlePriceSubmit}
          style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}
        >
          <Input
            placeholder="Seller price in INR (e.g. 850000)"
            value={inputPrice}
            onChange={e => setInputPrice(e.target.value)}
            style={{ width: '220px' }}
            aria-label="Enter asking price"
          />
          <Button type="submit" variant="primary" size="md" isLoading={isLoading}>
            Analyze Deal
          </Button>
        </form>
      </div>

      {!dealAnalysis ? (
        /* Empty State */
        <div
          style={{
            padding: 'var(--space-8)',
            textAlign: 'center',
            backgroundColor: 'var(--bg-secondary)',
            borderRadius: 'var(--radius-lg)',
            border: '1px dashed var(--border-medium)',
          }}
        >
          <Target size={32} color="var(--accent-blue)" style={{ margin: '0 auto var(--space-2)' }} />
          <h4 style={{ margin: '0 0 var(--space-1)', fontSize: 'var(--font-size-base)' }}>
            Enter Asking Price to Analyze Deal
          </h4>
          <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-muted)', margin: 0 }}>
            Compare seller asking price with the calibrated market baseline to identify negotiation targets.
          </p>
        </div>
      ) : (
        /* Analysis Details */
        <>
          {(() => {
            const config = getDealConfig(dealAnalysis.deal_quality);
            return (
              <div
                style={{
                  backgroundColor: config.bg,
                  borderRadius: 'var(--radius-xl)',
                  padding: 'var(--space-5)',
                  border: `1px solid ${config.color}33`,
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 'var(--space-3)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                    <span style={{ color: config.color }}>{config.icon}</span>
                    <span style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 'var(--font-weight-extrabold)', color: config.color }}>
                      {config.label}
                    </span>
                  </div>

                  <Badge variant={config.badgeVariant} size="md">
                    {dealAnalysis.deal_quality_label}
                  </Badge>
                </div>

                <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-primary)', margin: 0, fontWeight: 'var(--font-weight-medium)' }}>
                  {config.summary}
                </p>

                <div
                  style={{
                    backgroundColor: 'rgba(255, 255, 255, 0.85)',
                    borderRadius: 'var(--radius-md)',
                    padding: 'var(--space-3) var(--space-4)',
                    fontSize: 'var(--font-size-xs)',
                    color: 'var(--text-secondary)',
                    lineHeight: 1.5,
                  }}
                >
                  <strong>What to do:</strong> {config.actionAdvice}
                </div>
              </div>
            );
          })()}

          {/* Price Metrics Grid */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
              gap: 'var(--space-4)',
            }}
          >
            <div style={{ backgroundColor: 'var(--bg-secondary)', padding: 'var(--space-4)', borderRadius: 'var(--radius-lg)' }}>
              <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>Asking Price</div>
              <div style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 'var(--font-weight-bold)', color: 'var(--text-primary)' }}>
                {formatINR(dealAnalysis.asking_price)}
              </div>
              <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
                {formatINRFull(dealAnalysis.asking_price)}
              </div>
            </div>

            <div style={{ backgroundColor: 'var(--bg-secondary)', padding: 'var(--space-4)', borderRadius: 'var(--radius-lg)' }}>
              <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>Fair Market Baseline</div>
              <div style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 'var(--font-weight-bold)', color: 'var(--accent-blue)' }}>
                {formatINR(dealAnalysis.valuation.estimated_fair_market_value)}
              </div>
              <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
                {formatINRFull(dealAnalysis.valuation.estimated_fair_market_value)}
              </div>
            </div>

            <div style={{ backgroundColor: 'var(--bg-secondary)', padding: 'var(--space-4)', borderRadius: 'var(--radius-lg)' }}>
              <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>Price Difference</div>
              <div
                style={{
                  fontSize: 'var(--font-size-2xl)',
                  fontWeight: 'var(--font-weight-bold)',
                  color: dealAnalysis.price_deviation.absolute_difference > 0 ? 'var(--status-fail)' : 'var(--status-pass)',
                }}
              >
                {dealAnalysis.price_deviation.absolute_difference > 0 ? '+' : ''}
                {formatINR(dealAnalysis.price_deviation.absolute_difference)}
              </div>
              <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
                {formatPercent(dealAnalysis.price_deviation.relative_difference_percent, true)} vs baseline
              </div>
            </div>
          </div>

          {/* Negotiation Guidance Card */}
          {dealAnalysis.negotiation && (
            <div
              style={{
                backgroundColor: 'var(--bg-secondary)',
                borderRadius: 'var(--radius-xl)',
                padding: 'var(--space-5)',
                border: '1px solid var(--border-subtle)',
                display: 'flex',
                flexDirection: 'column',
                gap: 'var(--space-3)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                  <Target size={18} color="var(--accent-blue)" />
                  <h4 style={{ margin: 0, fontSize: 'var(--font-size-base)' }}>Defensible Negotiation Target</h4>
                </div>
                <Badge variant="info" size="sm">
                  Leverage: {dealAnalysis.negotiation.negotiation_strength}
                </Badge>
              </div>

              <div style={{ display: 'flex', alignItems: 'baseline', gap: 'var(--space-3)' }}>
                <span style={{ fontSize: 'var(--font-size-3xl)', fontWeight: 'var(--font-weight-extrabold)', color: 'var(--accent-blue)' }}>
                  {formatINR(dealAnalysis.negotiation.target_price)}
                </span>
                {dealAnalysis.negotiation.target_range_formatted && (
                  <span style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-muted)' }}>
                    Target Range: {dealAnalysis.negotiation.target_range_formatted}
                  </span>
                )}
              </div>

              <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)', margin: 0 }}>
                {dealAnalysis.negotiation.rationale}
              </p>

              <div
                style={{
                  fontSize: 'var(--font-size-xs)',
                  color: 'var(--text-muted)',
                  borderTop: '1px solid var(--border-light)',
                  paddingTop: 'var(--space-2)',
                }}
              >
                <em>{dealAnalysis.negotiation.safety_disclaimer}</em>
              </div>
            </div>
          )}

          {/* Risk Signals */}
          {dealAnalysis.risk_signals && dealAnalysis.risk_signals.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                <ShieldAlert size={18} color="var(--status-attention)" />
                <h4 style={{ margin: 0, fontSize: 'var(--font-size-base)' }}>
                  Identified Risk Signals ({dealAnalysis.risk_signals.length})
                </h4>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
                {dealAnalysis.risk_signals.map((risk, idx) => (
                  <div
                    key={idx}
                    style={{
                      padding: 'var(--space-3) var(--space-4)',
                      borderRadius: 'var(--radius-lg)',
                      backgroundColor: risk.severity === 'CRITICAL' || risk.severity === 'HIGH' ? 'var(--status-fail-bg)' : 'var(--status-attention-bg)',
                      border: `1px solid ${risk.severity === 'CRITICAL' || risk.severity === 'HIGH' ? 'var(--status-fail-border)' : 'var(--status-attention-border)'}`,
                      display: 'flex',
                      flexDirection: 'column',
                      gap: 'var(--space-1)',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontWeight: 'var(--font-weight-semibold)', fontSize: 'var(--font-size-sm)', color: 'var(--text-primary)' }}>
                        {risk.title}
                      </span>
                      <Badge variant={risk.severity === 'CRITICAL' || risk.severity === 'HIGH' ? 'danger' : 'warning'} size="sm">
                        {risk.severity}
                      </Badge>
                    </div>
                    <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)', margin: 0 }}>
                      {risk.explanation}
                    </p>
                    <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-primary)', fontWeight: 'var(--font-weight-medium)', marginTop: '2px' }}>
                      <strong>Action:</strong> {risk.recommended_action}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};
