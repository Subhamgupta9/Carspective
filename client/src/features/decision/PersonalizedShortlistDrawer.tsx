import React, { useState, useEffect } from 'react';
import {
  UserRequirementsProfile,
  PersonalizedComparisonResponse,
  DecisionEvaluationResponse,
} from '../../types';
import { decisionApi } from '../../api/decisionApi';
import {
  Trophy,
  Heart,
  AlertCircle,
  X,
  ChevronRight,
  Sparkles,
  Scale,
  Shield,
  Fuel,
} from 'lucide-react';

export interface PersonalizedShortlistDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  shortlistIds: string[];
  onRemoveVehicle: (canonicalId: string) => void;
  profile: UserRequirementsProfile;
  onSelectVehicle?: (canonicalId: string) => void;
}

export const PersonalizedShortlistDrawer: React.FC<PersonalizedShortlistDrawerProps> = ({
  isOpen,
  onClose,
  shortlistIds,
  onRemoveVehicle,
  profile,
  onSelectVehicle,
}) => {
  const [comparison, setComparison] = useState<PersonalizedComparisonResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && shortlistIds.length >= 2) {
      loadComparison();
    }
  }, [isOpen, shortlistIds, profile]);

  const loadComparison = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await decisionApi.compareVehicles(shortlistIds.slice(0, 5), profile);
      setComparison(res);
    } catch (e: any) {
      setError('Failed to compute personalized comparison for shortlist.');
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        right: 0,
        bottom: 0,
        width: 'min(90vw, 680px)',
        background: '#ffffff',
        boxShadow: '-4px 0 20px rgba(0,0,0,0.15)',
        zIndex: 1000,
        display: 'flex',
        flexDirection: 'column',
      }}
      data-testid="personalized-shortlist-drawer"
    >
      {/* Drawer Header */}
      <div
        style={{
          padding: '16px 24px',
          borderBottom: '1px solid #e2e8f0',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          background: '#f8fafc',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Scale size={20} color="#2563eb" />
          <h3 style={{ margin: 0, fontSize: '1.2rem', fontWeight: 600 }}>
            Personalized Shortlist & Comparison ({shortlistIds.length})
          </h3>
        </div>
        <button
          onClick={onClose}
          style={{
            background: 'none',
            border: 'none',
            padding: '4px',
            cursor: 'pointer',
            color: '#64748b',
          }}
        >
          <X size={20} />
        </button>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '24px' }}>
        {shortlistIds.length < 2 ? (
          <div style={{ textAlign: 'center', padding: '40px 20px', color: '#64748b' }}>
            <AlertCircle size={36} color="#94a3b8" style={{ margin: '0 auto 12px' }} />
            <p style={{ margin: 0, fontWeight: 500 }}>Add at least 2 vehicles to your shortlist to compare.</p>
            <p style={{ fontSize: '0.85rem', color: '#94a3b8', marginTop: '4px' }}>
              We will deterministically analyze 'Best Vehicle Overall' vs 'Best For You'.
            </p>
          </div>
        ) : isLoading ? (
          <div style={{ textAlign: 'center', padding: '40px 20px', color: '#64748b' }}>
            <Sparkles size={32} color="#3b82f6" style={{ margin: '0 auto 12px', animation: 'spin 2s linear infinite' }} />
            <p>Evaluating multi-vehicle personalized suitability & constraints...</p>
          </div>
        ) : error ? (
          <div style={{ padding: '16px', background: '#fef2f2', color: '#b91c1c', borderRadius: '8px' }}>
            {error}
          </div>
        ) : comparison ? (
          <div>
            {/* Divergence Banner */}
            {comparison.divergence_explanation && (
              <div
                style={{
                  background: '#eff6ff',
                  border: '1px solid #bfdbfe',
                  borderRadius: '8px',
                  padding: '16px',
                  marginBottom: '24px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                  <Sparkles size={18} color="#2563eb" />
                  <strong style={{ color: '#1e40af', fontSize: '0.95rem' }}>Personalization Divergence Detected</strong>
                </div>
                <p style={{ margin: 0, fontSize: '0.85rem', color: '#1e3a8a', lineHeight: 1.5 }}>
                  {comparison.divergence_explanation}
                </p>
              </div>
            )}

            {/* Winner Badges */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '24px' }}>
              <div
                style={{
                  padding: '16px',
                  background: '#fefce8',
                  border: '1px solid #fde047',
                  borderRadius: '8px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#854d0e', marginBottom: '6px' }}>
                  <Trophy size={18} />
                  <strong style={{ fontSize: '0.85rem' }}>Best Vehicle Overall</strong>
                </div>
                <div style={{ fontSize: '1.05rem', fontWeight: 700, color: '#713f12' }}>
                  {comparison.vehicles[comparison.general_winner_index]?.vehicle_summary}
                </div>
                <p style={{ margin: '6px 0 0', fontSize: '0.8rem', color: '#a16207' }}>
                  Highest intrinsic score ({comparison.vehicles[comparison.general_winner_index]?.intrinsic_score}/100)
                </p>
              </div>

              <div
                style={{
                  padding: '16px',
                  background: '#f0fdf4',
                  border: '1px solid #86efac',
                  borderRadius: '8px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#166534', marginBottom: '6px' }}>
                  <Heart size={18} />
                  <strong style={{ fontSize: '0.85rem' }}>Best For You</strong>
                </div>
                <div style={{ fontSize: '1.05rem', fontWeight: 700, color: '#14532d' }}>
                  {comparison.vehicles[comparison.user_winner_index]?.vehicle_summary}
                </div>
                <p style={{ margin: '6px 0 0', fontSize: '0.8rem', color: '#15803d' }}>
                  Highest user fit ({comparison.vehicles[comparison.user_winner_index]?.user_fit_score}/100)
                </p>
              </div>
            </div>

            {/* Side-by-side List */}
            <h4 style={{ margin: '0 0 12px', fontSize: '1rem', fontWeight: 600, color: '#1e293b' }}>
              Ranked Shortlist Evaluation
            </h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {comparison.vehicles.map((v, idx) => {
                const isUserWinner = idx === comparison.user_winner_index;
                const isGenWinner = idx === comparison.general_winner_index;
                const isFail = v.hard_constraint_status === 'FAIL';

                return (
                  <div
                    key={v.canonical_vehicle_id}
                    style={{
                      border: isUserWinner ? '2px solid #22c55e' : '1px solid #e2e8f0',
                      borderRadius: '8px',
                      padding: '16px',
                      background: '#ffffff',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ fontWeight: 700, fontSize: '1rem', color: '#0f172a' }}>
                            {v.vehicle_summary}
                          </span>
                          {isUserWinner && (
                            <span
                              style={{
                                fontSize: '0.7rem',
                                background: '#dcfce7',
                                color: '#15803d',
                                padding: '2px 6px',
                                borderRadius: '4px',
                                fontWeight: 700,
                              }}
                            >
                              ★ Top Match For You
                            </span>
                          )}
                          {isGenWinner && (
                            <span
                              style={{
                                fontSize: '0.7rem',
                                background: '#fef9c3',
                                color: '#854d0e',
                                padding: '2px 6px',
                                borderRadius: '4px',
                                fontWeight: 700,
                              }}
                            >
                              🏆 Best Engineering
                            </span>
                          )}
                        </div>
                        <div style={{ fontSize: '0.8rem', color: '#64748b', marginTop: '2px' }}>
                          {v.verdict_label}
                        </div>
                      </div>

                      <div style={{ textAlign: 'right' }}>
                        <div style={{ fontSize: '1.2rem', fontWeight: 800, color: isFail ? '#dc2626' : '#2563eb' }}>
                          {v.user_fit_score}
                          <span style={{ fontSize: '0.75rem', fontWeight: 500, color: '#94a3b8' }}>/100 Fit</span>
                        </div>
                        <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
                          Intrinsic: {v.intrinsic_score || 'N/A'}/100
                        </div>
                      </div>
                    </div>

                    {/* Constraints / Why / Tradeoffs summary */}
                    <div style={{ marginTop: '12px', fontSize: '0.85rem' }}>
                      {isFail ? (
                        <p style={{ margin: 0, color: '#b91c1c' }}>
                          ⚠️ {v.why_it_may_not_fit[0] || 'Violates stated constraint.'}
                        </p>
                      ) : (
                        <p style={{ margin: 0, color: '#166534' }}>
                          ✓ {v.why_it_fits[0] || 'Aligns with your primary usage profile.'}
                        </p>
                      )}
                    </div>

                    <div style={{ marginTop: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <button
                        onClick={() => onRemoveVehicle(v.canonical_vehicle_id)}
                        style={{
                          background: 'none',
                          border: 'none',
                          color: '#94a3b8',
                          fontSize: '0.8rem',
                          cursor: 'pointer',
                        }}
                      >
                        Remove
                      </button>

                      {onSelectVehicle && (
                        <button
                          onClick={() => onSelectVehicle(v.canonical_vehicle_id)}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px',
                            background: '#eff6ff',
                            border: '1px solid #bfdbfe',
                            color: '#1d4ed8',
                            padding: '4px 10px',
                            borderRadius: '6px',
                            fontSize: '0.8rem',
                            fontWeight: 500,
                            cursor: 'pointer',
                          }}
                        >
                          View Workspace <ChevronRight size={14} />
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
};
