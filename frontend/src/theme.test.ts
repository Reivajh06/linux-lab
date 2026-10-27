import { describe, expect, it } from 'vitest';
import { accentText, contrast, onAccent, palettes } from './theme';

describe('theme contrast', () => {
  it('keeps every palette accent readable as text and as a button fill', () => {
    for (const p of palettes) {
      expect(contrast(accentText(p.accent, p.surface), p.surface)).toBeGreaterThanOrEqual(4.5);
      expect(contrast(onAccent(p.accent), p.accent)).toBeGreaterThanOrEqual(4.5);
    }
  });
  it('lightens a dark custom accent and picks white text on it', () => {
    expect(accentText('#1a237e', '#242424')).not.toBe('#1a237e');
    expect(contrast(accentText('#1a237e', '#242424'), '#242424')).toBeGreaterThanOrEqual(4.5);
    expect(onAccent('#1a237e')).toBe('#ffffff');
    expect(onAccent('#dfb74c')).toBe('#17170f');
  });
});
