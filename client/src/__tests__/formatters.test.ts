import { describe, it, expect } from 'vitest';
import { formatINR, formatINRFull, formatKm, formatPercent, cleanLabel } from '../utils/formatters';

describe('Formatters Unit Tests', () => {
  it('formats Indian Rupees into Lakhs correctly', () => {
    expect(formatINR(850000)).toBe('₹8.50 L');
    expect(formatINR(1425000)).toBe('₹14.25 L');
    expect(formatINR(72000)).toBe('₹72,000');
  });

  it('formats Crores correctly', () => {
    expect(formatINR(12000000)).toBe('₹1.20 Cr');
    expect(formatINR(25000000)).toBe('₹2.50 Cr');
  });

  it('handles zero and negative amounts', () => {
    expect(formatINR(0)).toBe('₹0');
    expect(formatINR(-50000)).toBe('-₹50,000');
    expect(formatINR(-850000)).toBe('-₹8.50 L');
  });

  it('handles null and undefined fallbacks gracefully', () => {
    expect(formatINR(null)).toBe('—');
    expect(formatINR(undefined)).toBe('—');
    expect(formatINR(NaN, 'N/A')).toBe('N/A');
  });

  it('formats full INR with commas', () => {
    expect(formatINRFull(850000)).toBe('₹8,50,000');
    expect(formatINRFull(12500000)).toBe('₹1,25,00,000');
  });

  it('formats kilometers', () => {
    expect(formatKm(35000)).toBe('35,000 km');
    expect(formatKm(120450)).toBe('1,20,450 km');
    expect(formatKm(null)).toBe('—');
  });

  it('formats percentages with optional sign', () => {
    expect(formatPercent(12.5)).toBe('12.5%');
    expect(formatPercent(12.5, true)).toBe('+12.5%');
    expect(formatPercent(-8.3, true)).toBe('-8.3%');
    expect(formatPercent(0, true)).toBe('0.0%');
  });

  it('cleans snake_case labels into title case', () => {
    expect(cleanLabel('great_deal')).toBe('Great Deal');
    expect(cleanLabel('structural_safety')).toBe('Structural Safety');
  });
});
