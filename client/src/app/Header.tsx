import React, { useState } from 'react';
import { useApp } from '../state/AppContext';
import { Button } from '../components/common/Button';
import { Scale, Bot, Menu, X, CarFront } from 'lucide-react';

export interface HeaderProps {
  currentPath: string;
  onNavigate: (path: string) => void;
}

export const Header: React.FC<HeaderProps> = ({ currentPath, onNavigate }) => {
  const { comparisonVehicles, openAssistant } = useApp();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navLinks = [
    { label: 'Explore', path: '/' },
    { label: 'Value a Car', path: '/value' },
    { label: 'Analyze Deal', path: '/deal' },
    { label: 'Compare', path: '/compare' },
    { label: 'Inspect', path: '/inspect' },
  ];

  const handleNavClick = (path: string) => {
    onNavigate(path);
    setMobileMenuOpen(false);
  };

  return (
    <header
      style={{
        position: 'sticky',
        top: 0,
        zIndex: 100,
        backgroundColor: 'rgba(255, 255, 255, 0.95)',
        backdropFilter: 'blur(12px)',
        borderBottom: '1px solid var(--border-subtle)',
      }}
    >
      <div
        className="container"
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          height: '68px',
        }}
      >
        {/* Brand Logo & Product Promise */}
        <div
          onClick={() => handleNavClick('/')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--space-2)',
            cursor: 'pointer',
            userSelect: 'none',
          }}
        >
          <div
            style={{
              padding: '6px',
              backgroundColor: 'var(--text-primary)',
              borderRadius: 'var(--radius-md)',
              color: '#FFFFFF',
              display: 'flex',
            }}
          >
            <CarFront size={20} />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <span
              className="header-brand-title"
              style={{
                fontSize: 'var(--font-size-xl)',
                fontWeight: 'var(--font-weight-extrabold)',
                letterSpacing: '-0.03em',
                lineHeight: 1.1,
                color: 'var(--text-primary)',
              }}
            >
              CAR<span style={{ color: 'var(--accent-blue)' }}>spective</span>
            </span>
            <span
              className="header-brand-subtitle"
              style={{
                fontSize: '0.65rem',
                color: 'var(--text-muted)',
                letterSpacing: '0.04em',
                textTransform: 'uppercase',
                fontWeight: 'var(--font-weight-medium)',
              }}
            >
              Automotive Intelligence
            </span>
          </div>
        </div>

        {/* Desktop Navigation Links */}
        <nav
          className="desktop-nav"
        >
          {navLinks.map(link => {
            const isActive = currentPath === link.path;
            return (
              <button
                key={link.path}
                onClick={() => handleNavClick(link.path)}
                style={{
                  padding: 'var(--space-2) var(--space-3)',
                  borderRadius: 'var(--radius-md)',
                  fontSize: 'var(--font-size-sm)',
                  fontWeight: isActive ? 'var(--font-weight-bold)' : 'var(--font-weight-medium)',
                  color: isActive ? 'var(--accent-blue)' : 'var(--text-secondary)',
                  backgroundColor: isActive ? 'var(--accent-blue-light)' : 'transparent',
                  cursor: 'pointer',
                  transition: 'all var(--transition-fast)',
                }}
              >
                {link.label}
              </button>
            );
          })}
        </nav>

        {/* Action Controls: Comparison Tray & Persistent AI Assistant */}
        <div className="header-actions" style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
          {comparisonVehicles.length > 0 && (
            <Button
              variant="outline"
              size="sm"
              leftIcon={<Scale size={14} />}
              onClick={() => handleNavClick('/compare')}
              className="header-compare-btn"
              aria-label={`Compare ${comparisonVehicles.length} vehicles`}
            >
              <span className="header-btn-text-full">Compare ({comparisonVehicles.length})</span>
              <span className="header-btn-text-compact">({comparisonVehicles.length})</span>
            </Button>
          )}

          <Button
            variant="primary"
            size="sm"
            leftIcon={<Bot size={14} />}
            onClick={openAssistant}
            className="header-assistant-btn"
            aria-label="Ask CarSpective AI Assistant"
          >
            <span className="header-btn-text-full">Ask CarSpective</span>
            <span className="header-btn-text-compact">Ask AI</span>
          </Button>

          {/* Mobile Menu Toggle Button */}
          <button
            onClick={() => setMobileMenuOpen(prev => !prev)}
            aria-label="Toggle navigation menu"
            className="mobile-nav-toggle"
            style={{
              padding: 'var(--space-2)',
              borderRadius: 'var(--radius-md)',
              color: 'var(--text-primary)',
              cursor: 'pointer',
            }}
          >
            {mobileMenuOpen ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div
          style={{
            backgroundColor: 'var(--bg-primary)',
            borderBottom: '1px solid var(--border-medium)',
            padding: 'var(--space-4)',
            display: 'flex',
            flexDirection: 'column',
            gap: 'var(--space-2)',
          }}
        >
          {navLinks.map(link => (
            <button
              key={link.path}
              onClick={() => handleNavClick(link.path)}
              style={{
                padding: 'var(--space-3)',
                textAlign: 'left',
                fontSize: 'var(--font-size-base)',
                fontWeight: 'var(--font-weight-medium)',
                color: currentPath === link.path ? 'var(--accent-blue)' : 'var(--text-primary)',
                borderRadius: 'var(--radius-md)',
                backgroundColor: currentPath === link.path ? 'var(--accent-blue-light)' : 'transparent',
              }}
            >
              {link.label}
            </button>
          ))}
        </div>
      )}
    </header>
  );
};
