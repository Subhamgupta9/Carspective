import React, { useState, useEffect } from 'react';
import { useApp } from '../state/AppContext';
import { comparisonApi } from '../api/comparisonApi';
import { ComparisonResponse } from '../types';
import { ComparisonMatrix } from '../features/comparison/ComparisonMatrix';
import { Button } from '../components/common/Button';
import { Input } from '../components/common/Input';
import { EmptyState } from '../components/common/EmptyState';
import { Scale, Plus, Trash2 } from 'lucide-react';

export const ComparisonPage: React.FC = () => {
  const { comparisonVehicles, addComparisonVehicle, removeComparisonVehicle, clearComparison } = useApp();

  const [comparison, setComparison] = useState<ComparisonResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // New vehicle add inputs
  const [newBrand, setNewBrand] = useState('');
  const [newModel, setNewModel] = useState('');
  const [newYear, setNewYear] = useState('2021');

  useEffect(() => {
    if (comparisonVehicles.length >= 2) {
      runComparison();
    } else {
      setComparison(null);
    }
  }, [comparisonVehicles.length]);

  const runComparison = async () => {
    if (comparisonVehicles.length < 2) return;
    setIsLoading(true);
    try {
      const res = await comparisonApi.compareVehicles({
        vehicles: comparisonVehicles.map(v => ({
          brand: v.brand,
          model: v.model,
          manufacturing_year: v.year || 2021,
          fuel_type: v.fuel_type || 'Petrol',
          transmission_type: v.transmission_type || 'Manual',
        })),
        mode: 'general',
      });
      setComparison(res);
    } catch {
      // Error handled
    } finally {
      setIsLoading(false);
    }
  };

  const handleAddVehicle = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newBrand.trim() || !newModel.trim()) return;
    const added = addComparisonVehicle({
      brand: newBrand.trim(),
      model: newModel.trim(),
      year: parseInt(newYear, 10) || 2021,
      fuel_type: 'Petrol',
      transmission_type: 'Manual',
    });
    if (added) {
      setNewBrand('');
      setNewModel('');
    }
  };

  return (
    <div className="container" style={{ padding: 'var(--space-8) 0', display: 'flex', flexDirection: 'column', gap: 'var(--space-8)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 'var(--space-4)' }}>
        <div>
          <h1 style={{ fontSize: 'var(--font-size-3xl)', marginBottom: 'var(--space-2)' }}>Intelligent Vehicle Comparison</h1>
          <p style={{ fontSize: 'var(--font-size-base)', color: 'var(--text-muted)' }}>
            Compare 2 to 3 canonical vehicles across safety, reliability, maintenance, and trade-off metrics.
          </p>
        </div>

        {comparisonVehicles.length > 0 && (
          <Button variant="ghost" size="sm" onClick={clearComparison}>
            Clear Selection
          </Button>
        )}
      </div>

      {/* Selected Vehicles Tray */}
      <div
        style={{
          backgroundColor: 'var(--bg-primary)',
          borderRadius: 'var(--radius-xl)',
          padding: 'var(--space-5)',
          border: '1px solid var(--border-subtle)',
          boxShadow: 'var(--shadow-sm)',
          display: 'flex',
          flexDirection: 'column',
          gap: 'var(--space-4)',
        }}
      >
        <div style={{ fontSize: 'var(--font-size-xs)', fontWeight: 'var(--font-weight-semibold)', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
          Vehicles in Comparison ({comparisonVehicles.length} of 3)
        </div>

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-3)' }}>
          {comparisonVehicles.map((v, idx) => (
            <div
              key={idx}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--space-2)',
                backgroundColor: 'var(--bg-secondary)',
                borderRadius: 'var(--radius-lg)',
                padding: 'var(--space-2) var(--space-4)',
                border: '1px solid var(--border-light)',
              }}
            >
              <Scale size={16} color="var(--accent-blue)" />
              <span style={{ fontWeight: 'var(--font-weight-bold)', fontSize: 'var(--font-size-sm)' }}>
                {v.brand} {v.model} {v.year ? `(${v.year})` : ''}
              </span>
              <button
                onClick={() => removeComparisonVehicle(idx)}
                aria-label={`Remove ${v.brand} ${v.model} from comparison`}
                style={{
                  color: 'var(--text-muted)',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  padding: 'var(--space-1)',
                }}
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))}

          {/* Quick Add Form if < 3 vehicles */}
          {comparisonVehicles.length < 3 && (
            <form onSubmit={handleAddVehicle} style={{ display: 'flex', gap: 'var(--space-2)', alignItems: 'center' }}>
              <input
                placeholder="Brand (e.g. Maruti)"
                value={newBrand}
                onChange={e => setNewBrand(e.target.value)}
                style={{
                  padding: 'var(--space-2) var(--space-3)',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border-medium)',
                  fontSize: 'var(--font-size-xs)',
                  width: '130px',
                }}
              />
              <input
                placeholder="Model (e.g. Baleno)"
                value={newModel}
                onChange={e => setNewModel(e.target.value)}
                style={{
                  padding: 'var(--space-2) var(--space-3)',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border-medium)',
                  fontSize: 'var(--font-size-xs)',
                  width: '130px',
                }}
              />
              <Button type="submit" variant="secondary" size="sm" leftIcon={<Plus size={14} />}>
                Add
              </Button>
            </form>
          )}
        </div>
      </div>

      {/* Comparison Body */}
      {comparisonVehicles.length < 2 ? (
        <EmptyState
          title="Add At Least 2 Vehicles to Compare"
          description="CarSpective needs at least 2 vehicles (and up to 3) to analyze meaningful category differences and trade-offs."
          icon={<Scale size={42} color="var(--accent-blue)" />}
        />
      ) : (
        <ComparisonMatrix comparison={comparison} isLoading={isLoading} />
      )}
    </div>
  );
};
