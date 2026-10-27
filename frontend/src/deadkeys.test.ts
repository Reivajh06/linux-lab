import { describe, expect, it } from 'vitest';
import { compose, deadAccent, keysym } from './deadkeys';

describe('dead keys', () => {
  it('finds Spanish accents by physical key', () => {
    expect(deadAccent('Quote', false, false)?.spacing).toBe('´');
    expect(deadAccent('Quote', true, false)?.spacing).toBe('¨');
    expect(deadAccent('BracketLeft', false, false)?.spacing).toBe('`');
    expect(deadAccent('BracketLeft', true, false)?.spacing).toBe('^');
    expect(deadAccent('Digit4', false, true)?.spacing).toBe('~');
    expect(deadAccent('KeyQ', false, false)).toBeNull();
  });

  it('composes like Windows', () => {
    const acute = deadAccent('Quote', false, false), tilde = deadAccent('Digit4', false, true);
    expect(compose(tilde, ' ')).toBe('~');
    expect(compose(acute, 'a')).toBe('á');
    expect(compose(acute, 'E')).toBe('É');
    expect(compose(deadAccent('Quote', true, false), 'u')).toBe('ü');
    expect(compose(tilde, 'n')).toBe('ñ');
    expect(compose(acute, 'x')).toBe('´x');
    expect(compose(acute, 'á')).toBe('á');
    expect(compose(tilde, '~')).toBe('~');
    expect(compose(null, 'ç')).toBe('ç');
  });

  it('maps characters to X keysyms', () => {
    expect(keysym('~')).toBe(0x7e);
    expect(keysym('á')).toBe(0xe1);
    expect(keysym('ŵ')).toBe(0x1000175);
  });
});
