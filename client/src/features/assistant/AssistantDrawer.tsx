import React, { useState, useRef, useEffect } from 'react';
import { useApp } from '../../state/AppContext';
import { assistantApi } from '../../api/assistantApi';
import { AssistantRequest, AssistantResponse, AssistantEvidenceCitation } from '../../types';
import { Button } from '../../components/common/Button';
import { EvidenceBadge } from '../../components/common/EvidenceBadge';
import {
  MessageSquare,
  X,
  Send,
  Sparkles,
  Bot,
  User,
  ArrowRight,
  ShieldAlert,
} from 'lucide-react';

interface ChatTurn {
  role: 'user' | 'assistant';
  content: string;
  citations?: AssistantEvidenceCitation[];
  nextActions?: string[];
  timestamp: string;
}

export const AssistantDrawer: React.FC = () => {
  const { isAssistantOpen, closeAssistant, currentVehicle, assistantPrompt, setAssistantPrompt } = useApp();
  const [messages, setMessages] = useState<ChatTurn[]>([
    {
      role: 'assistant',
      content:
        "Hello, I'm the CarSpective Assistant. I can explain market valuation baselines, deal quality, inspection checkpoints, and safety ratings grounded in empirical evidence.",
      nextActions: [
        'Is the asking price fair?',
        'What should I inspect first?',
        'How does safety score compare?',
      ],
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);
  const [inputQuery, setInputQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (assistantPrompt) {
      setInputQuery(assistantPrompt);
      if (setAssistantPrompt) setAssistantPrompt('');
    }
  }, [assistantPrompt, setAssistantPrompt]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  if (!isAssistantOpen) return null;

  const handleSend = async (queryToSend?: string) => {
    const text = (queryToSend || inputQuery).trim();
    if (!text || isLoading) return;

    const userTurn: ChatTurn = {
      role: 'user',
      content: text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages(prev => [...prev, userTurn]);
    setInputQuery('');
    setIsLoading(true);

    try {
      const payload: AssistantRequest = {
        message: text,
        vehicle: currentVehicle
          ? {
              brand: currentVehicle.brand,
              model: currentVehicle.model,
              manufacturing_year: currentVehicle.year,
              variant: currentVehicle.variant,
              fuel_type: currentVehicle.fuel_type || 'Petrol',
              transmission_type: currentVehicle.transmission_type || 'Manual',
              km_driven: currentVehicle.km_driven,
              canonical_vehicle_id: currentVehicle.canonical_id,
            }
          : undefined,
        listing: currentVehicle?.asking_price
          ? {
              asking_price: currentVehicle.asking_price,
            }
          : undefined,
      };

      const res: AssistantResponse = await assistantApi.askAssistant(payload);
      const items = res.evidence_bundle || res.citations || [];

      const assistantTurn: ChatTurn = {
        role: 'assistant',
        content: res.answer,
        citations: items,
        nextActions: res.suggested_next_actions,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };

      setMessages(prev => [...prev, assistantTurn]);
    } catch (err: any) {
      const errorMsg =
        err?.detail ||
        err?.message ||
        'I encountered an issue querying the automotive intelligence engines. Please check the vehicle valuation or checklist directly.';
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: errorMsg,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        right: 0,
        bottom: 0,
        width: '100%',
        maxWidth: '440px',
        backgroundColor: 'var(--bg-primary)',
        boxShadow: 'var(--shadow-xl)',
        borderLeft: '1px solid var(--border-medium)',
        zIndex: 1100,
        display: 'flex',
        flexDirection: 'column',
        animation: 'slideInRight 0.25s cubic-bezier(0.16, 1, 0.3, 1)',
      }}
      role="complementary"
      aria-label="Ask CarSpective AI Assistant"
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: 'var(--space-4) var(--space-5)',
          borderBottom: '1px solid var(--border-light)',
          backgroundColor: 'var(--bg-secondary)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
          <div
            style={{
              padding: 'var(--space-2)',
              borderRadius: 'var(--radius-md)',
              backgroundColor: 'var(--accent-blue)',
              color: '#FFFFFF',
              display: 'flex',
            }}
          >
            <Bot size={18} />
          </div>
          <div>
            <h4 style={{ margin: 0, fontSize: 'var(--font-size-base)' }}>Ask CarSpective</h4>
            <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
              Grounded Automotive Intelligence
            </span>
          </div>
        </div>

        <button
          onClick={closeAssistant}
          aria-label="Close assistant drawer"
          style={{
            padding: 'var(--space-2)',
            borderRadius: 'var(--radius-full)',
            color: 'var(--text-muted)',
            cursor: 'pointer',
            display: 'flex',
          }}
        >
          <X size={18} />
        </button>
      </div>

      {/* Active Vehicle Context Indicator */}
      {currentVehicle && (
        <div
          style={{
            padding: 'var(--space-2) var(--space-4)',
            backgroundColor: 'var(--accent-blue-light)',
            fontSize: 'var(--font-size-xs)',
            color: 'var(--accent-blue)',
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--space-2)',
            borderBottom: '1px solid rgba(0, 102, 255, 0.1)',
          }}
        >
          <Sparkles size={14} />
          <span>
            Active Context: <strong>{currentVehicle.brand} {currentVehicle.model} {currentVehicle.year || ''}</strong>
          </span>
        </div>
      )}

      {/* Message History */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: 'var(--space-4)',
          display: 'flex',
          flexDirection: 'column',
          gap: 'var(--space-4)',
        }}
      >
        {messages.map((turn, i) => (
          <div
            key={i}
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: turn.role === 'user' ? 'flex-end' : 'flex-start',
              gap: 'var(--space-1)',
            }}
          >
            <div
              style={{
                maxWidth: '88%',
                padding: 'var(--space-3) var(--space-4)',
                borderRadius: 'var(--radius-xl)',
                backgroundColor: turn.role === 'user' ? 'var(--accent-blue)' : 'var(--bg-secondary)',
                color: turn.role === 'user' ? 'var(--text-inverse)' : 'var(--text-primary)',
                border: turn.role === 'assistant' ? '1px solid var(--border-light)' : 'none',
                fontSize: 'var(--font-size-sm)',
                lineHeight: 1.5,
              }}
            >
              <div style={{ whiteSpace: 'pre-wrap' }}>{turn.content}</div>

              {/* Citations */}
              {turn.citations && turn.citations.length > 0 && (
                <div style={{ marginTop: 'var(--space-3)', borderTop: '1px solid var(--border-light)', paddingTop: 'var(--space-2)' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 'var(--font-weight-bold)', marginBottom: 'var(--space-1)' }}>
                    GROUNDED CITATIONS
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-1)' }}>
                    {turn.citations.map((c, idx) => (
                      <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-1)', fontSize: '0.75rem' }}>
                        <EvidenceBadge state={c.evidence_state} size="sm" />
                        <span style={{ color: 'var(--text-secondary)' }}>{c.claim || c.title || c.id}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Suggested Next Actions */}
            {turn.nextActions && turn.nextActions.length > 0 && (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-1)', marginTop: 'var(--space-2)' }}>
                {turn.nextActions.map((action, aIdx) => (
                  <button
                    key={aIdx}
                    onClick={() => handleSend(action)}
                    style={{
                      fontSize: 'var(--font-size-xs)',
                      backgroundColor: 'var(--bg-tertiary)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: 'var(--radius-full)',
                      padding: 'var(--space-1) var(--space-3)',
                      color: 'var(--accent-blue)',
                      cursor: 'pointer',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: 'var(--space-1)',
                    }}
                  >
                    <span>{action}</span>
                    <ArrowRight size={10} />
                  </button>
                ))}
              </div>
            )}

            <span style={{ fontSize: '0.7rem', color: 'var(--text-subtle)', padding: '0 var(--space-1)' }}>
              {turn.timestamp}
            </span>
          </div>
        ))}

        {isLoading && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', color: 'var(--text-muted)', fontSize: 'var(--font-size-xs)' }}>
            <span
              style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                backgroundColor: 'var(--accent-blue)',
                animation: 'pulse 1s infinite',
              }}
            />
            Querying authoritative domain engines...
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Composer */}
      <div
        style={{
          padding: 'var(--space-3) var(--space-4)',
          borderTop: '1px solid var(--border-subtle)',
          backgroundColor: 'var(--bg-primary)',
        }}
      >
        <form
          onSubmit={e => {
            e.preventDefault();
            handleSend();
          }}
          style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}
        >
          <input
            type="text"
            value={inputQuery}
            onChange={e => setInputQuery(e.target.value)}
            placeholder="Ask about this car's value or deal..."
            aria-label="Message to CarSpective AI"
            style={{
              flex: 1,
              padding: 'var(--space-2) var(--space-3)',
              borderRadius: 'var(--radius-lg)',
              border: '1px solid var(--border-medium)',
              fontSize: 'var(--font-size-sm)',
              outline: 'none',
              fontFamily: 'inherit',
            }}
          />
          <Button
            type="submit"
            variant="primary"
            size="md"
            disabled={!inputQuery.trim() || isLoading}
            aria-label="Send message"
          >
            <Send size={16} />
          </Button>
        </form>
        <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', textAlign: 'center', marginTop: 'var(--space-1)' }}>
          Responses are strictly grounded in CarSpective verified evidence.
        </div>
      </div>
    </div>
  );
};
