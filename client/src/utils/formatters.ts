/**
 * CARspective — Number, Currency & Text Formatters
 * Formats Indian Rupee (INR) amounts into clean Lakh/Crore notation according to Indian market conventions.
 */

export function formatINR(amount?: number | null, fallback = '—'): string {
  if (amount === null || amount === undefined || isNaN(amount)) {
    return fallback;
  }

  const absAmount = Math.abs(amount);
  const sign = amount < 0 ? '-' : '';

  if (absAmount >= 10000000) {
    // 1 Crore = 10,000,000
    const cr = absAmount / 10000000;
    return `${sign}₹${cr.toFixed(2)} Cr`;
  } else if (absAmount >= 100000) {
    // 1 Lakh = 100,000
    const lakh = absAmount / 100000;
    return `${sign}₹${lakh.toFixed(2)} L`;
  } else {
    // Standard Indian number grouping
    return `${sign}₹${new Intl.NumberFormat('en-IN').format(absAmount)}`;
  }
}

export function formatINRFull(amount?: number | null, fallback = '—'): string {
  if (amount === null || amount === undefined || isNaN(amount)) {
    return fallback;
  }
  return `₹${new Intl.NumberFormat('en-IN').format(amount)}`;
}

export function formatKm(km?: number | null, fallback = '—'): string {
  if (km === null || km === undefined || isNaN(km)) {
    return fallback;
  }
  return `${new Intl.NumberFormat('en-IN').format(Math.round(km))} km`;
}

export function formatPercent(value?: number | null, includeSign = false, fallback = '—'): string {
  if (value === null || value === undefined || isNaN(value)) {
    return fallback;
  }
  const formatted = `${Math.abs(value).toFixed(1)}%`;
  if (includeSign) {
    return value > 0 ? `+${formatted}` : value < 0 ? `-${formatted}` : formatted;
  }
  return formatted;
}

export function cleanLabel(snakeCase?: string): string {
  if (!snakeCase) return '';
  return snakeCase
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
}
