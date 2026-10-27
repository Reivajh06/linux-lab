/**
 * Windows reports accent keys (´ ` ^ ¨ ~ on a Spanish keyboard) as key "Dead", which noVNC
 * cannot map to a keysym and drops. Compose them in the browser and send the finished character.
 */
export type Accent = { spacing: string; combining: string };

const acute = { spacing: '´', combining: '́' }, grave = { spacing: '`', combining: '̀' };
const circumflex = { spacing: '^', combining: '̂' }, diaeresis = { spacing: '¨', combining: '̈' };
const tilde = { spacing: '~', combining: '̃' };

// Spanish (Spain) dead keys by physical key: [plain, Shift, AltGr].
const SPANISH: Record<string, (Accent | undefined)[]> = {
  Quote: [acute, diaeresis], BracketLeft: [grave, circumflex], Digit4: [undefined, undefined, tilde],
};

/** The accent a dead key starts, or null for a layout we don't know (the OS may still compose it). */
export function deadAccent(code: string, shift: boolean, altGraph: boolean): Accent | null {
  return SPANISH[code]?.[altGraph ? 2 : shift ? 1 : 0] ?? null;
}

/** The text a dead key followed by `key` produces, following Windows: space gives the accent alone. */
export function compose(accent: Accent | null, key: string): string {
  if (!accent) return key;
  if (key === ' ') return accent.spacing;
  // Already composed by the OS (á, or "´x" for a letter without that accent).
  if (key.length !== 1 || key === accent.spacing || key.normalize('NFD') !== key) return key;
  const composed = (key + accent.combining).normalize('NFC');
  return composed.length === 1 ? composed : accent.spacing + key;
}

/** X11 keysym of one character: Latin-1 maps directly, everything else to the Unicode range. */
export function keysym(char: string) {
  const code = char.codePointAt(0)!;
  return code < 0x100 ? code : 0x1000000 + code;
}

const MODIFIERS = new Set(['Shift', 'Control', 'Alt', 'AltGraph', 'CapsLock']);

/** Intercept dead-key sequences on `target` before noVNC's canvas handler; `send` types the result. */
export function attachDeadKeys(target: HTMLElement, send: (text: string) => void) {
  let pending: { accent: Accent | null } | null = null;
  const keydown = (e: KeyboardEvent) => {
    if (e.isComposing) return;
    if (e.key === 'Dead') {
      if (pending?.accent) send(pending.accent.spacing); // Two dead keys in a row type the first one.
      pending = { accent: deadAccent(e.code, e.shiftKey, e.getModifierState('AltGraph')) };
      e.stopPropagation();
      return;
    }
    if (!pending || MODIFIERS.has(e.key)) return;
    const { accent } = pending;
    pending = null;
    const shortcut = (e.ctrlKey && !e.getModifierState('AltGraph')) || e.metaKey;
    if (shortcut || /^[A-Z][A-Za-z0-9]+$/.test(e.key)) return; // Enter, Escape, arrows…: drop the accent.
    e.preventDefault(); e.stopPropagation();
    send(compose(accent, e.key));
  };
  target.addEventListener('keydown', keydown, true);
  return () => target.removeEventListener('keydown', keydown, true);
}
