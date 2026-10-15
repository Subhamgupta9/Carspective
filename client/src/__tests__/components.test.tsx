import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Button } from '../components/common/Button';
import { Input } from '../components/common/Input';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { Range } from '../components/common/Range';
import { Modal } from '../components/common/Modal';
import { EmptyState } from '../components/common/EmptyState';
import { ErrorState } from '../components/common/ErrorState';
import { Toast } from '../components/common/Toast';

describe('Design System Common Components Tests', () => {
  it('renders Button and handles click events', () => {
    const handleClick = vi.fn();
    render(<Button onClick={handleClick}>Click Me</Button>);
    const btn = screen.getByRole('button', { name: /click me/i });
    fireEvent.click(btn);
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('renders Button loading and disabled states', () => {
    render(<Button isLoading disabled>Submit</Button>);
    const btn = screen.getByRole('button');
    expect(btn).toBeDisabled();
    expect(btn).toHaveAttribute('aria-busy', 'true');
  });

  it('renders Input with accessible labels and error messages', () => {
    render(
      <Input
        label="Asking Price"
        error="Asking price must be positive"
        helperText="In Indian Rupees"
        value=""
        onChange={() => {}}
      />
    );
    expect(screen.getByLabelText(/asking price/i)).toBeInTheDocument();
    expect(screen.getByRole('alert')).toHaveTextContent(/asking price must be positive/i);
    const input = screen.getByLabelText(/asking price/i);
    expect(input).toHaveAttribute('aria-invalid', 'true');
  });

  it('renders Card with children and interactive variant', () => {
    render(
      <Card interactive data-testid="test-card">
        <div>Card Content</div>
      </Card>
    );
    expect(screen.getByTestId('test-card')).toHaveClass('carspective-card-interactive');
    expect(screen.getByText('Card Content')).toBeInTheDocument();
  });

  it('renders Badge with variants and icons', () => {
    render(<Badge variant="success">Great Deal</Badge>);
    expect(screen.getByText('Great Deal').closest('.badge')).toHaveClass('badge-success');
  });

  it('renders Range component with bounds and marker position', () => {
    render(<Range low={700000} high={900000} point={800000} pointLabel="Asking Price" />);
    expect(screen.getByText(/Low: ₹7.00 L/i)).toBeInTheDocument();
    expect(screen.getByText(/High: ₹9.00 L/i)).toBeInTheDocument();
    expect(screen.getByText(/Asking Price: ₹8.00 L/i)).toBeInTheDocument();
  });

  it('renders Modal when open and handles escape key to close', () => {
    const handleClose = vi.fn();
    const { unmount } = render(
      <Modal isOpen={true} onClose={handleClose} title="Dialog Title">
        <p>Modal Body</p>
      </Modal>
    );
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('Dialog Title')).toBeInTheDocument();
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(handleClose).toHaveBeenCalled();
    unmount();
  });

  it('renders EmptyState with action', () => {
    render(
      <EmptyState
        title="No Saved Cars"
        description="Search vehicles to add them."
        action={<button>Add Car</button>}
      />
    );
    expect(screen.getByText('No Saved Cars')).toBeInTheDocument();
    expect(screen.getByText('Search vehicles to add them.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /add car/i })).toBeInTheDocument();
  });

  it('renders ErrorState with what still works and retry button', () => {
    const handleRetry = vi.fn();
    render(
      <ErrorState
        title="Valuation Unavailable"
        message="Cannot reach pricing service."
        whatStillWorks="Vehicle specs and inspection checklists remain available."
        onRetry={handleRetry}
      />
    );
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText(/valuation unavailable/i)).toBeInTheDocument();
    expect(screen.getByText(/what still works/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /try again/i }));
    expect(handleRetry).toHaveBeenCalledTimes(1);
  });

  it('renders Toast notification and dismisses', () => {
    const handleDismiss = vi.fn();
    render(<Toast id="1" message="Test Notification" onDismiss={handleDismiss} />);
    expect(screen.getByRole('status')).toHaveTextContent('Test Notification');
    fireEvent.click(screen.getByLabelText(/dismiss toast/i));
    expect(handleDismiss).toHaveBeenCalledWith('1');
  });
});
