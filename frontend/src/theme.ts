export const palettes = [
  { id: 'tux', name: 'Tux', accent: '#dfb74c', background: '#191919', surface: '#242424', sidebar: '#111111' },
  { id: 'ubuntu', name: 'Ubuntu', accent: '#e97846', background: '#211923', surface: '#302433', sidebar: '#171119' },
  { id: 'terminal', name: 'Terminal', accent: '#71cc80', background: '#101510', surface: '#1b241b', sidebar: '#090e09' },
  { id: 'debian', name: 'Debian', accent: '#e96a89', background: '#1c181b', surface: '#2b2227', sidebar: '#120e11' },
  { id: 'mint', name: 'Mint', accent: '#9ac779', background: '#171e1a', surface: '#242e27', sidebar: '#101712' },
  { id: 'fedora', name: 'Fedora', accent: '#75a8ef', background: '#151b26', surface: '#212c3b', sidebar: '#0f1520' },
  { id: 'arch', name: 'Arch', accent: '#48b6de', background: '#121b21', surface: '#1d2b34', sidebar: '#0c1319' },
  { id: 'kali', name: 'Kali', accent: '#779bff', background: '#111623', surface: '#1c263a', sidebar: '#0b101b' },
  { id: 'opensuse', name: 'openSUSE', accent: '#78c27a', background: '#16201b', surface: '#25332b', sidebar: '#0e1712' },
  { id: 'pop', name: 'Pop!_OS', accent: '#67c5cd', background: '#182022', surface: '#283235', sidebar: '#101719' },
  { id: 'manjaro', name: 'Manjaro', accent: '#56c4a3', background: '#151e1c', surface: '#22312c', sidebar: '#0e1613' },
] as const;
export type Preferences = { palette: typeof palettes[number]['id']; accent: string | null; model: string };
export const defaults: Preferences = { palette: 'tux', accent: null, model: 'gemma3:12b-it-qat' };
export function applyTheme(preferences: Preferences) {
  const palette = palettes.find(p => p.id === preferences.palette) || palettes[0];
  const root = document.documentElement;
  const accent = preferences.accent || palette.accent;
  root.dataset.palette = palette.id;
  root.style.setProperty('--accent', accent);
  root.style.setProperty('--surface-0', palette.background);
  root.style.setProperty('--surface-1', palette.surface);
  root.style.setProperty('--surface-2', palette.sidebar);
  const rgb = accent.slice(1).match(/.{2}/g)!.map(n => parseInt(n, 16));
  root.style.setProperty('--on-accent', rgb[0] * .299 + rgb[1] * .587 + rgb[2] * .114 > 145 ? '#17170f' : '#ffffff');
}
