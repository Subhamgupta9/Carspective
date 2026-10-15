import React, { useState } from 'react';
import {
  OwnershipProfile,
  VehicleOwnershipIntelligence,
  EvidenceState,
  TCOHorizonSummary,
} from '../../../types';
import { Badge } from '../../../components/common/Badge';
import { EvidenceBadge } from '../../../components/common/EvidenceBadge';
import {
  Wrench,
  Fuel,
  Calculator,
  ShieldAlert,
  ThumbsUp,
  ThumbsDown,
  Info,
  DollarSign,
  TrendingUp,
  Sliders,
  CheckCircle2,
} from 'lucide-react';

export interface OwnershipSectionProps {
  ownership?: OwnershipProfile | null;
  ownershipIntelligence?: VehicleOwnershipIntelligence | null;
}

export const OwnershipSection: React.FC<OwnershipSectionProps> = ({
  ownership,
  ownershipIntelligence,
}) => {
  // Horizon selection for TCO: 1, 3, or 5 years
  const [selectedHorizon, setSelectedHorizon] = useState<1 | 3 | 5>(5);

  // Fuel Cost Calculator state
  const defaultCityMileage = ownershipIntelligence?.fuel?.real_world_city_kmpl || 14;
  const defaultHwyMileage = ownershipIntelligence?.fuel?.real_world_highway_kmpl || 18;
  const defaultCombined =
    ownershipIntelligence?.fuel?.real_world_combined_kmpl ||
    Math.round(((defaultCityMileage + defaultHwyMileage) / 2) * 10) / 10;

  const [monthlyKm, setMonthlyKm] = useState<number>(1000);
  const [mileageKmpl, setMileageKmpl] = useState<number>(defaultCombined);
  const fuelType = ownershipIntelligence?.fuel?.fuel_type?.toUpperCase() || 'PETROL';

  const defaultPrice = fuelType.includes('DIESEL')
    ? 89.62
    : fuelType.includes('CNG')
    ? 75.59
    : 96.72;
  const [fuelPricePerLitre, setFuelPricePerLitre] = useState<number>(defaultPrice);

  // Computed interactive fuel values
  const monthlyLitres = mileageKmpl > 0 ? monthlyKm / mileageKmpl : 0;
  const monthlyFuelCost = monthlyLitres * fuelPricePerLitre;
  const annualFuelCost = monthlyFuelCost * 12;
  const fuelCostPerKm = monthlyKm > 0 ? monthlyFuelCost / monthlyKm : 0;

  // TCO Horizon Selection
  const currentTco: TCOHorizonSummary | undefined =
    selectedHorizon === 1
      ? ownershipIntelligence?.tco_1_year
      : selectedHorizon === 3
      ? ownershipIntelligence?.tco_3_year
      : ownershipIntelligence?.tco_5_year;

  const riskSignals = ownershipIntelligence?.risk_signals || [];
  const routineSchedule = ownershipIntelligence?.maintenance?.routine_schedule || [];

  if (!ownership && !ownershipIntelligence) {
    return (
      <div
        style={{
          borderRadius: 'var(--radius-xl)',
          backgroundColor: 'var(--bg-secondary)',
          border: '1px solid var(--border-subtle)',
          padding: 'var(--space-6)',
          display: 'flex',
          flexDirection: 'column',
          gap: 'var(--space-3)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
          <Wrench size={20} style={{ color: 'var(--text-muted)' }} />
          <h3 style={{ margin: 0, fontSize: 'var(--font-size-xl)' }}>
            Ownership & Maintenance Profile
          </h3>
        </div>
        <div
          style={{
            padding: 'var(--space-4)',
            backgroundColor: 'var(--bg-primary)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--border-subtle)',
            fontSize: 'var(--font-size-sm)',
            color: 'var(--text-secondary)',
          }}
        >
          Detailed ownership lifecycle parameters not documented for this variant.
        </div>
      </div>
    );
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
        gap: 'var(--space-6)',
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          flexWrap: 'wrap',
          gap: 'var(--space-2)',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            <Wrench size={20} style={{ color: 'var(--color-primary)' }} />
            <h3 style={{ margin: 0, fontSize: 'var(--font-size-xl)' }}>
              Real-World Ownership & Lifecycle Economics
            </h3>
          </div>
          <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
            Empirical maintenance cadence, interactive fuel expenditure calculator, and 5-year Total Cost of Ownership
          </span>
        </div>

        <EvidenceBadge
          state={((ownership?.evidence_state as EvidenceState) || 'SUPPORTED')}
          size="sm"
        />
      </div>

      {/* Metrics Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))',
          gap: 'var(--space-4)',
        }}
      >
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
            Service Cadence
          </span>
          <div style={{ fontSize: 'var(--font-size-lg)', fontWeight: 'var(--font-weight-bold)', color: 'var(--text-primary)' }}>
            {ownership?.service_interval_km ? `${ownership.service_interval_km.toLocaleString('en-IN')} km` : '10,000 km'}
          </div>
          <span style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>
            or every {ownership?.service_interval_months || 12} months
          </span>
        </div>

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
            Typical Routine Maintenance
          </span>
          <div style={{ fontSize: 'var(--font-size-lg)', fontWeight: 'var(--font-weight-bold)', color: 'var(--color-primary)' }}>
            {ownership?.typical_annual_maintenance_inr || '₹5,500 – ₹8,500'}
          </div>
          <span style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>
            {ownership?.maintenance_complexity || 'Standard'} Complexity
          </span>
        </div>

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
            Real-World Mileage (City / Hwy)
          </span>
          <div style={{ fontSize: 'var(--font-size-lg)', fontWeight: 'var(--font-weight-bold)', color: 'var(--text-primary)' }}>
            {ownership?.real_world_city_mileage_kmpl || defaultCityMileage} / {ownership?.real_world_highway_mileage_kmpl || defaultHwyMileage} km/l
          </div>
          <span style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>
            Combined ~{defaultCombined} km/l
          </span>
        </div>

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
            Parts & Garage Accessibility
          </span>
          <div style={{ fontSize: 'var(--font-size-lg)', fontWeight: 'var(--font-weight-bold)', color: 'var(--text-primary)' }}>
            {ownership?.parts_availability || 'Wide Availability'}
          </div>
          <span style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>
            {ownershipIntelligence?.maintenance?.independent_garage_familiarity || 'High independent garage familiarity'}
          </span>
        </div>
      </div>

      {/* Interactive Fuel Cost Calculator */}
      <div
        style={{
          backgroundColor: 'var(--bg-primary)',
          borderRadius: 'var(--radius-lg)',
          border: '1px solid var(--border-subtle)',
          padding: 'var(--space-5)',
          display: 'flex',
          flexDirection: 'column',
          gap: 'var(--space-4)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
          <Fuel size={18} style={{ color: 'var(--color-primary)' }} />
          <h4 style={{ margin: 0, fontSize: 'var(--font-size-md)', fontWeight: 'var(--font-weight-semibold)' }}>
            Interactive Fuel Cost Calculator
          </h4>
        </div>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
            gap: 'var(--space-4)',
            alignItems: 'center',
          }}
        >
          {/* Slider 1: Monthly Usage */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--font-size-xs)' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Monthly Driving:</span>
              <strong>{monthlyKm.toLocaleString('en-IN')} km</strong>
            </div>
            <input
              type="range"
              min={200}
              max={3500}
              step={100}
              value={monthlyKm}
              onChange={(e) => setMonthlyKm(Number(e.target.value))}
              style={{ width: '100%', cursor: 'pointer' }}
            />
            <span style={{ fontSize: '10px', color: 'var(--text-tertiary)' }}>
              ~{Math.round(monthlyKm / 30)} km daily average commute
            </span>
          </div>

          {/* Slider 2: Fuel Economy */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--font-size-xs)' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Real Fuel Economy:</span>
              <strong>{mileageKmpl} km/l</strong>
            </div>
            <input
              type="range"
              min={8}
              max={28}
              step={0.5}
              value={mileageKmpl}
              onChange={(e) => setMileageKmpl(Number(e.target.value))}
              style={{ width: '100%', cursor: 'pointer' }}
            />
            <span style={{ fontSize: '10px', color: 'var(--text-tertiary)' }}>
              Benchmark: City {defaultCityMileage} | Highway {defaultHwyMileage} km/l
            </span>
          </div>

          {/* Calculator Output Card */}
          <div
            style={{
              padding: 'var(--space-3) var(--space-4)',
              backgroundColor: 'var(--bg-secondary)',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-medium)',
              display: 'flex',
              flexDirection: 'column',
              gap: 'var(--space-1)',
            }}
          >
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Estimated Fuel Running Cost</span>
            <div style={{ fontSize: 'var(--font-size-xl)', fontWeight: 'var(--font-weight-bold)', color: 'var(--color-primary)' }}>
              ₹{Math.round(monthlyFuelCost).toLocaleString('en-IN')} / mo
            </div>
            <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)' }}>
              ₹{fuelCostPerKm.toFixed(2)} / km • ₹{Math.round(annualFuelCost).toLocaleString('en-IN')} / year
            </div>
          </div>
        </div>
      </div>

      {/* Total Cost of Ownership (TCO) Simulator */}
      {currentTco && (
        <div
          style={{
            backgroundColor: 'var(--bg-primary)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--border-subtle)',
            padding: 'var(--space-5)',
            display: 'flex',
            flexDirection: 'column',
            gap: 'var(--space-4)',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                <Calculator size={18} style={{ color: 'var(--color-primary)' }} />
                <h4 style={{ margin: 0, fontSize: 'var(--font-size-md)', fontWeight: 'var(--font-weight-semibold)' }}>
                  Total Cost of Ownership (TCO) Projection
                </h4>
              </div>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                Multi-year economic projection combining depreciation, fuel, routine service, and insurance
              </span>
            </div>

            {/* Horizon Switcher Tabs */}
            <div style={{ display: 'flex', gap: 'var(--space-1)', backgroundColor: 'var(--bg-secondary)', padding: '2px', borderRadius: 'var(--radius-md)' }}>
              {([1, 3, 5] as const).map((yr) => (
                <button
                  key={yr}
                  onClick={() => setSelectedHorizon(yr)}
                  style={{
                    padding: '4px 12px',
                    borderRadius: 'var(--radius-sm)',
                    border: 'none',
                    backgroundColor: selectedHorizon === yr ? 'var(--color-primary)' : 'transparent',
                    color: selectedHorizon === yr ? '#FFFFFF' : 'var(--text-secondary)',
                    fontSize: 'var(--font-size-xs)',
                    fontWeight: selectedHorizon === yr ? 'var(--font-weight-semibold)' : 'var(--font-weight-normal)',
                    cursor: 'pointer',
                  }}
                >
                  {yr}-Year
                </button>
              ))}
            </div>
          </div>

          {/* TCO Highlights */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
              gap: 'var(--space-4)',
              padding: 'var(--space-4)',
              backgroundColor: 'var(--bg-secondary)',
              borderRadius: 'var(--radius-md)',
            }}
          >
            <div>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                {selectedHorizon}-Year Total Ownership Cost
              </span>
              <div style={{ fontSize: 'var(--font-size-xl)', fontWeight: 'var(--font-weight-bold)', color: 'var(--text-primary)' }}>
                ₹{currentTco.total_cost_inr.toLocaleString('en-IN')}
              </div>
            </div>

            <div>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                Effective Running Burden
              </span>
              <div style={{ fontSize: 'var(--font-size-xl)', fontWeight: 'var(--font-weight-bold)', color: 'var(--color-primary)' }}>
                ₹{currentTco.cost_per_km_inr.toFixed(2)} / km
              </div>
            </div>

            <div>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                Net Expected Depreciation
              </span>
              <div style={{ fontSize: 'var(--font-size-lg)', fontWeight: 'var(--font-weight-bold)', color: 'var(--color-warning)' }}>
                ₹{currentTco.depreciation_cost_inr.toLocaleString('en-IN')}
              </div>
            </div>
          </div>

          {/* TCO Component Breakdown */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
            <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 'var(--font-weight-semibold)', color: 'var(--text-secondary)' }}>
              Component Breakdown & Evidence Provenance
            </span>

            {currentTco.components.map((comp) => (
              <div
                key={comp.component_name}
                style={{
                  display: 'grid',
                  gridTemplateColumns: '150px 110px 1fr 140px',
                  alignItems: 'center',
                  gap: 'var(--space-3)',
                  padding: 'var(--space-2) 0',
                  borderBottom: '1px solid var(--border-subtle)',
                  fontSize: 'var(--font-size-xs)',
                }}
              >
                <span style={{ fontWeight: 'var(--font-weight-semibold)', color: 'var(--text-primary)' }}>
                  {comp.component_name}
                </span>

                <span style={{ color: 'var(--text-secondary)' }}>
                  ₹{comp.amount_inr.toLocaleString('en-IN')}
                </span>

                {/* Progress bar */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                  <div
                    style={{
                      flex: 1,
                      height: '6px',
                      backgroundColor: 'var(--bg-secondary)',
                      borderRadius: 'var(--radius-full)',
                      overflow: 'hidden',
                    }}
                  >
                    <div
                      style={{
                        width: `${Math.min(100, comp.percentage_of_total)}%`,
                        height: '100%',
                        backgroundColor: 'var(--color-primary)',
                      }}
                    />
                  </div>
                  <span style={{ minWidth: '35px', color: 'var(--text-muted)' }}>
                    {comp.percentage_of_total}%
                  </span>
                </div>

                <div style={{ textAlign: 'right' }}>
                  <Badge
                    variant={comp.status === 'EVIDENCE_BACKED' ? 'success' : 'info'}
                    size="sm"
                  >
                    {comp.status.replace('_', ' ')}
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Routine Service Schedule Milestones */}
      {routineSchedule.length > 0 && (
        <div
          style={{
            backgroundColor: 'var(--bg-primary)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--border-subtle)',
            padding: 'var(--space-5)',
            display: 'flex',
            flexDirection: 'column',
            gap: 'var(--space-3)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            <Wrench size={18} style={{ color: 'var(--color-primary)' }} />
            <h4 style={{ margin: 0, fontSize: 'var(--font-size-md)', fontWeight: 'var(--font-weight-semibold)' }}>
              Standard OEM Service Milestones
            </h4>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 'var(--space-3)' }}>
            {routineSchedule.map((item) => (
              <div
                key={item.milestone_name}
                style={{
                  padding: 'var(--space-3)',
                  backgroundColor: 'var(--bg-secondary)',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border-subtle)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '4px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontWeight: 'var(--font-weight-bold)', fontSize: 'var(--font-size-xs)' }}>
                    {item.milestone_name}
                  </span>
                  <span style={{ color: 'var(--color-primary)', fontWeight: 'var(--font-weight-semibold)', fontSize: 'var(--font-size-xs)' }}>
                    ₹{item.estimated_cost_inr.toLocaleString('en-IN')}
                  </span>
                </div>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                  At {item.interval_km.toLocaleString('en-IN')} km ({item.interval_months} mo)
                </span>
                <span style={{ fontSize: '10px', color: 'var(--text-tertiary)' }}>
                  Tasks: {item.typical_tasks.slice(0, 3).join(', ')}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Ownership Risk Signals */}
      {riskSignals.length > 0 && (
        <div
          style={{
            backgroundColor: 'rgba(229, 62, 62, 0.04)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid rgba(229, 62, 62, 0.2)',
            padding: 'var(--space-5)',
            display: 'flex',
            flexDirection: 'column',
            gap: 'var(--space-3)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', color: 'var(--color-danger)' }}>
            <ShieldAlert size={18} />
            <h4 style={{ margin: 0, fontSize: 'var(--font-size-md)', fontWeight: 'var(--font-weight-semibold)' }}>
              Critical Ownership Risk Signals & Component Longevity
            </h4>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
            {riskSignals.map((risk) => (
              <div
                key={risk.risk_id}
                style={{
                  padding: 'var(--space-3) var(--space-4)',
                  backgroundColor: 'var(--bg-primary)',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border-subtle)',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  flexWrap: 'wrap',
                  gap: 'var(--space-2)',
                }}
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                    <Badge variant={risk.severity === 'CRITICAL' ? 'danger' : 'warning'} size="sm">
                      {risk.severity}
                    </Badge>
                    <span style={{ fontWeight: 'var(--font-weight-semibold)', fontSize: 'var(--font-size-xs)' }}>
                      {risk.title}
                    </span>
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
                    Component: <strong>{risk.component_affected}</strong>
                    {risk.typical_occurrence_km ? ` • Typical occurrence: ~${risk.typical_occurrence_km.toLocaleString('en-IN')} km` : ''}
                    {' • '}Preventative action: {risk.preventative_measure}
                  </div>
                </div>

                <div style={{ textAlign: 'right' }}>
                  <span style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>Est. Repair Cost</span>
                  <div style={{ fontWeight: 'var(--font-weight-bold)', fontSize: 'var(--font-size-xs)', color: 'var(--color-danger)' }}>
                    ₹{risk.estimated_repair_cost_inr.toLocaleString('en-IN')}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Strengths & Concerns */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 'var(--space-4)' }}>
        {ownership?.ownership_strengths && ownership.ownership_strengths.length > 0 && (
          <div
            style={{
              padding: 'var(--space-4)',
              backgroundColor: 'rgba(56, 161, 105, 0.04)',
              borderRadius: 'var(--radius-lg)',
              border: '1px solid rgba(56, 161, 105, 0.2)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', color: 'var(--color-success)', fontWeight: 'var(--font-weight-bold)', fontSize: 'var(--font-size-xs)', marginBottom: 'var(--space-2)' }}>
              <ThumbsUp size={14} />
              <span>Documented Ownership Strengths</span>
            </div>
            <ul style={{ margin: 0, paddingLeft: 'var(--space-4)', fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: 'var(--space-1)' }}>
              {ownership.ownership_strengths.map((str, idx) => (
                <li key={idx}>{str}</li>
              ))}
            </ul>
          </div>
        )}

        {ownership?.ownership_concerns && ownership.ownership_concerns.length > 0 && (
          <div
            style={{
              padding: 'var(--space-4)',
              backgroundColor: 'rgba(214, 158, 46, 0.04)',
              borderRadius: 'var(--radius-lg)',
              border: '1px solid rgba(214, 158, 46, 0.25)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', color: 'var(--color-warning)', fontWeight: 'var(--font-weight-bold)', fontSize: 'var(--font-size-xs)', marginBottom: 'var(--space-2)' }}>
              <ThumbsDown size={14} />
              <span>Documented Ownership Watchpoints</span>
            </div>
            <ul style={{ margin: 0, paddingLeft: 'var(--space-4)', fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: 'var(--space-1)' }}>
              {ownership.ownership_concerns.map((con, idx) => (
                <li key={idx}>{con}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Provenance Disclaimer */}
      <div
        style={{
          padding: 'var(--space-3) var(--space-4)',
          backgroundColor: 'rgba(49, 130, 206, 0.05)',
          borderRadius: 'var(--radius-lg)',
          border: '1px solid rgba(49, 130, 206, 0.15)',
          display: 'flex',
          alignItems: 'flex-start',
          gap: 'var(--space-3)',
          fontSize: 'var(--font-size-xs)',
          color: 'var(--text-secondary)',
        }}
      >
        <Info size={16} style={{ color: 'var(--accent-blue)', flexShrink: 0, marginTop: '2px' }} />
        <div>
          <strong>Ownership Model Transparency:</strong> TCO projections combine OEM published maintenance schedules, empirical wear rates for Indian road conditions, secondary market asking-price depreciation trajectories, and statutory insurance rates. Individual vehicle operating costs will fluctuate according to driver behavior, terrain, and fuel prices.
        </div>
      </div>
    </div>
  );
};
