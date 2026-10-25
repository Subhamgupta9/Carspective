import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AssistantDrawer } from '../features/assistant/AssistantDrawer';
import { AppProvider, useApp, VehicleSelection } from '../state/AppContext';
import { assistantApi } from '../api/assistantApi';
import { AssistantResponse } from '../types';

// Helper component that opens the drawer and optionally sets currentVehicle
const TestHost: React.FC<{ initialVehicle?: VehicleSelection | null }> = ({ initialVehicle }) => {
  const { openAssistant, setCurrentVehicle } = useApp();
  React.useEffect(() => {
    openAssistant();
    if (initialVehicle !== undefined) {
      setCurrentVehicle(initialVehicle);
    }
  }, [openAssistant, setCurrentVehicle, initialVehicle]);

  return <AssistantDrawer />;
};

describe('CarSpective AI Assistant Drawer Integration Tests', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    window.HTMLElement.prototype.scrollIntoView = vi.fn();
  });

  it('renders drawer, sends chat message, and displays the response answer', async () => {
    const mockResponse: AssistantResponse = {
      session_id: 'test-session-123',
      answer: 'The 2021 Honda City has an estimated fair market value of ₹8,42,000.',
      intent: 'VALUATION',
      referenced_domains: ['VALUATION'],
      evidence_refs: ['valuation.fair_market_value'],
      evidence_bundle: [
        {
          id: 'valuation.fair_market_value',
          claim: 'Estimated fair market value is ₹8,42,000 based on historical listings.',
          source: 'VALUATION',
          evidence_state: 'VERIFIED',
          domain: 'VALUATION',
        },
      ],
      suggested_next_actions: ['Is the asking price fair?'],
    };

    const askSpy = vi.spyOn(assistantApi, 'askAssistant').mockResolvedValueOnce(mockResponse);

    render(
      <AppProvider>
        <TestHost />
      </AppProvider>
    );

    // Initial greeting must be visible
    expect(screen.getByText(/Grounded Automotive Intelligence/i)).toBeInTheDocument();
    expect(screen.getByText(/Hello, I'm the CarSpective Assistant/i)).toBeInTheDocument();

    const input = screen.getByLabelText(/Message to CarSpective AI/i);
    fireEvent.change(input, { target: { value: 'What is the valuation?' } });

    const sendBtn = screen.getByRole('button', { name: /send message/i });
    fireEvent.click(sendBtn);

    // Should call API
    await waitFor(() => {
      expect(askSpy).toHaveBeenCalledTimes(1);
    });

    // Check payload passed
    const sentPayload = askSpy.mock.calls[0][0];
    expect(sentPayload.message).toBe('What is the valuation?');

    // Assistant answer should appear on screen
    await waitFor(() => {
      expect(screen.getByText(/The 2021 Honda City has an estimated fair market value of ₹8,42,000/i)).toBeInTheDocument();
    });
  });

  it('transmits active vehicle context and asking price correctly in vehicle and listing payload', async () => {
    const customVehicle: VehicleSelection = {
      brand: 'Toyota',
      model: 'Innova Crysta',
      year: 2019,
      variant: '2.4 GX',
      fuel_type: 'Diesel',
      transmission_type: 'Manual',
      asking_price: 1650000,
      km_driven: 65000,
      canonical_id: 'toyota-innova-crysta-2019',
    };

    const mockResponse: AssistantResponse = {
      session_id: 'test-session-innova',
      answer: 'The asking price of ₹16,50,000 is fair for this Innova Crysta.',
      intent: 'DEAL_ANALYSIS',
      referenced_domains: ['DEAL_ANALYZER'],
      evidence_refs: ['deal.classification'],
      evidence_bundle: [],
      suggested_next_actions: [],
    };

    const askSpy = vi.spyOn(assistantApi, 'askAssistant').mockResolvedValueOnce(mockResponse);

    render(
      <AppProvider>
        <TestHost initialVehicle={customVehicle} />
      </AppProvider>
    );

    const input = screen.getByLabelText(/Message to CarSpective AI/i);
    fireEvent.change(input, { target: { value: 'Is this a fair deal?' } });

    const sendBtn = screen.getByRole('button', { name: /send message/i });
    fireEvent.click(sendBtn);

    await waitFor(() => {
      expect(askSpy).toHaveBeenCalledTimes(1);
    });

    const sentPayload = askSpy.mock.calls[0][0];
    expect(sentPayload.message).toBe('Is this a fair deal?');
    expect(sentPayload.vehicle).toEqual({
      brand: 'Toyota',
      model: 'Innova Crysta',
      manufacturing_year: 2019,
      variant: '2.4 GX',
      fuel_type: 'Diesel',
      transmission_type: 'Manual',
      km_driven: 65000,
      canonical_vehicle_id: 'toyota-innova-crysta-2019',
    });
    expect(sentPayload.listing).toEqual({
      asking_price: 1650000,
    });
  });

  it('renders citations with claim text and evidence state badges', async () => {
    const mockResponse: AssistantResponse = {
      session_id: 'test-session-citations',
      answer: 'Verified findings for Honda City deal analysis.',
      intent: 'DEAL_ANALYSIS',
      referenced_domains: ['DEAL_ANALYZER', 'VALUATION'],
      evidence_refs: ['deal.fairness', 'inspection.brakes'],
      evidence_bundle: [
        {
          id: 'deal.fairness',
          claim: 'Asking price ₹8,50,000 aligns within fair market envelope.',
          source: 'DEAL_ANALYZER',
          evidence_state: 'VERIFIED',
          domain: 'DEAL_ANALYZER',
        },
        {
          id: 'inspection.brakes',
          claim: 'Brake pads worn past 60%, replacement recommended.',
          source: 'INSPECTION',
          evidence_state: 'SUPPORTED',
          domain: 'INSPECTION',
        },
      ],
      suggested_next_actions: [],
    };

    vi.spyOn(assistantApi, 'askAssistant').mockResolvedValueOnce(mockResponse);

    render(
      <AppProvider>
        <TestHost />
      </AppProvider>
    );

    const input = screen.getByLabelText(/Message to CarSpective AI/i);
    fireEvent.change(input, { target: { value: 'Show evidence' } });

    const sendBtn = screen.getByRole('button', { name: /send message/i });
    fireEvent.click(sendBtn);

    await waitFor(() => {
      expect(screen.getByText('GROUNDED CITATIONS')).toBeInTheDocument();
    });

    expect(screen.getByText('Asking price ₹8,50,000 aligns within fair market envelope.')).toBeInTheDocument();
    expect(screen.getByText('Brake pads worn past 60%, replacement recommended.')).toBeInTheDocument();
    expect(screen.getByText('Verified Evidence')).toBeInTheDocument();
    expect(screen.getByText('Supported')).toBeInTheDocument();
  });

  it('displays a useful error message when the API request fails', async () => {
    vi.spyOn(assistantApi, 'askAssistant').mockRejectedValueOnce({
      detail: 'Vehicle data insufficient for valuation generation.',
    });

    render(
      <AppProvider>
        <TestHost />
      </AppProvider>
    );

    const input = screen.getByLabelText(/Message to CarSpective AI/i);
    fireEvent.change(input, { target: { value: 'Tell me about an unknown car' } });

    const sendBtn = screen.getByRole('button', { name: /send message/i });
    fireEvent.click(sendBtn);

    await waitFor(() => {
      expect(screen.getByText(/Vehicle data insufficient for valuation generation/i)).toBeInTheDocument();
    });
  });
});
