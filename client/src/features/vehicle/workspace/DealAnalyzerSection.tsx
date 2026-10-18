import React, { useState } from 'react';
import { DealAnalysisResponse, DealQuality, EvidenceState } from '../../../types';
import { Badge } from '../../../components/common/Badge';
import { Button } from '../../../components/common/Button';
import { Input } from '../../../components/common/Input';
import { DollarSign, Tag, TrendingDown, TrendingUp, AlertTriangle, CheckCircle2, ShieldAlert } from 'lucide-react';

export interface DealAnalyzerSectionProps {
  dealAnalysis?: DealAnalysisResponse | null;
  fairMarketValue?: number | null;
  onEvaluateDeal: (askingPrice: number, kmDriven?: number) => void;
  isLoading?: boolean;
}

export const DealAnalyzerSection: React.FC<DealAnalyzerSectionProps> = ({
  dealAnalysis,
  fairMarketValue,
  onEvaluateDeal,
  isLoading,
}) => {
  const [askingPriceInput, setAskingPriceInput] = useState<string>('');
  const [kmInput, setKmInput] = useState<string>('');

  const handleEvaluate = (e: React.FormEvent) => {
    e.preventDefault();
    const price = parseFloat(askingPriceInput.replace(/,/g, ''));
    const km = kmInput ? parseFloat(kmInput.replace(/,/g, '')) : undefined;
    if (!isNaN(price) && price > 0) {
      onEvaluateDeal(price, km);
    }
  };

  const getDealBadgeProps = (quality: DealQuality | string) => {
    switch (quality) {
      case 'GREAT_DEAL':
        return { variant: 'success' as const, label: 'Great Deal', color: 'var(--color-success)' };
      case 'FAIR_DEAL':
        return { variant: 'info' as const, label: 'Fair Deal', color: 'var(--accent-blue)' };
      case 'OVERPRICED':
        return { variant: 'danger' as const, label: 'Overpriced', color: 'var(--color-danger)' };
      case 'UNUSUALLY_LOW_ASKING_PRICE':
        return { variant: 'warning' as const, label: 'Unusually Low Price — Caution', color: 'var(--color-warning)' };
      default:
        return { variant: 'neutral' as const, label: String(quality).replace('_', ' '), color: 'var(--text-muted)' };
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
      {/* Header with Strict Isolation Note */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            <Tag size={20} style={{ color: 'var(--accent-blue)' }} />
            <h3 style={{ margin: 0, fontSize: 'var(--font-size-xl)' }}>
              Commercial Deal Analyzer
            </h3>
          </div>
          <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
            Phase 4 Asking Price Evaluation (Isolated from Intrinsic Vehicle Valuation)
          </span>
        </div>

        {dealAnalysis && (
          <Badge variant={getDealBadgeProps(dealAnalysis.deal_quality).variant} size="md">
            {getDealBadgeProps(dealAnalysis.deal_quality).label}
          </Badge>
        )}
      </div>

      {/* Interactive Deal Input Form */}
      <form
        onSubmit={handleEvaluate}
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr)) auto',
          alignItems: 'end',
          gap: 'var(--space-3)',
          padding: 'var(--space-4)',
          backgroundColor: 'var(--bg-primary)',
          borderRadius: 'var(--radius-lg)',
          border: '1px solid var(--border-subtle)',
        }}
      >
        <div>
          <label style={{ display: 'block', fontSize: 'var(--font-size-xs)', fontWeight: 'var(--font-weight-medium)', marginBottom: 'var(--space-1)', color: 'var(--text-secondary)' }}>
            Seller Asking Price (₹)
          </label>
          <input
            type="number"
            placeholder={fairMarketValue ? String(fairMarketValue) : "e.g. 650000"}
            value={askingPriceInput}
            onChange={(e) => setAskingPriceInput(e.target.value)}
            style={{
              width: '100%',
              padding: 'var(--space-2) var(--space-3)',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-medium)',
              backgroundColor: 'var(--bg-secondary)',
              color: 'var(--text-primary)',
              fontSize: 'var(--font-size-sm)',
            }}
          />
        </div>

        <div>
          <label style={{ display: 'block', fontSize: 'var(--font-size-xs)', fontWeight: 'var(--font-weight-medium)', marginBottom: 'var(--space-1)', color: 'var(--text-secondary)' }}>
            Odometer Reading (km)
          </label>
          <input
            type="number"
            placeholder="e.g. 35000"
            value={kmInput}
            onChange={(e) => setKmInput(e.target.value)}
            style={{
              width: '100%',
              padding: 'var(--space-2) var(--space-3)',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-medium)',
              backgroundColor: 'var(--bg-secondary)',
              color: 'var(--text-primary)',
              fontSize: 'var(--font-size-sm)',
            }}
          />
        </div>

        <Button
          type="submit"
          variant="primary"
          size="md"
          isLoading={isLoading}
          leftIcon={<DollarSign size={16} />}
        >
          Evaluate Deal
        </Button>
      </form>

      {/* Analysis Results (if asking price evaluated) */}
      {dealAnalysis ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
              gap: 'var(--space-4)',
            }}
          >
            {/* Deviation Metric */}
            <div
              style={{
                padding: 'var(--space-4)',
                backgroundColor: 'var(--bg-primary)',
                borderRadius: 'var(--radius-lg)',
                border: '1px solid var(--border-subtle)',
                display: 'flex',
                flexDirection: 'column',
                gap: 'var(--space-1)',
              }}
            >
              <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
                Price Deviation from Fair Market Value
              </span>
              <div
                style={{
                  fontSize: 'var(--font-size-2xl)',
                  fontWeight: 'var(--font-weight-bold)',
                  color: (dealAnalysis.price_deviation?.relative_difference_percent || 0) < 0 ? 'var(--color-success)' : 'var(--color-danger)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 'var(--space-1)',
                }}
              >
                {(dealAnalysis.price_deviation?.relative_difference_percent || 0) < 0 ? <TrendingDown size={20} /> : <TrendingUp size={20} />}
                <span>
                  {Math.abs(dealAnalysis.price_deviation?.relative_difference_percent || 0).toFixed(1)}% {dealAnalysis.price_deviation?.user_facing_summary ? `(${dealAnalysis.price_deviation.user_facing_summary})` : ''}
                </span>
              </div>
              <span style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>
                Asking ₹{dealAnalysis.asking_price != null ? dealAnalysis.asking_price.toLocaleString('en-IN') : '—'} vs FMV ₹{(dealAnalysis.valuation?.estimated_fair_market_value || fairMarketValue || 0).toLocaleString('en-IN')}
              </span>
            </div>

            {/* Negotiation Guidance */}
            {dealAnalysis.negotiation && (
              <div
                style={{
                  padding: 'var(--space-4)',
                  backgroundColor: 'var(--bg-primary)',
                  borderRadius: 'var(--radius-lg)',
                  border: '1px solid var(--border-subtle)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 'var(--space-1)',
                }}
              >
                <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
                  Recommended Negotiation Range
                </span>
                <div style={{ fontSize: 'var(--font-size-xl)', fontWeight: 'var(--font-weight-bold)', color: 'var(--text-primary)' }}>
                  {dealAnalysis.negotiation.target_range_formatted || 'Fair Market Baseline'}
                </div>
                <span style={{ fontSize: '11px', color: 'var(--accent-blue)' }}>
                  Leverage: {dealAnalysis.negotiation.negotiation_strength}
                </span>
              </div>
            )}
          </div>

          {/* Deal Explanation Narrative */}
          <div
            style={{
              padding: 'var(--space-3) var(--space-4)',
              backgroundColor: 'var(--bg-primary)',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-subtle)',
              fontSize: 'var(--font-size-xs)',
              color: 'var(--text-secondary)',
              lineHeight: 1.5,
            }}
          >
            <strong>Deal Verdict Explanation:</strong> {dealAnalysis.explanation}
          </div>

          {/* Risk Signals */}
          {dealAnalysis.risk_signals && dealAnalysis.risk_signals.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
              <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 'var(--font-weight-bold)', color: 'var(--color-warning)', display: 'flex', alignItems: 'center', gap: 'var(--space-1)' }}>
                <AlertTriangle size={14} /> Commercial Risk Watchpoints:
              </span>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
                {dealAnalysis.risk_signals.map((sig, idx) => (
                  <div
                    key={idx}
                    style={{
                      padding: 'var(--space-2) var(--space-3)',
                      backgroundColor: 'rgba(214, 158, 46, 0.08)',
                      borderRadius: 'var(--radius-md)',
                      fontSize: '11px',
                      color: 'var(--text-primary)',
                      border: '1px solid rgba(214, 158, 46, 0.25)',
                    }}
                  >
                    <strong>{sig.title}:</strong> {sig.explanation}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : (
        <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)', lineHeight: 1.5 }}>
          No asking price has been provided for this vehicle. Enter an asking price above to compare against the historical market baseline and receive negotiation guidance.
        </div>
      )}
    </div>
  );
};
