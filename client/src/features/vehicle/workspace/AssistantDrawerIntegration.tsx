import React from 'react';
import { Button } from '../../../components/common/Button';
import { Bot, Sparkles, MessageSquareQuote } from 'lucide-react';
import { useApp } from '../../../state/AppContext';

export interface AssistantDrawerIntegrationProps {
  vehicleSummary: string;
  score?: number | null;
  fmvLakhs?: number | null;
}

export const AssistantDrawerIntegration: React.FC<AssistantDrawerIntegrationProps> = ({
  vehicleSummary,
  score,
  fmvLakhs,
}) => {
  const { openAssistant, setAssistantPrompt } = useApp();

  const handlePromptClick = (promptText: string) => {
    if (setAssistantPrompt) {
      setAssistantPrompt(promptText);
    }
    openAssistant();
  };

  const samplePrompts = [
    score ? `Why is this car rated ${score}?` : `Why is this car rated with this score?`,
    `Is this asking price fair?`,
    `What should I inspect first?`,
    `How does this compare with the alternatives?`,
    `What are the biggest ownership risks?`,
    `What current market evidence do we have?`,
  ];

  return (
    <div
      style={{
        borderRadius: 'var(--radius-xl)',
        backgroundColor: 'var(--bg-secondary)',
        border: '1px solid var(--border-medium)',
        padding: 'var(--space-6)',
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-4)',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
          <Bot size={20} style={{ color: 'var(--color-primary)' }} />
          <h3 style={{ margin: 0, fontSize: 'var(--font-size-xl)' }}>
            Grounded Automotive AI Assistant
          </h3>
        </div>

        <Button
          variant="primary"
          size="md"
          leftIcon={<Bot size={16} />}
          onClick={openAssistant}
        >
          Ask Assistant
        </Button>
      </div>

      <p style={{ margin: 0, fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
        Ask questions grounded exclusively in CarSpective&apos;s verified technical taxonomy, valuation models, and inspection checklists. No ungrounded hallucinations.
      </p>

      {/* Quick Prompts Pills */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
        {samplePrompts.map((p, idx) => (
          <button
            key={idx}
            onClick={() => handlePromptClick(p)}
            style={{
              padding: 'var(--space-2) var(--space-3)',
              borderRadius: 'var(--radius-full)',
              backgroundColor: 'var(--bg-primary)',
              border: '1px solid var(--border-medium)',
              color: 'var(--text-primary)',
              fontSize: 'var(--font-size-xs)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--space-2)',
              transition: 'all 0.15s ease',
            }}
          >
            <Sparkles size={13} style={{ color: 'var(--accent-blue)' }} />
            <span>{p}</span>
          </button>
        ))}
      </div>
    </div>
  );
};
