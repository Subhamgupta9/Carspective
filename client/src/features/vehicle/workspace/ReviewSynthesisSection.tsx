import React from 'react';
import { ReviewSynthesis, EvidenceState } from '../../../types';
import { EvidenceBadge } from '../../../components/common/EvidenceBadge';
import { BookOpen, UserCheck, Award, Sparkles } from 'lucide-react';

export interface ReviewSynthesisSectionProps {
  reviews?: ReviewSynthesis | null;
}

export const ReviewSynthesisSection: React.FC<ReviewSynthesisSectionProps> = ({ reviews }) => {
  if (!reviews) {
    return null;
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
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            <BookOpen size={20} style={{ color: 'var(--color-primary)' }} />
            <h3 style={{ margin: 0, fontSize: 'var(--font-size-xl)' }}>
              Tripartite Review Synthesis
            </h3>
          </div>
          <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
            Empirical aggregation across verified owners, automotive journalists, and algorithmic analysis
          </span>
        </div>

        <EvidenceBadge state={(reviews.evidence_state as EvidenceState) || 'SUPPORTED'} size="sm" />
      </div>

      {/* 3 Synthesis Columns */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: 'var(--space-4)',
        }}
      >
        {/* Column 1: Owners */}
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
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', color: 'var(--accent-blue)', fontWeight: 'var(--font-weight-bold)', fontSize: 'var(--font-size-sm)' }}>
            <UserCheck size={16} />
            <span>What Verified Owners Report</span>
          </div>
          <p style={{ margin: 0, fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
            {reviews.what_owners_say || 'Owner evidence survey data unavailable.'}
          </p>
        </div>

        {/* Column 2: Journalists */}
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
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', color: 'var(--color-success)', fontWeight: 'var(--font-weight-bold)', fontSize: 'var(--font-size-sm)' }}>
            <Award size={16} />
            <span>What Automotive Journalists Conclude</span>
          </div>
          <p style={{ margin: 0, fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
            {reviews.what_experts_say || 'Editorial evaluation reports unavailable.'}
          </p>
        </div>

        {/* Column 3: CarSpective Analysis */}
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
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', color: 'var(--color-primary)', fontWeight: 'var(--font-weight-bold)', fontSize: 'var(--font-size-sm)' }}>
            <Sparkles size={16} />
            <span>CarSpective Intelligence Verdict</span>
          </div>
          <p style={{ margin: 0, fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
            {reviews.carspective_analysis}
          </p>
        </div>
      </div>
    </div>
  );
};
