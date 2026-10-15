import { describe, expect, it } from 'vitest';
import { progressPercent } from './api';

describe('course progress', () => {
  it('handles an empty library and partial points', () => {
    expect(progressPercent(0, 0)).toBe(0);
    expect(progressPercent(5, 30)).toBe(17);
    expect(progressPercent(30, 30)).toBe(100);
  });
});
