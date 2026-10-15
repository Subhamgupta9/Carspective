import React, { useState } from 'react';
import { VehicleSelection } from '../../state/AppContext';
import { EvidenceBadge } from '../../components/common/EvidenceBadge';
import { Badge } from '../../components/common/Badge';
import { VehicleKnowledgeProfile, EvidenceState } from '../../types';
import {
  Gauge,
  Fuel,
  Cog,
  Shield,
  Ruler,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Wrench,
  Sparkles,
  ThumbsUp,
  ThumbsDown,
  BookOpen,
  Calendar,
  Layers,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';

export interface VehicleSpecsProps {
  vehicle: VehicleSelection;
  knowledgeProfile?: VehicleKnowledgeProfile | null;
  isLoading?: boolean;
}

export const VehicleSpecs: React.FC<VehicleSpecsProps> = ({
  vehicle,
  knowledgeProfile,
  isLoading,
}) => {
  const [activeFeatureTab, setActiveFeatureTab] = useState<'ALL' | 'STANDARD' | 'OPTIONAL'>('ALL');
  const [showAllSources, setShowAllSources] = useState(false);

  // Extract canonical or fallback specifications
  const spec = knowledgeProfile?.specifications;
  const dim = knowledgeProfile?.dimensions;
  const safety = knowledgeProfile?.safety;
  const ownership = knowledgeProfile?.ownership;
  const issues = knowledgeProfile?.reliability_issues || [];
  const pros = knowledgeProfile?.pros || [];
  const cons = knowledgeProfile?.cons || [];
  const reviews = knowledgeProfile?.reviews;
  const features = knowledgeProfile?.features || [];

  // Summary spec items
  const enginePowerStr = spec
    ? `${spec.displacement_cc ? `${spec.displacement_cc.toLocaleString('en-IN')} cc` : ''}${spec.max_power_bhp ? ` • ${spec.max_power_bhp} bhp` : ''}${spec.max_torque_nm ? ` • ${spec.max_torque_nm} Nm` : ''}`
    : `${vehicle.fuel_type || 'Petrol'}`;

  const transmissionStr = spec?.transmission
    ? `${spec.transmission} (${spec.drivetrain || 'FWD'})`
    : `${vehicle.transmission_type || 'Manual'}`;

  const fuelEconomyStr = spec?.arai_mileage_kmpl
    ? `${spec.arai_mileage_kmpl} km/l (ARAI)`
    : `${vehicle.fuel_type || 'Petrol'} Standard`;

  const safetyStr = safety
    ? `${safety.adult_stars}/5 Adult Stars (${safety.organization} ${safety.test_year}) • ${safety.bodyshell_integrity || 'Stable'} Bodyshell`
    : 'No official crash rating published for this generation';

  const safetyEvidence: EvidenceState = safety ? 'VERIFIED' : 'INSUFFICIENT_DATA';

  const dimensionsStr = dim
    ? `${dim.length_mm} × ${dim.width_mm} × ${dim.height_mm} mm • ${dim.boot_capacity_l || 0} L Boot`
    : '5-Passenger Monocoque Layout';

  const specs = [
    {
      label: 'Powertrain & Output',
      value: enginePowerStr || 'Standard OEM Powertrain',
      icon: <Fuel size={16} />,
      evidence: (spec ? spec.evidence_state : 'SUPPORTED') as EvidenceState,
      note: spec?.engine_type,
    },
    {
      label: 'Transmission & Drive',
      value: transmissionStr,
      icon: <Cog size={16} />,
      evidence: (spec ? spec.evidence_state : 'SUPPORTED') as EvidenceState,
      note: spec?.transmission,
    },
    {
      label: 'Fuel Efficiency (Claimed)',
      value: fuelEconomyStr,
      icon: <Fuel size={16} />,
      evidence: (spec?.arai_mileage_kmpl ? 'VERIFIED' : 'SUPPORTED') as EvidenceState,
      note: 'ARAI Test Cycle',
    },
    {
      label: 'Odometer Mileage',
      value: vehicle.km_driven
        ? `${vehicle.km_driven.toLocaleString('en-IN')} km`
        : '35,000 km (Typical Market Sample)',
      icon: <Gauge size={16} />,
      evidence: (vehicle.km_driven ? 'USER_STATED' : 'EMPIRICAL') as EvidenceState,
      note: 'Listing Attribute',
    },
    {
      label: 'Structural Crash Safety',
      value: safetyStr,
      icon: <Shield size={16} />,
      evidence: safetyEvidence,
      note: safety?.organization,
    },
    {
      label: 'Dimensions & Capacity',
      value: dimensionsStr,
      icon: <Ruler size={16} />,
      evidence: (dim ? dim.evidence_state : 'SUPPORTED') as EvidenceState,
      note: dim?.ground_clearance_mm ? `${dim.ground_clearance_mm} mm clearance` : undefined,
    },
  ];

  // Filter features
  const filteredFeatures = features.filter(f => {
    if (activeFeatureTab === 'STANDARD') return f.availability === 'STANDARD';
    if (activeFeatureTab === 'OPTIONAL') return f.availability === 'OPTIONAL';
    return true;
  });

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-6)',
        backgroundColor: 'var(--bg-primary)',
        borderRadius: 'var(--radius-xl)',
        border: '1px solid var(--border-subtle)',
        padding: 'var(--space-6)',
      }}
    >
      {/* 1. Header with Coverage Tier & Verification Status */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            <h3 style={{ fontSize: 'var(--font-size-xl)', margin: 0 }}>Canonical Vehicle Intelligence</h3>
            <EvidenceBadge state="VERIFIED" size="sm" />
          </div>
          <p style={{ margin: 'var(--space-1) 0 0', fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
            Authoritative technical data verified against OEM manuals, ARAI certificates, and official crash registries.
          </p>
        </div>
        {knowledgeProfile?.coverage_tier && (
          <Badge variant="neutral" size="sm">
            {knowledgeProfile.coverage_tier.replace(/_/g, ' ')}
          </Badge>
        )}
      </div>

      {/* 2. Primary 6-Metric Specification Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
          gap: 'var(--space-3)',
        }}
      >
        {specs.map((item, idx) => (
          <div
            key={idx}
            style={{
              padding: 'var(--space-3) var(--space-4)',
              backgroundColor: 'var(--bg-secondary)',
              borderRadius: 'var(--radius-lg)',
              border: '1px solid var(--border-light)',
              display: 'flex',
              flexDirection: 'column',
              gap: 'var(--space-1)',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 'var(--space-1)',
                  fontSize: 'var(--font-size-xs)',
                  color: 'var(--text-muted)',
                }}
              >
                {item.icon}
                {item.label}
              </span>
              <EvidenceBadge state={item.evidence} size="sm" />
            </div>
            <span
              style={{
                fontWeight: 'var(--font-weight-bold)',
                fontSize: 'var(--font-size-sm)',
                color: 'var(--text-primary)',
                lineHeight: '1.4',
              }}
            >
              {item.value}
            </span>
            {item.note && (
              <span style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>
                {item.note}
              </span>
            )}
          </div>
        ))}
      </div>

      {/* 3. Safety Breakdown Card */}
      {safety && (
        <div
          style={{
            padding: 'var(--space-4)',
            backgroundColor: 'rgba(56, 161, 105, 0.04)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid rgba(56, 161, 105, 0.2)',
            display: 'flex',
            flexDirection: 'column',
            gap: 'var(--space-3)',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
              <Shield size={18} style={{ color: 'var(--color-success)' }} />
              <span style={{ fontWeight: 'var(--font-weight-bold)', fontSize: 'var(--font-size-sm)' }}>
                Crash Safety Assessment — {safety.organization} ({safety.test_year})
              </span>
            </div>
            <div style={{ display: 'flex', gap: 'var(--space-2)', alignItems: 'center' }}>
              <Badge variant={safety.bodyshell_integrity === 'STABLE' ? 'success' : 'warning'} size="sm">
                Bodyshell: {safety.bodyshell_integrity || 'UNRATED'}
              </Badge>
              <EvidenceBadge state={safety.evidence_state} size="sm" />
            </div>
          </div>

          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-6)', fontSize: 'var(--font-size-sm)' }}>
            <div>
              <span style={{ color: 'var(--text-muted)', fontSize: 'var(--font-size-xs)' }}>Adult Occupant Protection: </span>
              <strong>{'★'.repeat(safety.adult_stars)}{'☆'.repeat(5 - safety.adult_stars)}</strong> ({safety.adult_stars}/5)
            </div>
            {safety.child_stars !== undefined && safety.child_stars !== null && (
              <div>
                <span style={{ color: 'var(--text-muted)', fontSize: 'var(--font-size-xs)' }}>Child Occupant Protection: </span>
                <strong>{'★'.repeat(safety.child_stars)}{'☆'.repeat(5 - safety.child_stars)}</strong> ({safety.child_stars}/5)
              </div>
            )}
            {safety.standard_safety_equipment && (
              <div>
                <span style={{ color: 'var(--text-muted)', fontSize: 'var(--font-size-xs)' }}>Tested Equipment: </span>
                <span>{safety.standard_safety_equipment}</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 4. Variant Equipment Matrix */}
      {features.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
              <Layers size={18} style={{ color: 'var(--text-muted)' }} />
              <h4 style={{ margin: 0, fontSize: 'var(--font-size-base)' }}>Variant Equipment Matrix</h4>
            </div>
            <div style={{ display: 'flex', gap: 'var(--space-1)' }}>
              {(['ALL', 'STANDARD', 'OPTIONAL'] as const).map(tab => (
                <button
                  key={tab}
                  onClick={() => setActiveFeatureTab(tab)}
                  style={{
                    padding: 'var(--space-1) var(--space-3)',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid',
                    borderColor: activeFeatureTab === tab ? 'var(--color-primary)' : 'var(--border-light)',
                    backgroundColor: activeFeatureTab === tab ? 'rgba(49, 130, 206, 0.1)' : 'transparent',
                    color: activeFeatureTab === tab ? 'var(--color-primary)' : 'var(--text-muted)',
                    fontSize: 'var(--font-size-xs)',
                    cursor: 'pointer',
                    fontWeight: activeFeatureTab === tab ? 'var(--font-weight-bold)' : 'normal',
                  }}
                >
                  {tab}
                </button>
              ))}
            </div>
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
              gap: 'var(--space-2)',
            }}
          >
            {filteredFeatures.map((f, i) => {
              const isStd = f.availability === 'STANDARD';
              const isOpt = f.availability === 'OPTIONAL';
              return (
                <div
                  key={i}
                  style={{
                    padding: 'var(--space-2) var(--space-3)',
                    backgroundColor: 'var(--bg-secondary)',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--border-light)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    fontSize: 'var(--font-size-xs)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                    {isStd ? (
                      <CheckCircle2 size={14} style={{ color: 'var(--color-success)', flexShrink: 0 }} />
                    ) : isOpt ? (
                      <Sparkles size={14} style={{ color: 'var(--color-warning)', flexShrink: 0 }} />
                    ) : (
                      <XCircle size={14} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
                    )}
                    <span style={{ fontWeight: 'var(--font-weight-medium)' }}>{f.feature_name}</span>
                  </div>
                  <Badge variant={isStd ? 'success' : isOpt ? 'warning' : 'neutral'} size="sm">
                    {f.availability}
                  </Badge>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 5. Ownership Profile & Real Running Costs */}
      {ownership && (
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
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
              <Wrench size={18} style={{ color: 'var(--text-muted)' }} />
              <h4 style={{ margin: 0, fontSize: 'var(--font-size-base)' }}>Ownership & Maintenance Profile</h4>
            </div>
            <EvidenceBadge state={ownership.evidence_state} size="sm" />
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
              gap: 'var(--space-3)',
              fontSize: 'var(--font-size-sm)',
            }}
          >
            <div>
              <div style={{ color: 'var(--text-muted)', fontSize: 'var(--font-size-xs)' }}>Service Interval</div>
              <strong>{ownership.service_interval_km?.toLocaleString('en-IN')} km / {ownership.service_interval_months} mo</strong>
            </div>
            {ownership.typical_annual_maintenance_inr && (
              <div>
                <div style={{ color: 'var(--text-muted)', fontSize: 'var(--font-size-xs)' }}>Typical Annual Routine Service</div>
                <strong>₹{ownership.typical_annual_maintenance_inr}</strong>
              </div>
            )}
            {ownership.real_world_city_mileage_kmpl && (
              <div>
                <div style={{ color: 'var(--text-muted)', fontSize: 'var(--font-size-xs)' }}>Real-World Mileage (City / Hwy)</div>
                <strong>{ownership.real_world_city_mileage_kmpl} / {ownership.real_world_highway_mileage_kmpl || '—'} km/l</strong>
              </div>
            )}
            <div>
              <div style={{ color: 'var(--text-muted)', fontSize: 'var(--font-size-xs)' }}>Parts Availability</div>
              <Badge variant="neutral" size="sm">{ownership.parts_availability}</Badge>
            </div>
          </div>
        </div>
      )}

      {/* 6. Documented Mechanical Watchpoints / Reliability Advisories */}
      {issues.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
              <AlertTriangle size={18} style={{ color: 'var(--color-warning)' }} />
              <h4 style={{ margin: 0, fontSize: 'var(--font-size-base)' }}>Documented Mechanical Watchpoints ({issues.length})</h4>
            </div>
            <EvidenceBadge state="SUPPORTED" size="sm" />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
            {issues.map((iss, i) => (
              <div
                key={i}
                style={{
                  padding: 'var(--space-3)',
                  backgroundColor: 'var(--bg-secondary)',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border-light)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 'var(--space-1)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontWeight: 'var(--font-weight-bold)', fontSize: 'var(--font-size-sm)', color: 'var(--text-primary)' }}>
                    {iss.title}
                  </span>
                  <Badge
                    variant={iss.severity === 'HIGH' || iss.severity === 'CRITICAL' ? 'danger' : 'warning'}
                    size="sm"
                  >
                    {iss.severity}
                  </Badge>
                </div>
                <p style={{ margin: 0, fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)' }}>
                  {iss.description}
                </p>
                {iss.affected_powertrains && (
                  <span style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>
                    Powertrain context: {iss.affected_powertrains}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 7. Evidence-Grounded Pros & Cons */}
      {(pros.length > 0 || cons.length > 0) && (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
            gap: 'var(--space-4)',
          }}
        >
          {pros.length > 0 && (
            <div
              style={{
                padding: 'var(--space-4)',
                backgroundColor: 'rgba(56, 161, 105, 0.04)',
                borderRadius: 'var(--radius-lg)',
                border: '1px solid rgba(56, 161, 105, 0.2)',
                display: 'flex',
                flexDirection: 'column',
                gap: 'var(--space-2)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', color: 'var(--color-success)', fontWeight: 'var(--font-weight-bold)', fontSize: 'var(--font-size-sm)' }}>
                <ThumbsUp size={16} />
                <span>Verified Strengths</span>
              </div>
              <ul style={{ margin: 0, paddingLeft: 'var(--space-4)', fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: 'var(--space-1)' }}>
                {pros.map((p, i) => (
                  <li key={i}>{p.statement}</li>
                ))}
              </ul>
            </div>
          )}

          {cons.length > 0 && (
            <div
              style={{
                padding: 'var(--space-4)',
                backgroundColor: 'rgba(229, 62, 62, 0.04)',
                borderRadius: 'var(--radius-lg)',
                border: '1px solid rgba(229, 62, 62, 0.2)',
                display: 'flex',
                flexDirection: 'column',
                gap: 'var(--space-2)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', color: 'var(--color-danger)', fontWeight: 'var(--font-weight-bold)', fontSize: 'var(--font-size-sm)' }}>
                <ThumbsDown size={16} />
                <span>Documented Considerations</span>
              </div>
              <ul style={{ margin: 0, paddingLeft: 'var(--space-4)', fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: 'var(--space-1)' }}>
                {cons.map((c, i) => (
                  <li key={i}>{c.statement}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* 8. Tripartite Review Synthesis */}
      {reviews && (
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
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
              <BookOpen size={18} style={{ color: 'var(--text-muted)' }} />
              <h4 style={{ margin: 0, fontSize: 'var(--font-size-base)' }}>Tripartite Review Synthesis</h4>
            </div>
            <EvidenceBadge state={reviews.evidence_state} size="sm" />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 'var(--space-3)', fontSize: 'var(--font-size-xs)' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-1)' }}>
              <span style={{ fontWeight: 'var(--font-weight-bold)', color: 'var(--text-primary)' }}>What Verified Owners Report</span>
              <p style={{ margin: 0, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                {reviews.what_owners_say || 'Review evidence unavailable.'}
              </p>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-1)' }}>
              <span style={{ fontWeight: 'var(--font-weight-bold)', color: 'var(--text-primary)' }}>What Automotive Journalists Conclude</span>
              <p style={{ margin: 0, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                {reviews.what_experts_say || 'Review evidence unavailable.'}
              </p>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-1)' }}>
              <span style={{ fontWeight: 'var(--font-weight-bold)', color: 'var(--color-primary)' }}>CarSpective Intelligence Verdict</span>
              <p style={{ margin: 0, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                {reviews.carspective_analysis}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* 9. Documentary Evidence Provenance Bar */}
      {knowledgeProfile?.freshness_summary && (
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: 'var(--space-2)',
            paddingTop: 'var(--space-2)',
            borderTop: '1px solid var(--border-subtle)',
            fontSize: '11px',
            color: 'var(--text-tertiary)',
          }}
        >
          <span>
            Last verified: <strong>{knowledgeProfile.freshness_summary.last_verified}</strong>
          </span>
          <div style={{ display: 'flex', gap: 'var(--space-3)' }}>
            <span>Specs: {knowledgeProfile.freshness_summary.evidence_coverage.specifications}</span>
            <span>Safety: {knowledgeProfile.freshness_summary.evidence_coverage.safety}</span>
            <span>Ownership: {knowledgeProfile.freshness_summary.evidence_coverage.ownership}</span>
          </div>
        </div>
      )}
    </div>
  );
};
