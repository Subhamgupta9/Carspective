import React, { useState } from 'react';
import { useApp } from '../state/AppContext';
import { valuationApi } from '../api/valuationApi';
import { ValuationResponse } from '../types';
import { ValuationCard } from '../features/valuation/ValuationCard';
import { Button } from '../components/common/Button';
import { Input } from '../components/common/Input';
import { FeedbackWidget } from '../features/feedback/FeedbackWidget';
import { BarChart3 } from 'lucide-react';

export const ValuationPage: React.FC = () => {
  const { currentVehicle } = useApp();

  const [brand, setBrand] = useState(currentVehicle?.brand || 'Honda');
  const [model, setModel] = useState(currentVehicle?.model || 'City');
  const [year, setYear] = useState(String(currentVehicle?.year || 2021));
  const [kmDriven, setKmDriven] = useState(String(currentVehicle?.km_driven || 35000));
  const [fuelType, setFuelType] = useState(currentVehicle?.fuel_type || 'Petrol');

  const [valuation, setValuation] = useState<ValuationResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleCalculate = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      const res = await valuationApi.getValuation({
        brand: brand.trim(),
        model: model.trim(),
        manufacturing_year: parseInt(year, 10) || 2021,
        km_driven: parseFloat(kmDriven) || 35000,
        fuel_type: fuelType,
        transmission_type: 'Manual',
      });
      setValuation(res);
    } catch {
      // Error handled
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="container" style={{ padding: 'var(--space-8) 0', display: 'flex', flexDirection: 'column', gap: 'var(--space-8)' }}>
      <div>
        <h1 style={{ fontSize: 'var(--font-size-3xl)', marginBottom: 'var(--space-2)' }}>
          Vehicle Fair Market Valuation
        </h1>
        <p style={{ fontSize: 'var(--font-size-base)', color: 'var(--text-muted)' }}>
          Empirically calibrated asking-price valuation engine trained on 57,480 historical Indian listing records.
        </p>
      </div>

      {/* Input Parameters Form Card */}
      <div
        style={{
          backgroundColor: 'var(--bg-primary)',
          borderRadius: 'var(--radius-xl)',
          border: '1px solid var(--border-subtle)',
          padding: 'var(--space-6)',
          boxShadow: 'var(--shadow-sm)',
        }}
      >
        <form onSubmit={handleCalculate} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 'var(--space-4)' }}>
            <Input
              label="Manufacturer / Brand"
              value={brand}
              onChange={e => setBrand(e.target.value)}
              placeholder="e.g. Honda, Maruti, Tata"
              required
            />
            <Input
              label="Model Name"
              value={model}
              onChange={e => setModel(e.target.value)}
              placeholder="e.g. City, Swift, Nexon"
              required
            />
            <Input
              label="Manufacturing Year"
              type="number"
              min="1990"
              max="2026"
              value={year}
              onChange={e => setYear(e.target.value)}
              required
            />
            <Input
              label="Odometer (km driven)"
              type="number"
              value={kmDriven}
              onChange={e => setKmDriven(e.target.value)}
              required
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 'var(--space-2)' }}>
            <Button
              type="submit"
              variant="primary"
              size="lg"
              isLoading={isLoading}
              leftIcon={<BarChart3 size={18} />}
            >
              Compute Valuation
            </Button>
          </div>
        </form>
      </div>

      {/* Valuation Output */}
      {valuation && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
          <ValuationCard valuation={valuation} isLoading={isLoading} />
          <FeedbackWidget feature="valuation" />
        </div>
      )}
    </div>
  );
};
