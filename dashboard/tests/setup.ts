import '@testing-library/jest-dom/vitest';
import { expect, afterEach, vi} from 'vitest';
import { cleanup } from '@testing-library/react';

// Cleanup after each test
afterEach(() => {
  cleanup();
});

// Mock WebSocket globally
global.WebSocket = vi.fn() as any;
