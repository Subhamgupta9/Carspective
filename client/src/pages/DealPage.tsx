import React, { useState } from 'react';
import { useApp } from '../state/AppContext';
import { dealApi } from '../api/dealApi';
import { DealAnalysisResponse } from '../types';
import { DealAnalyzerCard } from '../features/deal/DealAnalyzerCard';
import { Button } from '../components/common/Button';
import { Input } from '../components/common/Input';
import { FeedbackWidget } from '../features/feedback/FeedbackWidget';
import { TrendingUp } from 'lucide-react';

export const DealPage: React.FC = () => {
  const { currentVehicle } = useApp();

  const [brand, setBrand] = useState(currentVehicle?.brand || 'Honda');
  const [model, setModel] = useState(currentVehicle?.model || 'City');
  const [year, setYear] = useState(String(currentVehicle?.year || 2021));
  const [kmDriven, setKmDriven] = useState(String(currentVehicle?.km_driven || 35000));
  const [askingPrice, setAskingPrice] = useState(
    currentVehicle?.asking_price ? String(currentVehicle.asking_price) : '850000'
  );

  const [dealAnalysis, setDealAnalysis] = useState<DealAnalysisResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleAnalyze = async (priceOverride?: number) => {
    const finalPrice = priceOverride || parseFloat(askingPrice);
    if (isNaN(finalPrice) || finalPrice <= 0) return;

    setIsLoading(true);
    try {
      const res = await dealApi.analyzeDeal({
        brand: brand.trim(),
        model: model.trim(),
        manufacturing_year: parseInt(year, 10) || 2021,
        km_driven: parseFloat(kmDriven) || 35000,
        asking_price: finalPrice,
        fuel_type: 'Petrol',
        transmission_type: 'Manual',
      });
      setDealAnalysis(res);
    } catch {
      // Error handled
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="container" style={{ padding: 'var(--space-8) 0', display: 'flex', flexDirection: 'column', gap: 'var(--space-8)' }}>
      <div>
        <h1 style={{ fontSize: 'var(--font-size-3xl)', marginBottom: 'var(--space-2)' }}>Deal Analyzer</h1>
        <p style={{ fontSize: 'var(--font-size-base)', color: 'var(--text-muted)' }}>
          Compare seller asking price with CarSpective's fair-market valuation range to evaluate commercial risk and
          negotiation leverage.
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
        <form
          onSubmit={e => {
            e.preventDefault();
            handleAnalyze();
          }}
          style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}
        >
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 'var(--space-4)' }}>
            <Input
              label="Manufacturer / Brand"
              value={brand}
              onChange={e => setBrand(e.target.value)}
              placeholder="e.g. Honda, Hyundai, Tata"
              required
            />
            <Input
              label="Model Name"
              value={model}
              onChange={e => setModel(e.target.value)}
              placeholder="e.g. City, Creta, Nexon"
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
              label="Odometer (km)"
              type="number"
              value={kmDriven}
              onChange={e => setKmDriven(e.target.value)}
              required
            />
            <Input
              label="Seller Asking Price (INR)"
              type="number"
              value={askingPrice}
              onChange={e => setAskingPrice(e.target.value)}
              placeholder="e.g. 850000"
              required
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 'var(--space-2)' }}>
            <Button
              type="submit"
              variant="primary"
              size="lg"
              isLoading={isLoading}
              leftIcon={<TrendingUp size={18} />}
            >
              Analyze Deal Quality
            </Button>
          </div>
        </form>
      </div>

      {/* Deal Output Card */}
      <DealAnalyzerCard
        dealAnalysis={dealAnalysis}
        onAnalyze={price => handleAnalyze(price)}
        isLoading={isLoading}
      />

      {dealAnalysis && <FeedbackWidget feature="deal" />}
    </div>
  );
};
