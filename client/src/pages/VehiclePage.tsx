import React, { useState, useEffect, useCallback } from 'react';
import { useApp } from '../state/AppContext';
import { vehicleApi } from '../api/vehicleApi';
import { dealApi } from '../api/dealApi';
import {
  VehicleWorkspaceResponse,
  DealAnalysisResponse,
} from '../types';

// Workspace Components
import { DecisionSummaryCard } from '../features/vehicle/workspace/DecisionSummaryCard';
import { ExecutiveSummaryCard } from '../features/vehicle/workspace/ExecutiveSummaryCard';
import { IdentityConfidenceCard } from '../features/vehicle/workspace/IdentityConfidenceCard';
import { MarketValueCard } from '../features/vehicle/workspace/MarketValueCard';
import { DealAnalyzerSection } from '../features/vehicle/workspace/DealAnalyzerSection';
import { VehicleScoreSection } from '../features/vehicle/workspace/VehicleScoreSection';
import { KeySpecsSection } from '../features/vehicle/workspace/KeySpecsSection';
import { SafetySection } from '../features/vehicle/workspace/SafetySection';
import { OwnershipSection } from '../features/vehicle/workspace/OwnershipSection';
import { ReliabilitySection } from '../features/vehicle/workspace/ReliabilitySection';
import { FeaturesSection } from '../features/vehicle/workspace/FeaturesSection';
import { ReviewSynthesisSection } from '../features/vehicle/workspace/ReviewSynthesisSection';
import { ProsConsSection } from '../features/vehicle/workspace/ProsConsSection';
import { MarketPositionSection } from '../features/vehicle/workspace/MarketPositionSection';
import { LiveMarketEvidenceSection } from '../features/vehicle/workspace/LiveMarketEvidenceSection';
import { AlternativesSection } from '../features/vehicle/workspace/AlternativesSection';
import { InspectionCalloutSection } from '../features/vehicle/workspace/InspectionCalloutSection';
import { AssistantDrawerIntegration } from '../features/vehicle/workspace/AssistantDrawerIntegration';
import { Vehicle3DViewer } from '../features/vehicle/Vehicle3DViewer';
import { FeedbackWidget } from '../features/feedback/FeedbackWidget';

// Common Components
import { Badge } from '../components/common/Badge';
import { EvidenceBadge } from '../components/common/EvidenceBadge';
import { Button } from '../components/common/Button';
import {
  PersonalizedDecisionCard,
  RequirementsEditor,
  PersonalizedShortlistDrawer,
} from '../features/decision';
import { decisionApi } from '../api/decisionApi';
import {
  UserRequirementsProfile,
  DecisionEvaluationResponse,
} from '../types';
import {
  Scale,
  Bot,
  ClipboardCheck,
  Compass,
  ArrowLeft,
  RefreshCw,
  Search,
  Sliders,
  ListPlus,
  TrendingUp,
  Tag,
  ShieldCheck,
} from 'lucide-react';

export interface VehiclePageProps {
  vehicleId?: string;
  onNavigate: (path: string) => void;
}

