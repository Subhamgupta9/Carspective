import React, { useState } from 'react';
import {
  UserRequirementsProfile,
  PriorityLevel,
  UsageProfile,
  NaturalLanguageRequirementsResponse,
} from '../../types';
import { decisionApi } from '../../api/decisionApi';
import {
  Sliders,
  Sparkles,
  Shield,
  Wrench,
  Fuel,
  Users,
  Compass,
  CheckCircle2,
  AlertCircle,
  RotateCcw,
} from 'lucide-react';

export interface RequirementsEditorProps {
  profile: UserRequirementsProfile;
  onChange: (updated: UserRequirementsProfile) => void;
  onClose?: () => void;
}

export const RequirementsEditor: React.FC<RequirementsEditorProps> = ({
  profile,
  onChange,
  onClose,
}) => {
  const [nlQuery, setNlQuery] = useState('');
  const [isParsing, setIsParsing] = useState(false);
  const [parseError, setParseError] = useState<string | null>(null);
  const [clarifications, setClarifications] = useState<string[]>([]);

  const handleNlParse = async () => {
    if (!nlQuery.trim()) return;
    setIsParsing(true);
    setParseError(null);
    setClarifications([]);
    try {
      const res: NaturalLanguageRequirementsResponse = await decisionApi.parseQuery(nlQuery);
      onChange({
        ...profile,
        ...res.parsed_profile,
        hard_constraints: {
          ...profile.hard_constraints,
          ...res.parsed_profile.hard_constraints,
        },
      });
      if (res.clarification_questions && res.clarification_questions.length > 0) {
        setClarifications(res.clarification_questions);
      }
    } catch (e: any) {
      setParseError('Failed to parse plain language requirements. Please try again.');
    } finally {
      setIsParsing(false);
    }
  };

  const handleReset = () => {
    onChange({
      budget_min_inr: undefined,
      budget_max_inr: undefined,
      budget_flexible: false,
      monthly_running_budget_max_inr: undefined,
      purchase_type: 'NOT_SPECIFIED',
      usage_profile: 'NOT_SPECIFIED',
      annual_km: undefined,
      family_size: undefined,
      fuel_preferences: [],
      transmission_preferences: [],
      body_type_preferences: [],
      safety_priority: 'NOT_SPECIFIED',
      reliability_priority: 'NOT_SPECIFIED',
      maintenance_priority: 'NOT_SPECIFIED',
      practicality_priority: 'NOT_SPECIFIED',
      resale_priority: 'NOT_SPECIFIED',
      performance_priority: 'NOT_SPECIFIED',
      efficiency_priority: 'NOT_SPECIFIED',
      value_priority: 'NOT_SPECIFIED',
      ownership_years: undefined,
      maintenance_tolerance: 'NOT_SPECIFIED',
      hard_constraints: {
        strict_budget_ceiling: false,
        strict_transmission: false,
        strict_fuel_type: false,
        strict_min_seating: false,
        strict_body_type: false,
      },
      provenance_map: {},
    });
    setNlQuery('');
    setClarifications([]);
  };

  const priorityOptions: PriorityLevel[] = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'];

  const toggleArrayItem = (arr: string[] = [], item: string): string[] => {
    return arr.includes(item) ? arr.filter((x) => x !== item) : [...arr, item];
  };

  const updateFieldWithProvenance = (fieldKey: string, partial: Partial<UserRequirementsProfile>) => {
    const currentProv = profile.provenance_map || {};
    onChange({
      ...profile,
      ...partial,
      provenance_map: {
        ...currentProv,
        [fieldKey]: { state: 'USER_EXPLICIT' },
      },
    });
  };

  const renderProvenanceChip = (fieldKey: string) => {
    const prov = profile.provenance_map?.[fieldKey];
    const state = prov?.state || 'NOT_SPECIFIED';
    let bg = '#f1f5f9';
    let color = '#64748b';
    let label = 'Not specified';

    if (state === 'USER_EXPLICIT') {
      bg = '#dbeafe';
      color = '#1d4ed8';
      label = 'You specified';
    } else if (state === 'USER_INFERRED') {
      bg = '#fef3c7';
      color = '#b45309';
      label = 'Inferred from prompt';
    } else if (state === 'SYSTEM_DEFAULT') {
      bg = '#f1f5f9';
      color = '#475569';
      label = 'Default';
    }

    return (
      <span
        data-testid={`provenance-${fieldKey}`}
        style={{
          fontSize: '10px',
          padding: '2px 6px',
          borderRadius: '4px',
          backgroundColor: bg,
          color: color,
          fontWeight: 600,
          textTransform: 'uppercase',
          letterSpacing: '0.04em',
          marginLeft: 'auto',
        }}
        title={`Provenance: ${state}`}
      >
        {label}
      </span>
    );
  };

  return (
    <div
      style={{
        background: 'var(--bg-surface, #ffffff)',
        border: '1px solid var(--border-subtle, #e2e8f0)',
        borderRadius: 'var(--radius-lg, 12px)',
        padding: 'var(--space-6, 24px)',
        boxShadow: 'var(--shadow-md, 0 4px 6px -1px rgba(0,0,0,0.1))',
      }}
      data-testid="requirements-editor"
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 'var(--space-4, 16px)',
          borderBottom: '1px solid var(--border-subtle, #e2e8f0)',
          paddingBottom: 'var(--space-3, 12px)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Sliders size={20} color="var(--brand-primary, #1e40af)" />
          <h3 style={{ margin: 0, fontSize: '1.2rem', fontWeight: 600 }}>Personalized Decision Profile</h3>
        </div>
        <button
          onClick={handleReset}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            background: 'none',
            border: 'none',
            color: 'var(--text-muted, #64748b)',
            cursor: 'pointer',
            fontSize: '0.85rem',
          }}
          title="Reset all preferences"
        >
          <RotateCcw size={14} /> Reset
        </button>
      </div>

      {/* Natural Language Prompt Assistant */}
      <div
        style={{
          background: 'var(--bg-subtle, #f8fafc)',
          padding: 'var(--space-4, 16px)',
          borderRadius: 'var(--radius-md, 8px)',
          marginBottom: 'var(--space-5, 20px)',
          border: '1px solid var(--border-subtle, #e2e8f0)',
        }}
      >
        <label
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: '0.9rem',
            fontWeight: 600,
            color: 'var(--text-primary, #1e293b)',
            marginBottom: '6px',
          }}
        >
          <Sparkles size={16} color="var(--brand-primary, #3b82f6)" />
          Describe What You Need (Plain English)
        </label>
        <div style={{ display: 'flex', gap: '8px' }}>
          <input
            type="text"
            value={nlQuery}
            onChange={(e) => setNlQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleNlParse()}
            placeholder="e.g. 'I need an automatic SUV under 12 lakh with 5-star safety for city commute'"
            style={{
              flex: 1,
              padding: '8px 12px',
              borderRadius: '6px',
              border: '1px solid var(--border-default, #cbd5e1)',
              fontSize: '0.9rem',
            }}
          />
          <button
            onClick={handleNlParse}
            disabled={isParsing || !nlQuery.trim()}
            style={{
              padding: '8px 16px',
              background: 'var(--brand-primary, #2563eb)',
              color: '#ffffff',
              border: 'none',
              borderRadius: '6px',
              fontWeight: 500,
              cursor: isParsing ? 'wait' : 'pointer',
            }}
          >
            {isParsing ? 'Parsing...' : 'Apply'}
          </button>
        </div>
        {parseError && (
          <p style={{ color: 'var(--status-fail, #dc2626)', fontSize: '0.8rem', marginTop: '6px' }}>{parseError}</p>
        )}
        {clarifications.length > 0 && (
          <div style={{ marginTop: '8px', padding: '8px', background: '#fef3c7', borderRadius: '6px' }}>
            {clarifications.map((q, i) => (
              <p key={i} style={{ margin: 0, fontSize: '0.85rem', color: '#92400e' }}>
                💡 {q}
              </p>
            ))}
          </div>
        )}
      </div>

      {/* Grid of Profile Controls with Visibly Retained Provenance */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '20px' }}>
        {/* 1. Budget Section */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <label style={{ fontWeight: 600, fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span>Acquisition Budget Ceiling (INR)</span>
            {renderProvenanceChip('budget')}
          </label>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <input
              type="number"
              placeholder="e.g. 1000000"
              value={profile.budget_max_inr || ''}
              onChange={(e) =>
                updateFieldWithProvenance('budget', {
                  budget_max_inr: e.target.value ? parseFloat(e.target.value) : undefined,
                })
              }
              style={{
                flex: 1,
                padding: '8px 12px',
                borderRadius: '6px',
                border: '1px solid var(--border-default, #cbd5e1)',
              }}
            />
            {profile.budget_max_inr ? (
              <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--brand-primary, #2563eb)' }}>
                ₹{(profile.budget_max_inr / 100000).toFixed(1)}L
              </span>
            ) : null}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '4px' }}>
            <input
              type="checkbox"
              id="budget-flex"
              checked={profile.budget_flexible || false}
              onChange={(e) => updateFieldWithProvenance('budget', { budget_flexible: e.target.checked })}
            />
            <label htmlFor="budget-flex" style={{ fontSize: '0.85rem', color: 'var(--text-muted, #475569)' }}>
              Flexible ceiling (allow +10% stretch)
            </label>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <input
              type="checkbox"
              id="strict-budget"
              checked={profile.hard_constraints?.strict_budget_ceiling || false}
              onChange={(e) =>
                updateFieldWithProvenance('budget', {
                  hard_constraints: {
                    ...profile.hard_constraints,
                    strict_budget_ceiling: e.target.checked,
                  } as any,
                })
              }
            />
            <label htmlFor="strict-budget" style={{ fontSize: '0.85rem', color: '#b91c1c', fontWeight: 500 }}>
              Enforce strict budget cutoff (Hard constraint)
            </label>
          </div>
        </div>

        {/* 2. Usage & Transmission */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <label style={{ fontWeight: 600, fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Compass size={16} /> Primary Driving Usage
            {renderProvenanceChip('usage')}
          </label>
          <div style={{ display: 'flex', gap: '8px' }}>
            {(['CITY', 'HIGHWAY', 'MIXED'] as UsageProfile[]).map((u) => (
              <button
                key={u}
                type="button"
                onClick={() => updateFieldWithProvenance('usage', { usage_profile: u })}
                style={{
                  flex: 1,
                  padding: '6px 10px',
                  borderRadius: '6px',
                  border: profile.usage_profile === u ? '2px solid #2563eb' : '1px solid #cbd5e1',
                  background: profile.usage_profile === u ? '#eff6ff' : '#ffffff',
                  color: profile.usage_profile === u ? '#1d4ed8' : '#334155',
                  fontWeight: profile.usage_profile === u ? 600 : 400,
                  cursor: 'pointer',
                  fontSize: '0.85rem',
                }}
              >
                {u}
              </button>
            ))}
          </div>

          <label style={{ fontWeight: 600, fontSize: '0.9rem', marginTop: '6px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span>Transmission Preference</span>
            {renderProvenanceChip('transmission')}
          </label>
          <div style={{ display: 'flex', gap: '8px' }}>
            {['Automatic', 'Manual'].map((t) => {
              const active = profile.transmission_preferences?.includes(t);
              return (
                <button
                  key={t}
                  type="button"
                  onClick={() =>
                    updateFieldWithProvenance('transmission', {
                      transmission_preferences: toggleArrayItem(profile.transmission_preferences, t),
                    })
                  }
                  style={{
                    flex: 1,
                    padding: '6px 10px',
                    borderRadius: '6px',
                    border: active ? '2px solid #2563eb' : '1px solid #cbd5e1',
                    background: active ? '#eff6ff' : '#ffffff',
                    color: active ? '#1d4ed8' : '#334155',
                    fontWeight: active ? 600 : 400,
                    cursor: 'pointer',
                    fontSize: '0.85rem',
                  }}
                >
                  {t}
                </button>
              );
            })}
          </div>
        </div>

        {/* 3. Fuel & Family Size */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <label style={{ fontWeight: 600, fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Fuel size={16} /> Fuel Preferences
            {renderProvenanceChip('fuel')}
          </label>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
            {['Petrol', 'Diesel', 'CNG', 'Electric'].map((f) => {
              const active = profile.fuel_preferences?.includes(f);
              return (
                <button
                  key={f}
                  type="button"
                  onClick={() =>
                    updateFieldWithProvenance('fuel', {
                      fuel_preferences: toggleArrayItem(profile.fuel_preferences, f),
                    })
                  }
                  style={{
                    padding: '4px 10px',
                    borderRadius: '6px',
                    border: active ? '2px solid #2563eb' : '1px solid #cbd5e1',
                    background: active ? '#eff6ff' : '#ffffff',
                    color: active ? '#1d4ed8' : '#334155',
                    fontSize: '0.85rem',
                    cursor: 'pointer',
                  }}
                >
                  {f}
                </button>
              );
            })}
          </div>

          <label style={{ fontWeight: 600, fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '6px', marginTop: '6px' }}>
            <Users size={16} /> Family / Occupants (Seats)
            {renderProvenanceChip('family_size')}
          </label>
          <div style={{ display: 'flex', gap: '6px' }}>
            {[2, 4, 5, 7].map((num) => (
              <button
                key={num}
                type="button"
                onClick={() => updateFieldWithProvenance('family_size', { family_size: num })}
                style={{
                  flex: 1,
                  padding: '6px 8px',
                  borderRadius: '6px',
                  border: profile.family_size === num ? '2px solid #2563eb' : '1px solid #cbd5e1',
                  background: profile.family_size === num ? '#eff6ff' : '#ffffff',
                  color: profile.family_size === num ? '#1d4ed8' : '#334155',
                  fontSize: '0.85rem',
                  fontWeight: profile.family_size === num ? 600 : 400,
                  cursor: 'pointer',
                }}
              >
                {num} seats
              </button>
            ))}
          </div>
        </div>

        {/* 4. Annual KM & Ownership Horizon */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <label style={{ fontWeight: 600, fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span>Annual Driving Distance (km/year)</span>
            {renderProvenanceChip('annual_km')}
          </label>
          <div style={{ display: 'flex', gap: '6px' }}>
            {[8000, 12000, 18000, 25000].map((km) => (
              <button
                key={km}
                type="button"
                onClick={() => updateFieldWithProvenance('annual_km', { annual_km: km })}
                style={{
                  flex: 1,
                  padding: '6px 4px',
                  borderRadius: '6px',
                  border: profile.annual_km === km ? '2px solid #2563eb' : '1px solid #cbd5e1',
                  background: profile.annual_km === km ? '#eff6ff' : '#ffffff',
                  color: profile.annual_km === km ? '#1d4ed8' : '#334155',
                  fontSize: '0.75rem',
                  fontWeight: profile.annual_km === km ? 600 : 400,
                  cursor: 'pointer',
                }}
              >
                {km / 1000}k km
              </button>
            ))}
          </div>

          <label style={{ fontWeight: 600, fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '6px', marginTop: '6px' }}>
            <span>Planned Ownership Horizon</span>
            {renderProvenanceChip('ownership_years')}
          </label>
          <div style={{ display: 'flex', gap: '6px' }}>
            {[3, 5, 7, 10].map((yrs) => (
              <button
                key={yrs}
                type="button"
                onClick={() => updateFieldWithProvenance('ownership_years', { ownership_years: yrs })}
                style={{
                  flex: 1,
                  padding: '6px 8px',
                  borderRadius: '6px',
                  border: profile.ownership_years === yrs ? '2px solid #2563eb' : '1px solid #cbd5e1',
                  background: profile.ownership_years === yrs ? '#eff6ff' : '#ffffff',
                  color: profile.ownership_years === yrs ? '#1d4ed8' : '#334155',
                  fontSize: '0.8rem',
                  fontWeight: profile.ownership_years === yrs ? 600 : 400,
                  cursor: 'pointer',
                }}
              >
                {yrs} Yrs
              </button>
            ))}
          </div>
        </div>

        {/* 5. Body Type Preferences */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <label style={{ fontWeight: 600, fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span>Body Type Preference</span>
            {renderProvenanceChip('body_type')}
          </label>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
            {['Hatchback', 'Sedan', 'SUV', 'MUV'].map((b) => {
              const active = profile.body_type_preferences?.includes(b);
              return (
                <button
                  key={b}
                  type="button"
                  onClick={() =>
                    updateFieldWithProvenance('body_type', {
                      body_type_preferences: toggleArrayItem(profile.body_type_preferences, b),
                    })
                  }
                  style={{
                    padding: '4px 10px',
                    borderRadius: '6px',
                    border: active ? '2px solid #2563eb' : '1px solid #cbd5e1',
                    background: active ? '#eff6ff' : '#ffffff',
                    color: active ? '#1d4ed8' : '#334155',
                    fontSize: '0.85rem',
                    cursor: 'pointer',
                  }}
                >
                  {b}
                </button>
              );
            })}
          </div>
        </div>

        {/* 6. Priorities Section */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <label style={{ fontWeight: 600, fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Shield size={16} /> Safety Priority
            {renderProvenanceChip('safety_priority')}
          </label>
          <div style={{ display: 'flex', gap: '4px' }}>
            {priorityOptions.map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => updateFieldWithProvenance('safety_priority', { safety_priority: p })}
                style={{
                  flex: 1,
                  padding: '4px 6px',
                  borderRadius: '4px',
                  border: profile.safety_priority === p ? '2px solid #16a34a' : '1px solid #cbd5e1',
                  background: profile.safety_priority === p ? '#f0fdf4' : '#ffffff',
                  color: profile.safety_priority === p ? '#15803d' : '#334155',
                  fontSize: '0.75rem',
                  fontWeight: profile.safety_priority === p ? 600 : 400,
                  cursor: 'pointer',
                }}
              >
                {p}
              </button>
            ))}
          </div>

          <label style={{ fontWeight: 600, fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '6px', marginTop: '4px' }}>
            <Wrench size={16} /> Maintenance Sensitivity
            {renderProvenanceChip('maintenance_priority')}
          </label>
          <div style={{ display: 'flex', gap: '4px' }}>
            {priorityOptions.map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => updateFieldWithProvenance('maintenance_priority', { maintenance_priority: p })}
                style={{
                  flex: 1,
                  padding: '4px 6px',
                  borderRadius: '4px',
                  border: profile.maintenance_priority === p ? '2px solid #16a34a' : '1px solid #cbd5e1',
                  background: profile.maintenance_priority === p ? '#f0fdf4' : '#ffffff',
                  color: profile.maintenance_priority === p ? '#15803d' : '#334155',
                  fontSize: '0.75rem',
                  fontWeight: profile.maintenance_priority === p ? 600 : 400,
                  cursor: 'pointer',
                }}
              >
                {p}
              </button>
            ))}
          </div>

          <label style={{ fontWeight: 600, fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '6px', marginTop: '4px' }}>
            <span>Resale / Liquidity Priority</span>
            {renderProvenanceChip('resale_priority')}
          </label>
          <div style={{ display: 'flex', gap: '4px' }}>
            {priorityOptions.map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => updateFieldWithProvenance('resale_priority', { resale_priority: p })}
                style={{
                  flex: 1,
                  padding: '4px 6px',
                  borderRadius: '4px',
                  border: profile.resale_priority === p ? '2px solid #16a34a' : '1px solid #cbd5e1',
                  background: profile.resale_priority === p ? '#f0fdf4' : '#ffffff',
                  color: profile.safety_priority === p ? '#15803d' : '#334155',
                  fontSize: '0.75rem',
                  fontWeight: profile.resale_priority === p ? 600 : 400,
                  cursor: 'pointer',
                }}
              >
                {p}
              </button>
            ))}
          </div>
        </div>
      </div>

      {onClose && (
        <div style={{ marginTop: '20px', display: 'flex', justifyContent: 'flex-end' }}>
          <button
            onClick={onClose}
            style={{
              padding: '8px 20px',
              background: 'var(--brand-primary, #2563eb)',
              color: '#ffffff',
              border: 'none',
              borderRadius: '6px',
              fontWeight: 500,
              cursor: 'pointer',
            }}
          >
            Apply & Close
          </button>
        </div>
      )}
    </div>
  );
};
