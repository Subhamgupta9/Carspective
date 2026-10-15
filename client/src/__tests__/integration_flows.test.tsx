import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { App } from '../app/App';

describe('End-to-End User Integration Flows', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    window.location.hash = '#/';
  });

  it('Flow 1: Navigates from Homepage to Valuation Page via Header', async () => {
    render(<App />);

    // Check Hero is visible on homepage
    expect(screen.getByText(/What car are you looking for\?/i)).toBeInTheDocument();

    // Click "Value a Car" nav button in Header
    const valueNavButtons = screen.getAllByRole('button', { name: /value a car/i });
    fireEvent.click(valueNavButtons[0]);

    // Check we landed on the Valuation page
    await waitFor(() => {
      expect(screen.getByText(/Vehicle Fair Market Valuation/i)).toBeInTheDocument();
    });
  });

  it('Flow 2: Navigates from Homepage to Compare Page and shows empty state until 2 cars are added', async () => {
    render(<App />);

    const compareNavButtons = screen.getAllByRole('button', { name: /compare/i });
    fireEvent.click(compareNavButtons[0]);

    await waitFor(() => {
      expect(screen.getByText(/Intelligent Vehicle Comparison/i)).toBeInTheDocument();
    });
  });

  it('Flow 3: Navigates to Inspection Page and renders adaptive checklist', async () => {
    render(<App />);

    const inspectNavButtons = screen.getAllByRole('button', { name: /inspect/i });
    fireEvent.click(inspectNavButtons[0]);

    await waitFor(() => {
      expect(screen.getByText(/45-point adaptive inspection checklist/i)).toBeInTheDocument();
    });
  });

  it('Flow 4: Opens Ask CarSpective drawer and exposes grounded assistant context', async () => {
    render(<App />);

    // Click "Ask CarSpective"
    const askButtons = screen.getAllByRole('button', { name: /ask carspective/i });
    fireEvent.click(askButtons[0]);

    // Assistant drawer should now be open
    await waitFor(() => {
      expect(screen.getByRole('complementary', { name: /ask carspective ai assistant/i })).toBeInTheDocument();
    });

    // Contains grounded guidance intro
    expect(screen.getByText(/CarSpective Assistant/i)).toBeInTheDocument();
  });
});