export const VehiclePage: React.FC<VehiclePageProps> = ({ vehicleId, onNavigate }) => {
  const { currentVehicle, setCurrentVehicle, addComparisonVehicle, openAssistant } = useApp();

  const [activeCanonicalId, setActiveCanonicalId] = useState<string>(() => {
    if (vehicleId) return decodeURIComponent(vehicleId);
    if (currentVehicle?.canonical_id) return currentVehicle.canonical_id;
    // Default fallback to Maruti Swift Tier 1 deep vehicle
    return 'maruti-suzuki::swift::gen-3-2018::2021::zxi::1-2-k12m-5mt';
  });

  const [askingPrice, setAskingPrice] = useState<number | undefined>(
    currentVehicle?.asking_price || undefined
  );
  const [kmDriven, setKmDriven] = useState<number | undefined>(
    currentVehicle?.km_driven || undefined
  );

  const [workspace, setWorkspace] = useState<VehicleWorkspaceResponse | null>(null);
  const [dealAnalysis, setDealAnalysis] = useState<DealAnalysisResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isEvaluatingDeal, setIsEvaluatingDeal] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<string>('all');

  // Phase 15 Personalized Decision State
  const [userProfile, setUserProfile] = useState<UserRequirementsProfile>({
    hard_constraints: {
      strict_budget_ceiling: false,
      strict_transmission: false,
      strict_fuel_type: false,
      strict_min_seating: false,
      strict_body_type: false,
    },
  });
  const [personalizedDecision, setPersonalizedDecision] = useState<DecisionEvaluationResponse | null>(null);
  const [isEditingProfile, setIsEditingProfile] = useState<boolean>(false);
  const [isShortlistOpen, setIsShortlistOpen] = useState<boolean>(false);
  const [shortlist, setShortlist] = useState<string[]>([]);

  const fetchDecision = useCallback(async (canId: string, prof: UserRequirementsProfile, price?: number, km?: number) => {
    try {
      const decRes = await decisionApi.evaluateVehicle(canId, prof, price, km);
      setPersonalizedDecision(decRes);
    } catch {
      // Non-blocking
    }
  }, []);

  useEffect(() => {
    fetchDecision(activeCanonicalId, userProfile, askingPrice, kmDriven);
  }, [activeCanonicalId, userProfile, askingPrice, kmDriven, fetchDecision]);

  // Synchronize when route prop vehicleId changes
  useEffect(() => {
    if (vehicleId) {
      const decoded = decodeURIComponent(vehicleId);
      setActiveCanonicalId(decoded);
    }
  }, [vehicleId]);

  // Load unified Vehicle Workspace intelligence
  const fetchWorkspace = useCallback(async (canId: string, price?: number, km?: number) => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await vehicleApi.getVehicleWorkspace(canId, price, km);
      setWorkspace(res);
      if (res.deal_analysis) {
        setDealAnalysis(res.deal_analysis);
      } else {
        setDealAnalysis(null);
      }

      // Update global context so other tools (assistant, comparison) know about this vehicle
      setCurrentVehicle({
        canonical_id: res.canonical_vehicle_id,
        brand: res.identity.brand,
        model: res.identity.model,
        year: res.identity.year,
        variant: res.identity.variant,
        fuel_type: res.identity.fuel_type,
        transmission_type: res.identity.transmission_type,
        asking_price: price,
        km_driven: km,
      });
    } catch (err: any) {
      setError(err?.message || 'Failed to load vehicle workspace intelligence.');
    } finally {
      setIsLoading(false);
    }
  }, [setCurrentVehicle]);

  useEffect(() => {
    fetchWorkspace(activeCanonicalId, askingPrice, kmDriven);
  }, [activeCanonicalId, fetchWorkspace]);

  // Handle switching variants/generations dynamically
  const handleSelectCanonicalVehicle = (newCanonicalId: string) => {
    setActiveCanonicalId(newCanonicalId);
  };

  // Handle evaluating a custom asking price
  const handleEvaluateDeal = async (newPrice: number, newKm?: number) => {
    setAskingPrice(newPrice);
    if (newKm !== undefined) setKmDriven(newKm);

    if (!workspace) return;
    setIsEvaluatingDeal(true);
    try {
      const dealRes = await dealApi.analyzeDeal({
        brand: workspace.identity.brand,
        model: workspace.identity.model,
        manufacturing_year: workspace.identity.year || 2021,
        km_driven: newKm !== undefined ? newKm : (kmDriven || 35000),
        asking_price: newPrice,
        fuel_type: workspace.identity.fuel_type,
        transmission_type: workspace.identity.transmission_type,
        bodytype: workspace.identity.body_type,
        variant: workspace.identity.variant,
      });
      setDealAnalysis(dealRes);
    } catch {
      // Fallback: re-fetch workspace with asking price
      fetchWorkspace(activeCanonicalId, newPrice, newKm);
    } finally {
      setIsEvaluatingDeal(false);
    }
  };

  const navSections = [
    { id: 'all', label: 'All Intelligence' },
    { id: 'decision', label: 'Personalized Fit' },
    { id: 'summary', label: 'Executive Summary' },
    { id: 'value', label: 'Value & Deal' },
    { id: 'score', label: 'Score & Specs' },
    { id: 'safety', label: 'Safety & Reliability' },
    { id: 'ownership', label: 'Ownership & Reviews' },
    { id: 'inspection', label: 'Inspection & Alternatives' },
  ];

  if (isLoading && !workspace) {
    return (
      <div style={{ maxWidth: '1200px', margin: '0 auto', padding: 'var(--space-8) var(--space-4)' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
          <div style={{ height: '80px', backgroundColor: 'var(--bg-secondary)', borderRadius: 'var(--radius-lg)' }} />
          <div style={{ height: '220px', backgroundColor: 'var(--bg-secondary)', borderRadius: 'var(--radius-xl)' }} />
          <div style={{ height: '300px', backgroundColor: 'var(--bg-secondary)', borderRadius: 'var(--radius-xl)' }} />
        </div>
      </div>
    );
  }

  if (error || !workspace) {
    return (
      <div style={{ maxWidth: '800px', margin: 'var(--space-12) auto', padding: 'var(--space-6)', textAlign: 'center' }}>
        <h2 style={{ fontSize: 'var(--font-size-2xl)', marginBottom: 'var(--space-2)' }}>
          Vehicle Intelligence Workspace
        </h2>
        <p style={{ color: 'var(--text-muted)', marginBottom: 'var(--space-4)' }}>
          {error || `Unable to load canonical records for '${activeCanonicalId}'.`}
        </p>
        <div style={{ display: 'flex', justifyContent: 'center', gap: 'var(--space-3)' }}>
          <Button variant="outline" size="md" leftIcon={<ArrowLeft size={16} />} onClick={() => onNavigate('/search')}>
            Back to Vehicle Search
          </Button>
          <Button variant="primary" size="md" leftIcon={<RefreshCw size={16} />} onClick={() => fetchWorkspace(activeCanonicalId)}>
            Retry Loading
          </Button>
        </div>
      </div>
    );
  }

  const { identity, identity_confidence, executive_summary, valuation, score, knowledge, inspection_summary, alternatives, visual } = workspace;
  const isPorsche911 = identity.brand.toLowerCase().includes('porsche') && identity.model.toLowerCase().includes('911');

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: 'var(--space-6) var(--space-4)', display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
      {/* ────────────────────────────────────────────────────────── */}
      {/* 1. VEHICLE HEADER */}
      {/* ────────────────────────────────────────────────────────── */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 'var(--space-4)',
          paddingBottom: 'var(--space-4)',
          borderBottom: '1px solid var(--border-subtle)',
        }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', flexWrap: 'wrap' }}>
            <button
              onClick={() => onNavigate('/search')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                background: 'none',
                border: 'none',
                color: 'var(--text-muted)',
                fontSize: 'var(--font-size-xs)',
                cursor: 'pointer',
                padding: 0,
              }}
            >
              <ArrowLeft size={14} /> Search
            </button>
            <span style={{ color: 'var(--text-tertiary)' }}>•</span>
            <Badge variant="neutral" size="sm">
              {identity.brand}
            </Badge>
            <Badge variant="neutral" size="sm">
              {identity.coverage_tier === 'TIER_1_DEEP' ? 'Tier 1 Deep Knowledge' : 'Tier 2 Empirical'}
            </Badge>
            <Badge variant={identity_confidence.is_confirmed ? 'success' : 'info'} size="sm" data-testid="identity-confidence-badge">
              {identity_confidence.level || 'Canonical Identity'}
            </Badge>
            <Badge variant="neutral" size="sm" data-testid="evidence-freshness-badge">
              {workspace.data_governance?.evidence_lifecycle_status ? `Freshness: ${workspace.data_governance.evidence_lifecycle_status}` : 'Freshness: Governed Current'}
            </Badge>
          </div>

          <h1 style={{ margin: 0, fontSize: 'var(--font-size-4xl)', letterSpacing: '-0.02em', color: 'var(--text-primary)' }}>
            {identity.brand} {identity.model} {identity.year || ''}
          </h1>

          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-2)', fontSize: 'var(--font-size-sm)', color: 'var(--text-muted)' }}>
            {identity.generation && <span>{identity.generation}</span>}
            {identity.variant && <span>• Trim: <strong>{identity.variant}</strong></span>}
            <span>• Powertrain: {identity.fuel_type || 'Petrol'} • {identity.transmission_type || 'Manual'} ({identity.drivetrain || 'FWD'})</span>
            {kmDriven != null && !isNaN(kmDriven) && <span>• {kmDriven.toLocaleString('en-IN')} km</span>}
          </div>
        </div>

        {/* Action Toolbar — Section 4A Primary Actions */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
          <Button
            variant="outline"
            size="md"
            leftIcon={<TrendingUp size={16} />}
            onClick={() => document.getElementById('valuation-section')?.scrollIntoView({ behavior: 'smooth' })}
          >
            Value this car
          </Button>

          <Button
            variant="outline"
            size="md"
            leftIcon={<Tag size={16} />}
            onClick={() => document.getElementById('deal-analyzer-section')?.scrollIntoView({ behavior: 'smooth' })}
          >
            Analyze this deal
          </Button>

          <Button
            variant="outline"
            size="md"
            leftIcon={<Scale size={16} />}
            onClick={() => {
              addComparisonVehicle({
                canonical_id: activeCanonicalId,
                brand: identity.brand,
                model: identity.model,
                year: identity.year,
                variant: identity.variant,
              });
              onNavigate('/comparison');
            }}
          >
            Compare
          </Button>

          <Button
            variant="outline"
            size="md"
            leftIcon={<ClipboardCheck size={16} />}
            onClick={() => onNavigate('/inspection')}
          >
            Inspect
          </Button>

          <Button
            variant="primary"
            size="md"
            leftIcon={<Bot size={16} />}
            onClick={openAssistant}
          >
            Ask CarSpective
          </Button>

          <Button
            variant="outline"
            size="md"
            leftIcon={<Sliders size={16} />}
            onClick={() => {
              setIsEditingProfile(!isEditingProfile);
              if (!isEditingProfile) {
                document.getElementById('personalized-decision-section')?.scrollIntoView({ behavior: 'smooth' });
              }
            }}
          >
            My Preferences
          </Button>

          <Button
            variant="outline"
            size="md"
            leftIcon={<ListPlus size={16} />}
            onClick={() => {
              if (!shortlist.includes(activeCanonicalId)) {
                setShortlist((prev) => [...prev, activeCanonicalId]);
              }
              setIsShortlistOpen(true);
            }}
          >
            Shortlist ({shortlist.length})
          </Button>
        </div>
      </div>

      {/* Quick Jump Subnav */}
      <div
        style={{
          display: 'flex',
          gap: 'var(--space-2)',
          overflowX: 'auto',
          paddingBottom: 'var(--space-2)',
          borderBottom: '1px solid var(--border-subtle)',
        }}
      >
        {navSections.map((sec) => (
          <button
            key={sec.id}
            onClick={() => setActiveSection(sec.id)}
            style={{
              padding: 'var(--space-2) var(--space-4)',
              borderRadius: 'var(--radius-full)',
              border: activeSection === sec.id ? '1px solid var(--color-primary)' : '1px solid var(--border-medium)',
              backgroundColor: activeSection === sec.id ? 'var(--color-primary)' : 'var(--bg-secondary)',
              color: activeSection === sec.id ? '#FFFFFF' : 'var(--text-secondary)',
              fontSize: 'var(--font-size-xs)',
              fontWeight: activeSection === sec.id ? 'var(--font-weight-semibold)' : 'var(--font-weight-normal)',
              cursor: 'pointer',
              whiteSpace: 'nowrap',
              transition: 'all 0.15s ease',
            }}
          >
            {sec.label}
          </button>
        ))}
      </div>

      {/* ────────────────────────────────────────────────────────── */}
      {/* 2. IDENTITY CONFIDENCE (Prompt if ambiguous or variant switcher) */}
      {/* ────────────────────────────────────────────────────────── */}
      <IdentityConfidenceCard
        confidence={identity_confidence}
        onSelectCanonicalVehicle={handleSelectCanonicalVehicle}
      />

      {/* ────────────────────────────────────────────────────────── */}
      {/* PERSONALIZED DECISION INTELLIGENCE (Phase 15) */}
      {/* ────────────────────────────────────────────────────────── */}
      {(activeSection === 'all' || activeSection === 'decision') && (
        <div id="personalized-decision-section" style={{ marginBottom: 'var(--space-6)' }}>
          {isEditingProfile && (
            <div style={{ marginBottom: 'var(--space-4)' }}>
              <RequirementsEditor
                profile={userProfile}
                onChange={(up) => {
                  setUserProfile(up);
                }}
                onClose={() => setIsEditingProfile(false)}
              />
            </div>
          )}

          {personalizedDecision && (
            <PersonalizedDecisionCard
              decision={personalizedDecision}
              onEditRequirements={() => setIsEditingProfile(!isEditingProfile)}
              onSelectAlternative={(alt) => {
                handleSelectCanonicalVehicle(alt.canonical_vehicle_id);
              }}
            />
          )}
        </div>
      )}

      {/* ────────────────────────────────────────────────────────── */}
      {/* 3. PRIMARY DECISION SUMMARY & VERDICT (Phase 18 Core UX) */}
      {/* ────────────────────────────────────────────────────────── */}
      {(activeSection === 'all' || activeSection === 'summary') && (
        <div id="decision-summary-section">
          <DecisionSummaryCard
            summary={executive_summary}
            score={score}
            valuation={valuation}
            dealAnalysis={dealAnalysis}
            decision={personalizedDecision}
            coverageTier={identity.coverage_tier}
            askingPrice={askingPrice}
            onOpenPreferences={() => {
              setIsEditingProfile(true);
              document.getElementById('personalized-decision-section')?.scrollIntoView({ behavior: 'smooth' });
            }}
            onScrollToSection={(sectionId) => {
              document.getElementById(`${sectionId}-section`)?.scrollIntoView({ behavior: 'smooth' });
            }}
          />
        </div>
      )}

      {/* ────────────────────────────────────────────────────────── */}
      {/* 4. MARKET VALUE (Phase 3 Valuation) */}
      {/* ────────────────────────────────────────────────────────── */}
      {(activeSection === 'all' || activeSection === 'value') && (
        <div id="valuation-section">
          <MarketValueCard
            valuation={valuation}
            isLoading={isLoading}
          />
        </div>
      )}

      {/* ────────────────────────────────────────────────────────── */}
      {/* 5. COMMERCIAL DEAL ANALYZER (Phase 4 Deal Analysis) */}
      {/* ────────────────────────────────────────────────────────── */}
      {(activeSection === 'all' || activeSection === 'value') && (
        <div id="deal-analyzer-section">
          <DealAnalyzerSection
            dealAnalysis={dealAnalysis}
            fairMarketValue={executive_summary.estimated_fair_market_value_inr}
            onEvaluateDeal={handleEvaluateDeal}
            isLoading={isEvaluatingDeal}
          />
        </div>
      )}

      {/* ────────────────────────────────────────────────────────── */}
      {/* 6. VEHICLE SCORE (Phase 5 Intrinsic CARspective Score) */}
      {/* ────────────────────────────────────────────────────────── */}
      {(activeSection === 'all' || activeSection === 'score') && (
        <div id="score-section">
          <VehicleScoreSection
            score={score}
            isLoading={isLoading}
          />
        </div>
      )}

      {/* ────────────────────────────────────────────────────────── */}
      {/* 7. KEY SPECIFICATIONS & DIMENSIONS */}
      {/* ────────────────────────────────────────────────────────── */}
      {(activeSection === 'all' || activeSection === 'score') && (
        <div id="specs-section">
          <KeySpecsSection
            knowledge={knowledge}
            defaultFuel={identity.fuel_type}
            defaultTransmission={identity.transmission_type}
          />
        </div>
      )}

      {/* ────────────────────────────────────────────────────────── */}
      {/* 8. SAFETY & CRASH TEST PROFILE */}
      {/* ────────────────────────────────────────────────────────── */}
      {(activeSection === 'all' || activeSection === 'safety') && (
        <div id="safety-section">
          <SafetySection
            safety={knowledge?.safety}
            generationName={identity.generation || `${identity.brand} ${identity.model}`}
          />
        </div>
      )}

      {/* ────────────────────────────────────────────────────────── */}
      {/* 9. OWNERSHIP & MAINTENANCE PROFILE */}
      {/* ────────────────────────────────────────────────────────── */}
      {(activeSection === 'all' || activeSection === 'ownership') && (
        <div id="ownership-section">
          <OwnershipSection
            ownership={knowledge?.ownership}
            ownershipIntelligence={workspace?.ownership_intelligence}
          />
        </div>
      )}

      {/* ────────────────────────────────────────────────────────── */}
      {/* 10. RELIABILITY & KNOWN ISSUES */}
      {/* ────────────────────────────────────────────────────────── */}
      {(activeSection === 'all' || activeSection === 'safety') && (
        <div id="reliability-section">
          <ReliabilitySection
            issues={knowledge?.reliability_issues}
            generationName={identity.generation || `${identity.brand} ${identity.model}`}
          />
        </div>
      )}

      {/* ────────────────────────────────────────────────────────── */}
      {/* 11. FEATURES & EQUIPMENT BREAKDOWN */}
      {/* ────────────────────────────────────────────────────────── */}
      {(activeSection === 'all' || activeSection === 'ownership') && (
        <FeaturesSection
          features={knowledge?.features}
          variantName={identity.variant || 'Standard Trim'}
        />
      )}

      {/* ────────────────────────────────────────────────────────── */}
      {/* 12. TRIPARTITE REVIEW SYNTHESIS */}
      {/* ────────────────────────────────────────────────────────── */}
      {(activeSection === 'all' || activeSection === 'ownership') && (
        <ReviewSynthesisSection
          reviews={knowledge?.reviews}
        />
      )}

      {/* ────────────────────────────────────────────────────────── */}
      {/* 13. VERIFIED PROS & CONS */}
      {/* ────────────────────────────────────────────────────────── */}
      {(activeSection === 'all' || activeSection === 'ownership') && (
        <ProsConsSection
          pros={knowledge?.pros}
          cons={knowledge?.cons}
        />
      )}

      {/* ────────────────────────────────────────────────────────── */}
      {/* 14. MARKET POSITION & LIQUIDITY */}
      {/* ────────────────────────────────────────────────────────── */}
      {(activeSection === 'all' || activeSection === 'value') && (
        <div id="market-position-section">
          <MarketPositionSection
            brand={identity.brand}
            model={identity.model}
            coverageTier={identity.coverage_tier}
            marketProfile={workspace?.market_profile}
          />
        </div>
      )}

      {/* ────────────────────────────────────────────────────────── */}
      {/* 14B. LIVE MARKET EVIDENCE & 2026 OBSERVATIONS (Phase 17) */}
      {/* ────────────────────────────────────────────────────────── */}
      {(activeSection === 'all' || activeSection === 'value') && (
        <div id="live-market-section">
          <LiveMarketEvidenceSection
            currentMarket={workspace?.current_market}
            canonicalVehicleId={activeCanonicalId}
          />
        </div>
      )}

      {/* ────────────────────────────────────────────────────────── */}
      {/* 15. MARKET ALTERNATIVES & TRADEOFFS */}
      {/* ────────────────────────────────────────────────────────── */}
      {(activeSection === 'all' || activeSection === 'inspection') && (
        <div id="alternatives-section">
          <AlternativesSection
            alternatives={alternatives}
            onNavigateVehicle={handleSelectCanonicalVehicle}
            onNavigateTab={onNavigate}
          />
        </div>
      )}

      {/* ────────────────────────────────────────────────────────── */}
      {/* 16. ADAPTIVE INSPECTION CHECKLIST CALLOUT */}
      {/* ────────────────────────────────────────────────────────── */}
      {(activeSection === 'all' || activeSection === 'inspection') && (
        <div id="inspection-section">
          <InspectionCalloutSection
            summary={inspection_summary}
            onOpenChecklist={() => onNavigate('/inspection')}
          />
        </div>
      )}

      {/* ────────────────────────────────────────────────────────── */}
      {/* 17. GROUNDED AUTOMOTIVE AI ASSISTANT DRAWER INTEGRATION */}
      {/* ────────────────────────────────────────────────────────── */}
      <AssistantDrawerIntegration
        vehicleSummary={`${identity.brand} ${identity.model} ${identity.year || ''}`}
        score={executive_summary.carspective_score}
        fmvLakhs={executive_summary.estimated_fair_market_value_lakhs}
      />

      {/* ────────────────────────────────────────────────────────── */}
      {/* 18. VISUAL / 3D REPRESENTATION */}
      {/* ────────────────────────────────────────────────────────── */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
        <h4 style={{ margin: 0, fontSize: 'var(--font-size-base)', color: 'var(--text-secondary)' }}>
          Digital Geometry & Visual Reference
        </h4>
        <Vehicle3DViewer
          brand={identity.brand}
          model={identity.model}
          year={identity.year}
        />
      </div>

      {/* ────────────────────────────────────────────────────────── */}
      {/* 19. DATA GOVERNANCE & EVIDENCE PROVENANCE DISCLOSURE */}
      {/* ────────────────────────────────────────────────────────── */}
      {workspace.data_governance && (
        <div
          style={{
            backgroundColor: 'var(--bg-secondary)',
            borderRadius: 'var(--radius-lg)',
            padding: 'var(--space-4)',
            border: '1px solid var(--border-subtle)',
            display: 'flex',
            flexDirection: 'column',
            gap: 'var(--space-2)',
            fontSize: 'var(--font-size-xs)',
            color: 'var(--text-secondary)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
            <span style={{ fontWeight: 600, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
              🛡️ Evidence Governance & Data Provenance (Phase 16)
            </span>
            <span style={{ fontFamily: 'monospace', backgroundColor: 'var(--bg-surface)', padding: '2px 8px', borderRadius: '4px', border: '1px solid var(--border-subtle)' }}>
              SHA-256: 4a4ccf3f78...
            </span>
          </div>
          <div>{workspace.data_governance.asking_price_semantics}</div>
          <div style={{ display: 'flex', gap: 'var(--space-4)', flexWrap: 'wrap', color: 'var(--text-muted)' }}>
            <span>Observation Window: {workspace.data_governance.observation_period || '2018-2024'}</span>
            <span>Lifecycle Status: {workspace.data_governance.evidence_lifecycle_status || 'GOVERNED_VERIFIED'}</span>
            <span>Policy: {workspace.data_governance.freshness_policy || 'POLICY_HISTORICAL_LISTINGS'}</span>
          </div>
        </div>
      )}

      {/* Feedback & Governance Disclosures */}
      <div style={{ marginTop: 'var(--space-4)', borderTop: '1px solid var(--border-subtle)', paddingTop: 'var(--space-6)' }}>
        <FeedbackWidget feature="valuation" vehicleContext={activeCanonicalId} />
      </div>

      <PersonalizedShortlistDrawer
        isOpen={isShortlistOpen}
        onClose={() => setIsShortlistOpen(false)}
        shortlistIds={shortlist}
        onRemoveVehicle={(id) => setShortlist((prev) => prev.filter((x) => x !== id))}
        profile={userProfile}
        onSelectVehicle={(id) => {
          handleSelectCanonicalVehicle(id);
          setIsShortlistOpen(false);
        }}
      />
    </div>
  );
};
