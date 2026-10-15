import React, { useState, useEffect } from 'react';
import { useApp } from '../state/AppContext';
import { inspectionApi } from '../api/inspectionApi';
import { InspectionEvaluationResponse, InspectionStatus } from '../types';
import { InspectionChecklist } from '../features/inspection/InspectionChecklist';
import { Button } from '../components/common/Button';
import { Input } from '../components/common/Input';
import { FeedbackWidget } from '../features/feedback/FeedbackWidget';
import { ClipboardCheck } from 'lucide-react';

export const InspectionPage: React.FC = () => {
  const { currentVehicle } = useApp();

  const [brand, setBrand] = useState(currentVehicle?.brand || 'Honda');
  const [model, setModel] = useState(currentVehicle?.model || 'City');
  const [year, setYear] = useState(String(currentVehicle?.year || 2021));
  const [odometerKm, setOdometerKm] = useState(String(currentVehicle?.km_driven || 35000));
  const [fuelType, setFuelType] = useState(currentVehicle?.fuel_type || 'Petrol');
  const [transmission, setTransmission] = useState(currentVehicle?.transmission_type || 'Manual');

  const [inspection, setInspection] = useState<InspectionEvaluationResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    loadInspection();
  }, []);

  const loadInspection = async () => {
    setIsLoading(true);
    try {
      const res = await inspectionApi.getInspection({
        brand: brand.trim(),
        model: model.trim(),
        manufacturing_year: parseInt(year, 10) || 2021,
        odometer_km: parseFloat(odometerKm) || 35000,
        fuel_type: fuelType,
        transmission_type: transmission,
      });
      setInspection(res);
    } catch {
      // Error handled
    } finally {
      setIsLoading(false);
    }
  };

  const handleStatusChange = (itemId: string, newStatus: InspectionStatus) => {
    if (!inspection) return;
    const updatedCategories = inspection.categories.map(cat => ({
      ...cat,
      items: cat.items.map(item => (item.item_id === itemId ? { ...item, status: newStatus } : item)),
    }));
    setInspection({
      ...inspection,
      categories: updatedCategories,
    });
  };

  return (
    <div className="container" style={{ padding: 'var(--space-8) 0', display: 'flex', flexDirection: 'column', gap: 'var(--space-8)' }}>
      <div>
        <h1 style={{ fontSize: 'var(--font-size-3xl)', marginBottom: 'var(--space-2)' }}>Inspection Intelligence</h1>
        <p style={{ fontSize: 'var(--font-size-base)', color: 'var(--text-muted)' }}>
          45-point adaptive inspection checklist tailored to vehicle powertrain, fuel type, and age.
        </p>
      </div>

      {/* Target Vehicle Configuration */}
      <div
        style={{
          backgroundColor: 'var(--bg-primary)',
          borderRadius: 'var(--radius-xl)',
          padding: 'var(--space-5)',
          border: '1px solid var(--border-subtle)',
          boxShadow: 'var(--shadow-sm)',
        }}
      >
        <form
          onSubmit={e => {
            e.preventDefault();
            loadInspection();
          }}
          style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 'var(--space-3)', alignItems: 'flex-end' }}
        >
          <Input label="Brand" value={brand} onChange={e => setBrand(e.target.value)} required />
          <Input label="Model" value={model} onChange={e => setModel(e.target.value)} required />
          <Input label="Year" type="number" value={year} onChange={e => setYear(e.target.value)} required />
          <Input label="Odometer (km)" type="number" value={odometerKm} onChange={e => setOdometerKm(e.target.value)} required />

          <Button type="submit" variant="primary" size="md" isLoading={isLoading} leftIcon={<ClipboardCheck size={16} />}>
            Generate Checklist
          </Button>
        </form>
      </div>

      {/* Inspection Checklist Component */}
      <InspectionChecklist
        inspection={inspection}
        onItemStatusChange={handleStatusChange}
        isLoading={isLoading}
      />

      <FeedbackWidget feature="inspection" />
    </div>
  );
};
