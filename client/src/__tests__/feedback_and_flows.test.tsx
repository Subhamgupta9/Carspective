import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { FeedbackWidget } from '../features/feedback/FeedbackWidget';
import { AppProvider } from '../state/AppContext';

describe('Feedback Widget & Interaction Tests', () => {
  it('renders feedback question and allows voting Yes', () => {
    render(
      <AppProvider>
        <FeedbackWidget feature="valuation" />
      </AppProvider>
    );

    expect(screen.getByText(/was this analysis useful\?/i)).toBeInTheDocument();
    const yesButton = screen.getByRole('button', { name: /yes, this was useful/i });
    fireEvent.click(yesButton);

    // Shows optional comments form
    expect(screen.getByPlaceholderText(/what price did you expect\?/i)).toBeInTheDocument();

    // Submit feedback
    const submitBtn = screen.getByRole('button', { name: /submit feedback/i });
    fireEvent.click(submitBtn);

    expect(screen.getByText(/feedback received/i)).toBeInTheDocument();
  });

  it('allows voting No and submitting without mandatory account', () => {
    render(
      <AppProvider>
        <FeedbackWidget feature="deal" />
      </AppProvider>
    );

    const noButton = screen.getByRole('button', { name: /no, this was not useful/i });
    fireEvent.click(noButton);

    const submitBtn = screen.getByRole('button', { name: /submit feedback/i });
    fireEvent.click(submitBtn);

    expect(screen.getByText(/feedback received/i)).toBeInTheDocument();
  });
});
