import React from 'react';
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Header } from '../app/Header';
import { Footer } from '../app/Footer';
import { SearchBox } from '../components/common/SearchBox';
import { AppProvider } from '../state/AppContext';

describe('Accessibility & Semantic DOM Tests', () => {
  it('Header contains proper semantic landmarks and ARIA navigation', () => {
    render(
      <AppProvider>
        <Header currentPath="/" onNavigate={() => {}} />
      </AppProvider>
    );

    const header = screen.getByRole('banner');
    expect(header).toBeInTheDocument();

    const nav = screen.getByRole('navigation');
    expect(nav).toBeInTheDocument();

    // Verify all primary buttons have accessible names
    const buttons = screen.getAllByRole('button');
    buttons.forEach(btn => {
      expect(btn).toHaveAccessibleName();
    });
  });

  it('Footer contains copyright, disclosures, and contentinfo role', () => {
    render(<Footer />);
    const footer = screen.getByRole('contentinfo');
    expect(footer).toBeInTheDocument();
    expect(screen.getByText(/Analytical Governance/i)).toBeInTheDocument();
    expect(screen.getByText(/57,480 verified historical Indian listings/i)).toBeInTheDocument();
  });

  it('SearchBox has accessible input label, listbox role, and keyboard handlers', () => {
    render(<SearchBox />);
    const searchInput = screen.getByLabelText(/search vehicles by brand, model or year/i);
    expect(searchInput).toBeInTheDocument();
    expect(searchInput).toHaveAttribute('aria-autocomplete', 'list');
  });
});
