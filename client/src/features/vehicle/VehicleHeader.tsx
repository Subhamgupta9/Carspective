import React from 'react';
import { VehicleSelection } from '../../state/AppContext';
import { EvidenceBadge } from '../../components/common/EvidenceBadge';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import { Scale, Bot, CheckSquare, Sparkles } from 'lucide-react';
import { useApp } from '../../state/AppContext';

export interface VehicleHeaderProps {
  vehicle: VehicleSelection;
  onNavigateTab?: (tab: string) => void;
}

export const VehicleHeader: React.FC<VehicleHeaderProps> = ({
  vehicle,
  onNavigateTab,
}) => {
  const { addComparisonVehicle, openAssistant } = useApp();

  return (
    <div
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 'var(--space-4)',
        padding: 'var(--space-6) 0',
        borderBottom: '1px solid var(--border-subtle)',
      }}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
          <Badge variant="neutral" size="sm">
            {vehicle.brand}
          </Badge>
          <EvidenceBadge state="VERIFIED" size="sm" />
        </div>

        <h1 style={{ margin: 0, fontSize: 'var(--font-size-4xl)', letterSpacing: '-0.02em' }}>
          {vehicle.brand} {vehicle.model} {vehicle.year ? vehicle.year : ''}
        </h1>

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-2)', fontSize: 'var(--font-size-sm)', color: 'var(--text-muted)' }}>
          {vehicle.variant && <span>Variant: {vehicle.variant}</span>}
          <span>• Powertrain: {vehicle.fuel_type || 'Petrol'} {vehicle.transmission_type || 'Manual'}</span>
          {vehicle.km_driven && <span>• Odometer: {vehicle.km_driven.toLocaleString('en-IN')} km</span>}
        </div>
      </div>

      {/* Action Buttons */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
        <Button
          variant="outline"
          size="md"
          leftIcon={<Scale size={16} />}
          onClick={() => addComparisonVehicle(vehicle)}
        >
          Compare
        </Button>

        <Button
          variant="outline"
          size="md"
          leftIcon={<CheckSquare size={16} />}
          onClick={() => onNavigateTab && onNavigateTab('inspection')}
        >
          Inspect Checklist
        </Button>

        <Button
          variant="primary"
          size="md"
          leftIcon={<Bot size={16} />}
          onClick={openAssistant}
        >
          Ask CarSpective
        </Button>
      </div>
    </div>
  );
};
