import '@testing-library/jest-dom';
import { vi } from 'vitest';

// JSDOM does not implement window.scrollTo
window.scrollTo = vi.fn();
