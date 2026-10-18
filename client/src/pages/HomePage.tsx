import React from 'react';
import { SearchBox } from '../components/common/SearchBox';
import { Button } from '../components/common/Button';
import { useApp } from '../state/AppContext';
import {
  TrendingUp,
  Scale,
  ClipboardCheck,
  ShieldCheck,
  Sparkles,
  BarChart3,
  Search as SearchIcon,
  CheckCircle2,
} from 'lucide-react';

export interface HomePageProps {
  onNavigate: (path: string) => void;
}

export const HomePage: React.FC<HomePageProps> = ({ onNavigate }) => {
  const { setCurrentVehicle } = useApp();

  const handleVehicleSelect = (item: { brand: string; model: string; year?: number; canonical_id?: string }) => {
    const canonicalId =
      item.canonical_id ||
      `${item.brand.toLowerCase().replace(/\s+/g, '-')}::${item.model.toLowerCase().replace(/\s+/g, '-')}`;
    setCurrentVehicle({
      brand: item.brand,
      model: item.model,
      year: item.year || 2021,
      canonical_id: canonicalId,
      fuel_type: 'Petrol',
      transmission_type: 'Manual',
      asking_price: 850000,
      km_driven: 35000,
    });
    onNavigate(`/vehicle/${encodeURIComponent(canonicalId)}`);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', width: '100%' }}>
      {/* Search-First Hero Section */}
      <section
        style={{
          padding: 'var(--space-16) 0 var(--space-12)',
          backgroundColor: 'var(--bg-primary)',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          textAlign: 'center',
        }}
      >
        <div className="container" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
          {/* Eyebrow Badge */}
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 'var(--space-2)',
              backgroundColor: 'var(--accent-blue-light)',
              color: 'var(--accent-blue)',
              borderRadius: 'var(--radius-full)',
              padding: 'var(--space-1) var(--space-4)',
              fontSize: 'var(--font-size-xs)',
              fontWeight: 'var(--font-weight-semibold)',
              marginBottom: 'var(--space-4)',
            }}
          >
            <Sparkles size={14} />
            <span>Intelligent Automotive Intelligence for India</span>
          </div>

          {/* Hero Headline */}
          <h1
            style={{
              fontSize: 'clamp(2rem, 5vw, 3.5rem)',
              fontWeight: 'var(--font-weight-extrabold)',
              letterSpacing: '-0.03em',
              lineHeight: 1.15,
              maxWidth: '820px',
              margin: '0 0 var(--space-4)',
              color: 'var(--text-primary)',
            }}
          >
            What car are you looking for?
          </h1>

          {/* Subtitle / Product North Star */}
          <p
            style={{
              fontSize: 'var(--font-size-lg)',
              color: 'var(--text-muted)',
              maxWidth: '640px',
              margin: '0 0 var(--space-8)',
              lineHeight: 1.6,
            }}
          >
            Know the car. Know the value. Know the truth. Grounded market valuations, transparent deal analysis, and
            evidence-based inspection checklists.
          </p>

          {/* Centralized Search Box */}
          <div style={{ width: '100%', display: 'flex', justifyContent: 'center', marginBottom: 'var(--space-8)' }}>
            <SearchBox onSelectVehicle={handleVehicleSelect} size="lg" autoFocus />
          </div>

          {/* Secondary Quick-Action Shortcuts */}
          <div
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              justifyContent: 'center',
              gap: 'var(--space-3)',
            }}
          >
            <Button
              variant="outline"
              size="md"
              leftIcon={<BarChart3 size={16} color="var(--accent-blue)" />}
              onClick={() => onNavigate('/value')}
            >
              Value My Car
            </Button>

            <Button
              variant="outline"
              size="md"
              leftIcon={<TrendingUp size={16} color="var(--status-pass)" />}
              onClick={() => onNavigate('/deal')}
            >
              Analyze a Deal
            </Button>

            <Button
              variant="outline"
              size="md"
              leftIcon={<Scale size={16} color="var(--accent-intelligence)" />}
              onClick={() => onNavigate('/compare')}
            >
              Compare 2–3 Cars
            </Button>

            <Button
              variant="outline"
              size="md"
              leftIcon={<ClipboardCheck size={16} color="var(--status-attention)" />}
              onClick={() => onNavigate('/inspect')}
            >
              Inspection Checklist
            </Button>
          </div>
        </div>
      </section>

      {/* Product Pillars: Understanding > Decoration */}
      <section style={{ padding: 'var(--space-12) 0', backgroundColor: 'var(--bg-secondary)' }}>
        <div className="container" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-8)' }}>
          <div style={{ textAlign: 'center', maxWidth: '640px', margin: '0 auto' }}>
            <h2 style={{ fontSize: 'var(--font-size-3xl)', marginBottom: 'var(--space-2)' }}>
              Built for Used-Car Buyers Who Value Evidence
            </h2>
            <p style={{ fontSize: 'var(--font-size-base)', color: 'var(--text-muted)' }}>
              Traditional portals are built for sellers and advertisers. CarSpective is engineered exclusively for buyer
              clarity.
            </p>
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
              gap: 'var(--space-6)',
            }}
          >
            {/* Pillar 1 */}
            <div
              style={{
                backgroundColor: 'var(--bg-primary)',
                padding: 'var(--space-6)',
                borderRadius: 'var(--radius-xl)',
                border: '1px solid var(--border-subtle)',
                boxShadow: 'var(--shadow-sm)',
                display: 'flex',
                flexDirection: 'column',
                gap: 'var(--space-3)',
              }}
            >
              <div
                style={{
                  width: '42px',
                  height: '42px',
                  borderRadius: 'var(--radius-lg)',
                  backgroundColor: 'var(--accent-blue-light)',
                  color: 'var(--accent-blue)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <BarChart3 size={22} />
              </div>
              <h3 style={{ fontSize: 'var(--font-size-xl)', margin: 0 }}>Empirical Valuation</h3>
              <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.6 }}>
                Estimated fair market asking price with conformal uncertainty intervals calibrated across 57,480
                historical Indian used car records.
              </p>
            </div>

            {/* Pillar 2 */}
            <div
              style={{
                backgroundColor: 'var(--bg-primary)',
                padding: 'var(--space-6)',
                borderRadius: 'var(--radius-xl)',
                border: '1px solid var(--border-subtle)',
                boxShadow: 'var(--shadow-sm)',
                display: 'flex',
                flexDirection: 'column',
                gap: 'var(--space-3)',
              }}
            >
              <div
                style={{
                  width: '42px',
                  height: '42px',
                  borderRadius: 'var(--radius-lg)',
                  backgroundColor: 'var(--status-pass-bg)',
                  color: 'var(--status-pass)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <TrendingUp size={22} />
              </div>
              <h3 style={{ fontSize: 'var(--font-size-xl)', margin: 0 }}>Deal vs Vehicle Independence</h3>
              <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.6 }}>
                We strictly separate <em>how good the car is</em> from <em>how good the deal is</em>. A great car can be
                overpriced; a cheap deal can be risky.
              </p>
            </div>

            {/* Pillar 3 */}
            <div
              style={{
                backgroundColor: 'var(--bg-primary)',
                padding: 'var(--space-6)',
                borderRadius: 'var(--radius-xl)',
                border: '1px solid var(--border-subtle)',
                boxShadow: 'var(--shadow-sm)',
                display: 'flex',
                flexDirection: 'column',
                gap: 'var(--space-3)',
              }}
            >
              <div
                style={{
                  width: '42px',
                  height: '42px',
                  borderRadius: 'var(--radius-lg)',
                  backgroundColor: 'var(--accent-cyan-light)',
                  color: 'var(--accent-intelligence)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <ClipboardCheck size={22} />
              </div>
              <h3 style={{ fontSize: 'var(--font-size-xl)', margin: 0 }}>Adaptive Inspection</h3>
              <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.6 }}>
                45-point checklist tailored specifically to the vehicle's engine, fuel type, transmission, and age.
                Never assumes unknown items are safe.
              </p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};
