import type { Result } from './api';

/** Short UI sounds, synthesized with Web Audio so the app ships no audio files. */
export type Sound = 'course' | 'complete' | 'progress' | 'wrong' | 'regress' | 'error' | 'ready' | 'generated';

const SETTINGS_KEY = 'linuxlab.sound';
export type SoundSettings = { enabled: boolean; volume: number };
const defaultSettings: SoundSettings = { enabled: true, volume: 0.6 };

export function readSoundSettings(): SoundSettings {
  try {
    const saved = JSON.parse(localStorage.getItem(SETTINGS_KEY) || 'null');
    if (saved && typeof saved.enabled === 'boolean' && typeof saved.volume === 'number') return { enabled: saved.enabled, volume: Math.min(1, Math.max(0, saved.volume)) };
  } catch { /* Storage unavailable or corrupt: use defaults. */ }
  return { ...defaultSettings };
}
let settings = readSoundSettings();
export function saveSoundSettings(next: SoundSettings) {
  settings = next;
  try { localStorage.setItem(SETTINGS_KEY, JSON.stringify(next)); } catch { /* Not persisted. */ }
}

/**
 * Which sound an evaluation deserves, comparing the results before and after it.
 * Completing the whole course beats completing an exercise, which beats partial progress;
 * losing points or still failing gets the "wrong" sounds.
 */
export function evaluationSound(before: Record<string, Result>, after: Result[], exerciseIds: string[]): Sound | null {
  if (!after.length) return null;
  const complete = (r?: Result) => !!r && r.available > 0 && r.earned >= r.available;
  const merged = { ...before, ...Object.fromEntries(after.map(r => [r.exercise_id, r])) };
  const newlyComplete = after.some(r => complete(r) && !complete(before[r.exercise_id]));
  if (newlyComplete && exerciseIds.length > 0 && exerciseIds.every(id => complete(merged[id]))) return 'course';
  if (newlyComplete) return 'complete';
  const delta = after.reduce((n, r) => n + r.earned - (before[r.exercise_id]?.earned ?? 0), 0);
  if (delta > 0) return 'progress';
  if (delta < 0) return 'regress';
  if (after.some(r => r.tasks.some(t => t.status === 'error'))) return 'error';
  if (after.every(complete)) return 'complete';
  return 'wrong';
}

type Note = { freq: number; at: number; length: number; type?: OscillatorType; gain?: number; slide?: number };
const C5 = 523.25, E5 = 659.25, G5 = 783.99, C6 = 1046.5, E6 = 1318.5, G4 = 392, A4 = 440, D5 = 587.33;
const tunes: Record<Sound, Note[]> = {
  // Bright major arpeggio.
  complete: [{ freq: C5, at: 0, length: .12 }, { freq: E5, at: .09, length: .12 }, { freq: G5, at: .18, length: .12 }, { freq: C6, at: .27, length: .35 }],
  // Longer fanfare with a held chord.
  course: [{ freq: G4, at: 0, length: .12 }, { freq: C5, at: .1, length: .12 }, { freq: E5, at: .2, length: .12 }, { freq: G5, at: .3, length: .14 },
    { freq: C6, at: .44, length: .7 }, { freq: E6, at: .44, length: .7, gain: .5 }, { freq: G5, at: .44, length: .7, gain: .5 }],
  // Two soft rising notes.
  progress: [{ freq: E5, at: 0, length: .1 }, { freq: A4 * 2, at: .1, length: .2 }],
  // Low falling buzz.
  wrong: [{ freq: 220, at: 0, length: .14, type: 'square', gain: .35 }, { freq: 165, at: .13, length: .26, type: 'square', gain: .35, slide: 140 }],
  // Descending three notes: you lost points.
  regress: [{ freq: G4, at: 0, length: .12, type: 'triangle' }, { freq: 330, at: .12, length: .12, type: 'triangle' }, { freq: 262, at: .24, length: .3, type: 'triangle' }],
  // Dissonant double blip.
  error: [{ freq: 300, at: 0, length: .09, type: 'sawtooth', gain: .25 }, { freq: 300, at: .14, length: .16, type: 'sawtooth', gain: .25, slide: 240 }],
  // Gentle chime.
  ready: [{ freq: G5, at: 0, length: .3, gain: .6 }, { freq: C6, at: .08, length: .4, gain: .5 }],
  generated: [{ freq: D5, at: 0, length: .12, gain: .7 }, { freq: G5, at: .1, length: .3, gain: .7 }],
};

let context: AudioContext | null = null;
export function play(sound: Sound | null) {
  if (!sound || !settings.enabled || settings.volume <= 0) return;
  try {
    context ??= new AudioContext();
    if (context.state === 'suspended') void context.resume();
    const ctx = context, start = ctx.currentTime + .02;
    const master = ctx.createGain();
    master.gain.value = settings.volume * .25;
    master.connect(ctx.destination);
    let end = 0;
    for (const note of tunes[sound]) {
      const osc = ctx.createOscillator(), env = ctx.createGain();
      const t0 = start + note.at, t1 = t0 + note.length;
      osc.type = note.type ?? 'sine';
      osc.frequency.setValueAtTime(note.freq, t0);
      if (note.slide) osc.frequency.exponentialRampToValueAtTime(note.slide, t1);
      env.gain.setValueAtTime(0, t0);
      env.gain.linearRampToValueAtTime(note.gain ?? 1, t0 + .012);
      env.gain.exponentialRampToValueAtTime(.0001, t1);
      osc.connect(env).connect(master);
      osc.start(t0); osc.stop(t1 + .02);
      end = Math.max(end, t1);
    }
    setTimeout(() => master.disconnect(), (end - ctx.currentTime + .2) * 1000);
  } catch { /* Audio unavailable: stay silent. */ }
}
