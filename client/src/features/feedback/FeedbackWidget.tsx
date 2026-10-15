import React, { useState } from 'react';
import { ThumbsUp, ThumbsDown, CheckCircle2 } from 'lucide-react';
import { Button } from '../../components/common/Button';
import { Input } from '../../components/common/Input';
import { useApp } from '../../state/AppContext';

export interface FeedbackWidgetProps {
  feature?: 'valuation' | 'deal' | 'score' | 'recommendation' | 'comparison' | 'inspection' | 'assistant';
  vehicleContext?: string;
}

export const FeedbackWidget: React.FC<FeedbackWidgetProps> = ({
  feature = 'valuation',
  vehicleContext,
}) => {
  const { showToast } = useApp();
  const [submitted, setSubmitted] = useState(false);
  const [useful, setUseful] = useState<boolean | null>(null);
  const [expectedPrice, setExpectedPrice] = useState('');
  const [comment, setComment] = useState('');
  const [showDetails, setShowDetails] = useState(false);

  const handleVote = (isUseful: boolean) => {
    setUseful(isUseful);
    setShowDetails(true);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitted(true);
    showToast('Thank you! Your feedback helps us improve market transparency.', 'success');
  };

  if (submitted) {
    return (
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--space-2)',
          padding: 'var(--space-3) var(--space-4)',
          backgroundColor: 'var(--status-pass-bg)',
          borderRadius: 'var(--radius-lg)',
          fontSize: 'var(--font-size-xs)',
          color: 'var(--status-pass)',
          fontWeight: 'var(--font-weight-medium)',
        }}
      >
        <CheckCircle2 size={16} />
        <span>Feedback received. Thank you for helping keep CarSpective grounded!</span>
      </div>
    );
  }

  return (
    <div
      style={{
        padding: 'var(--space-4)',
        backgroundColor: 'var(--bg-secondary)',
        borderRadius: 'var(--radius-lg)',
        border: '1px solid var(--border-light)',
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-3)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
        <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)', fontWeight: 'var(--font-weight-medium)' }}>
          Was this analysis useful?
        </span>

        <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
          <button
            onClick={() => handleVote(true)}
            aria-label="Yes, this was useful"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 'var(--space-1)',
              padding: 'var(--space-1) var(--space-3)',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-medium)',
              backgroundColor: useful === true ? 'var(--status-pass-bg)' : 'var(--bg-primary)',
              color: useful === true ? 'var(--status-pass)' : 'var(--text-secondary)',
              fontSize: 'var(--font-size-xs)',
              cursor: 'pointer',
            }}
          >
            <ThumbsUp size={12} />
            <span>Yes</span>
          </button>

          <button
            onClick={() => handleVote(false)}
            aria-label="No, this was not useful"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 'var(--space-1)',
              padding: 'var(--space-1) var(--space-3)',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-medium)',
              backgroundColor: useful === false ? 'var(--status-fail-bg)' : 'var(--bg-primary)',
              color: useful === false ? 'var(--status-fail)' : 'var(--text-secondary)',
              fontSize: 'var(--font-size-xs)',
              cursor: 'pointer',
            }}
          >
            <ThumbsDown size={12} />
            <span>No</span>
          </button>
        </div>
      </div>

      {showDetails && (
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
          {feature === 'valuation' && (
            <Input
              placeholder="What price did you expect? (optional)"
              value={expectedPrice}
              onChange={e => setExpectedPrice(e.target.value)}
              style={{ fontSize: 'var(--font-size-xs)' }}
            />
          )}

          <input
            type="text"
            placeholder="Additional comments (optional)"
            value={comment}
            onChange={e => setComment(e.target.value)}
            style={{
              padding: 'var(--space-2)',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-medium)',
              fontSize: 'var(--font-size-xs)',
              backgroundColor: 'var(--bg-primary)',
              color: 'var(--text-primary)',
            }}
          />

          <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
            <Button type="submit" variant="secondary" size="sm">
              Submit Feedback
            </Button>
          </div>
        </form>
      )}
    </div>
  );
};
