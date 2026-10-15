import React from 'react';
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { EvidenceBadge } from '../components/common/EvidenceBadge';
import { StatusBadge } from '../components/common/StatusBadge';

describe('Evidence & Status Governance Tests', () => {
  it('renders all 7 canonical evidence states correctly', () => {
    const states = [
      { state: 'VERIFIED', expectedText: 'Verified Evidence' },
      { state: 'SUPPORTED', expectedText: 'Supported' },
      { state: 'EMPIRICAL', expectedText: 'Empirical Baseline' },
      { state: 'MODEL_ESTIMATE', expectedText: 'Model Estimate' },
      { state: 'USER_STATED', expectedText: 'User Stated' },
      { state: 'INSUFFICIENT_DATA', expectedText: 'Insufficient Data' },
      { state: 'UNVERIFIED', expectedText: 'Unverified Claim' },
    ];

    states.forEach(({ state, expectedText }) => {
      const { unmount } = render(<EvidenceBadge state={state as any} />);
      expect(screen.getByText(expectedText)).toBeInTheDocument();
      unmount();
    });
  });

  it('renders StatusBadge statuses with semantic text and never relies on color alone', () => {
    const { rerender } = render(<StatusBadge status="PASS" />);
    expect(screen.getByText('PASS')).toBeInTheDocument();
    expect(screen.getByLabelText(/Inspection finding status: PASS/i)).toBeInTheDocument();

    rerender(<StatusBadge status="ATTENTION" />);
    expect(screen.getByText('ATTENTION')).toBeInTheDocument();

    rerender(<StatusBadge status="FAIL" />);
    expect(screen.getByText('FAIL')).toBeInTheDocument();

    rerender(<StatusBadge status="UNKNOWN" />);
    expect(screen.getByText('UNKNOWN')).toBeInTheDocument();
  });

  it('INVARIANT: UNKNOWN status is never styled or presented as PASS', () => {
    const { container: unknownContainer } = render(<StatusBadge status="UNKNOWN" />);
    const unknownBadge = unknownContainer.querySelector('.status-badge');
    expect(unknownBadge).toHaveClass('status-unknown');
    expect(unknownBadge).not.toHaveClass('status-pass');

    const { container: passContainer } = render(<StatusBadge status="PASS" />);
    const passBadge = passContainer.querySelector('.status-badge');
    expect(passBadge).toHaveClass('status-pass');
    expect(passBadge).not.toHaveClass('status-unknown');
  });
});
