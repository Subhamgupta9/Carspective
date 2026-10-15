import React from 'react';
import { VehicleKnowledgeProfile, EvidenceState } from '../../../types';
import { EvidenceBadge } from '../../../components/common/EvidenceBadge';
import { Gauge, Fuel, Ruler, Cog, Shield, HelpCircle } from 'lucide-react';

export interface KeySpecsSectionProps {
  knowledge?: VehicleKnowledgeProfile | null;
  defaultFuel?: string;
  defaultTransmission?: string;
}

export const KeySpecsSection: React.FC<KeySpecsSectionProps> = ({
  knowledge,
  defaultFuel = 'Petrol',
  defaultTransmission = 'Manual',
}) => {
  const spec = knowledge?.specifications;
  const dim = knowledge?.dimensions;

  const specEvidence = (spec?.evidence_state as EvidenceState) || 'SUPPORTED';
  const dimEvidence = (dim?.evidence_state as EvidenceState) || 'SUPPORTED';

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
            <Gauge size={20} style={{ color: 'var(--color-primary)' }} />
            <h3 style={{ margin: 0, fontSize: 'var(--font-size-xl)' }}>
              Verified Specifications & Dimensions
            </h3>
          </div>
          <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
            Empirically documented engineering parameters with evidence provenance
          </span>
        </div>

        <EvidenceBadge state={spec ? specEvidence : 'INSUFFICIENT_DATA'} size="sm" />
      </div>

      {/* Grid of Spec Categories */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: 'var(--space-4)',
        }}
      >
        {/* Category 1: Powertrain & Output */}
        <div
          style={{
            padding: 'var(--space-4)',
            backgroundColor: 'var(--bg-primary)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--border-subtle)',
            display: 'flex',
            flexDirection: 'column',
            gap: 'var(--space-3)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', color: 'var(--color-primary)', fontWeight: 'var(--font-weight-semibold)', fontSize: 'var(--font-size-sm)' }}>
            <Fuel size={16} />
            <span>Powertrain & Engine</span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-2)', fontSize: 'var(--font-size-xs)' }}>
            <div>
              <span style={{ color: 'var(--text-muted)', display: 'block' }}>Engine</span>
              <strong>{spec?.displacement_cc ? `${spec.displacement_cc.toLocaleString('en-IN')} cc` : 'Unavailable'}</strong>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)', display: 'block' }}>Max Power</span>
              <strong>
                {spec?.max_power_bhp
                  ? `${spec.max_power_bhp} bhp ${spec.max_power_rpm ? `@ ${spec.max_power_rpm} rpm` : ''}`
                  : 'Unavailable'}
              </strong>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)', display: 'block' }}>Max Torque</span>
              <strong>
                {spec?.max_torque_nm
                  ? `${spec.max_torque_nm} Nm ${spec.max_torque_rpm ? `@ ${spec.max_torque_rpm} rpm` : ''}`
                  : 'Unavailable'}
              </strong>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)', display: 'block' }}>Configuration</span>
              <strong>{spec?.cylinders ? `${spec.cylinders} Cylinders` : 'Unavailable'}</strong>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)', display: 'block' }}>Aspiration</span>
              <strong>{spec?.aspiration || 'Naturally Aspirated'}</strong>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)', display: 'block' }}>Fuel Type</span>
              <strong>{spec?.fuel_type || defaultFuel}</strong>
            </div>
          </div>
        </div>

        {/* Category 2: Transmission & Drivetrain */}
        <div
          style={{
            padding: 'var(--space-4)',
            backgroundColor: 'var(--bg-primary)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--border-subtle)',
            display: 'flex',
            flexDirection: 'column',
            gap: 'var(--space-3)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', color: 'var(--accent-blue)', fontWeight: 'var(--font-weight-semibold)', fontSize: 'var(--font-size-sm)' }}>
            <Cog size={16} />
            <span>Transmission & Layout</span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-2)', fontSize: 'var(--font-size-xs)' }}>
            <div>
              <span style={{ color: 'var(--text-muted)', display: 'block' }}>Transmission</span>
              <strong>{spec?.transmission || defaultTransmission}</strong>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)', display: 'block' }}>Drivetrain</span>
              <strong>{spec?.drivetrain || 'FWD'}</strong>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)', display: 'block' }}>ARAI Mileage</span>
              <strong>{spec?.arai_mileage_kmpl ? `${spec.arai_mileage_kmpl} km/l` : 'Unavailable'}</strong>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)', display: 'block' }}>Fuel Tank</span>
              <strong>{spec?.fuel_tank_capacity_l ? `${spec.fuel_tank_capacity_l} Litres` : 'Unavailable'}</strong>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)', display: 'block' }}>Emission Norm</span>
              <strong>{spec?.emission_norm || 'BS6'}</strong>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)', display: 'block' }}>Body Type</span>
              <strong>{knowledge?.body_type || 'Hatchback'}</strong>
            </div>
          </div>
        </div>

        {/* Category 3: Exterior Dimensions & Practicality */}
        <div
          style={{
            padding: 'var(--space-4)',
            backgroundColor: 'var(--bg-primary)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--border-subtle)',
            display: 'flex',
            flexDirection: 'column',
            gap: 'var(--space-3)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', color: 'var(--color-success)', fontWeight: 'var(--font-weight-semibold)', fontSize: 'var(--font-size-sm)' }}>
            <Ruler size={16} />
            <span>Dimensions & Practicality</span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-2)', fontSize: 'var(--font-size-xs)' }}>
            <div>
              <span style={{ color: 'var(--text-muted)', display: 'block' }}>Dimensions (L×W×H)</span>
              <strong>
                {dim ? `${dim.length_mm} × ${dim.width_mm} × ${dim.height_mm} mm` : 'Unavailable'}
              </strong>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)', display: 'block' }}>Wheelbase</span>
              <strong>{dim?.wheelbase_mm ? `${dim.wheelbase_mm} mm` : 'Unavailable'}</strong>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)', display: 'block' }}>Ground Clearance</span>
              <strong>{dim?.ground_clearance_mm ? `${dim.ground_clearance_mm} mm` : 'Unavailable'}</strong>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)', display: 'block' }}>Boot Space</span>
              <strong>{dim?.boot_capacity_l ? `${dim.boot_capacity_l} Litres` : 'Unavailable'}</strong>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)', display: 'block' }}>Seating Capacity</span>
              <strong>{dim?.seating_capacity ? `${dim.seating_capacity} Persons` : '5 Persons'}</strong>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)', display: 'block' }}>Kerb Weight</span>
              <strong>{dim?.kerb_weight_kg ? `${dim.kerb_weight_kg} kg` : 'Unavailable'}</strong>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
