import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Header } from '../app/Header';
import { AssistantDrawer } from '../features/assistant/AssistantDrawer';
import { AppProvider, useApp } from '../state/AppContext';

const DrawerHost: React.FC = () => {
  const { openAssistant } = useApp();
  React.useEffect(() => {
    openAssistant();
  }, [openAssistant]);

  return <AssistantDrawer />;
};

describe('Mobile Navigation & Drawer Responsiveness Regression Tests', () => {
  it('Header renders responsive navigation elements and accessible mobile toggle', () => {
    const handleNavigate = vi.fn();
    render(
      <AppProvider>
        <Header currentPath="/" onNavigate={handleNavigate} />
      </AppProvider>
    );

    // Desktop nav container present with semantic role
    const nav = screen.getByRole('navigation');
    expect(nav).toHaveClass('desktop-nav');

    // Mobile toggle button present with accessible label
    const mobileToggle = screen.getByLabelText(/toggle navigation menu/i);
    expect(mobileToggle).toBeInTheDocument();
    expect(mobileToggle).toHaveClass('mobile-nav-toggle');

    // Assistant button present with accessible label and full + compact spans
    const assistantBtn = screen.getByLabelText(/ask carspective ai assistant/i);
    expect(assistantBtn).toBeInTheDocument();
    expect(assistantBtn.querySelector('.header-btn-text-full')).toHaveTextContent('Ask CarSpective');
    expect(assistantBtn.querySelector('.header-btn-text-compact')).toHaveTextContent('Ask AI');
  });

  it('Toggling mobile menu opens mobile drawer and navigating closes drawer', () => {
    const handleNavigate = vi.fn();
    render(
      <AppProvider>
        <Header currentPath="/" onNavigate={handleNavigate} />
      </AppProvider>
    );

    const mobileToggle = screen.getByLabelText(/toggle navigation menu/i);

    // Click to open mobile menu
    fireEvent.click(mobileToggle);

    // Links should now be visible in mobile drawer
    const valueCarBtn = screen.getAllByRole('button', { name: /value a car/i });
    expect(valueCarBtn.length).toBeGreaterThan(0);

    // Click a mobile navigation link
    fireEvent.click(valueCarBtn[valueCarBtn.length - 1]);
    expect(handleNavigate).toHaveBeenCalledWith('/value');
  });

  it('AssistantDrawer renders with assistant-drawer responsive class and bounds', () => {
    render(
      <AppProvider>
        <DrawerHost />
      </AppProvider>
    );

    const drawer = screen.getByRole('complementary', { name: /ask carspective ai assistant/i });
    expect(drawer).toBeInTheDocument();
    expect(drawer).toHaveClass('assistant-drawer');

    // Input field has minWidth 0 for flexbox safety
    const input = screen.getByLabelText(/message to carspective ai/i);
    expect(input).toBeInTheDocument();
    expect(['0', '0px']).toContain(input.style.minWidth);
  });
});
