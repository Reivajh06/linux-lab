import { useEffect, useRef, useState, type RefObject } from 'react';
import RFB from '@novnc/novnc';
import { AppWindow, ClipboardPaste, Expand, FilePenLine, Globe, Loader2, Plus, RefreshCw, Shrink, Terminal, X } from 'lucide-react';
import Modal from './Modal';
import { api, desktopURL, post } from './api';
import { attachDeadKeys, keysym } from './deadkeys';

type AppKind = 'terminal' | 'editor' | 'browser' | 'app';
type WindowTab = { id: string; title: string; kind: AppKind; class_name: string };
type WindowState = { windows: WindowTab[]; active_id: string | null };
const icons = { terminal: Terminal, editor: FilePenLine, browser: Globe, app: AppWindow };
const launchNames: Record<AppKind, string> = { terminal: 'The terminal', editor: 'gedit', browser: 'Firefox', app: 'The application' };
const launchCommands: Record<AppKind, string> = { terminal: 'lab-terminal &', editor: 'gedit &', browser: 'firefox &', app: 'it' };

export default function Desktop({ id, running, fullscreenTarget, fullscreen, onFullscreen }: { id: string; running: boolean; fullscreenTarget: RefObject<HTMLDivElement | null>; fullscreen: boolean; onFullscreen: (on: boolean) => void }) {
  const screen = useRef<HTMLDivElement>(null);
  const connection = useRef<RFB | null>(null);
  const refresh = useRef<() => Promise<void>>(async () => {});
  const tabs = useRef(new Map<string, HTMLButtonElement>());
  const [epoch, setEpoch] = useState(0);
  const [status, setStatus] = useState('Disconnected');
  const [prepared, setPrepared] = useState(false);
  const [windows, setWindows] = useState<WindowTab[]>([]);
  const [active, setActive] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [paste, setPaste] = useState<string | null>(null);
  // A launch is only a request; the app counts as open once a new window of its kind appears.
  const [pending, setPending] = useState<{ kind: AppKind; before: number } | null>(null);

  useEffect(() => {
    if (pending && windows.filter(w => w.kind === pending.kind).length > pending.before) setPending(null);
  }, [windows, pending]);
  useEffect(() => {
    if (!pending) return;
    const name = launchNames[pending.kind];
    const timer = setTimeout(() => {
      setPending(null);
      setError(`${name} did not open. It may have failed inside the Linux environment. Try again, or run ${launchCommands[pending.kind]} in the terminal to see its error output.`);
    }, pending.kind === 'browser' ? 45000 : 20000);
    return () => clearTimeout(timer);
  }, [pending]);

  useEffect(() => {
    // Full screen is an app layout (tabs, Linux display, side panel) that works even where the
    // browser refuses real full screen; real full screen is layered on top when it is allowed.
    document.body.classList.toggle('workspace-focus', fullscreen);
    const left = () => { if (!document.fullscreenElement) onFullscreen(false); };
    document.addEventListener('fullscreenchange', left);
    return () => { document.removeEventListener('fullscreenchange', left); document.body.classList.remove('workspace-focus'); };
  }, [fullscreen, onFullscreen]);

  useEffect(() => {
    setPending(null);
    if (!screen.current || !running) { setPrepared(false); setWindows([]); setActive(null); return; }
    let disposed = false;
    let rfb: RFB | null = null;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let detachDeadKeys: (() => void) | undefined;
    setPrepared(false); setError(''); setStatus('Preparing');
    const accept = (state: WindowState) => {
      if (!disposed) { setWindows(state.windows); setActive(state.active_id); }
    };
    refresh.current = async () => {
      const state = await api<WindowState>(`/environments/${id}/workspace/windows`);
      accept(state);
    };
    const poll = async () => {
      try { if (!document.hidden) await refresh.current(); }
      catch { /* Keep app tabs visible while the display reconnects. */ }
      if (!disposed) timer = setTimeout(poll, 1200);
    };
    (async () => {
      try {
        const state = await post<WindowState>(`/environments/${id}/workspace/prepare`);
        if (disposed || !screen.current) return;
        accept(state); setPrepared(true); setStatus('Connecting');
        rfb = new RFB(screen.current, desktopURL(id));
        // Resize the Fedora session at native size; noVNC observes layout/fullscreen changes.
        rfb.scaleViewport = false; rfb.resizeSession = true;
        // noVNC defaults to JPEG quality 6, which smears terminal text; the lab is local, so favour fidelity.
        rfb.qualityLevel = 9; rfb.compressionLevel = 1;
        connection.current = rfb;
        // An empty code makes noVNC send the keysym rather than a US-layout scancode.
        detachDeadKeys = attachDeadKeys(screen.current, text => { for (const char of text) rfb?.sendKey(keysym(char), ''); });
        rfb.addEventListener('connect', () => { if (!disposed) { setStatus('Connected'); rfb?.focus(); } });
        rfb.addEventListener('disconnect', () => { if (!disposed) setStatus('Disconnected'); });
        rfb.addEventListener('securityfailure', () => { if (!disposed) setStatus('Connection rejected'); });
        timer = setTimeout(poll, 700);
      } catch (e) {
        if (!disposed) { setStatus('Unavailable'); setError(e instanceof Error ? e.message : String(e)); }
      }
    })();
    return () => { disposed = true; if (timer) clearTimeout(timer); detachDeadKeys?.(); rfb?.disconnect(); connection.current = null; };
  }, [id, running, epoch]);

  const operate = async (action: string, body: object, focusDisplay = true) => {
    setBusy(true); setError('');
    try { await post(`/environments/${id}/workspace/${action}`, body); await refresh.current(); if (focusDisplay) connection.current?.focus(); return true; }
    catch (e) { setError(e instanceof Error ? e.message : String(e)); return false; }
    finally { setBusy(false); }
  };
  // Arrow keys keep focus on the tab strip; a click hands the keyboard to the Linux display.
  const select = (window: WindowTab, fromKeyboard = false) => { setActive(window.id); if (fromKeyboard) tabs.current.get(window.id)?.focus(); operate('activate', { window: window.id }, !fromKeyboard); };
  const launch = (app: 'terminal' | 'editor' | 'browser') => {
    setPending({ kind: app, before: windows.filter(w => w.kind === app).length });
    operate('launch', { app }).then(ok => { if (!ok) setPending(null); });
  };
  const toggleFullscreen = () => {
    const entering = !fullscreen;
    onFullscreen(entering);
    if (entering) fullscreenTarget.current?.requestFullscreen?.().catch(() => {});
    else if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
  };
  const terminalCount = windows.filter(w => w.kind === 'terminal').length;
  const current = windows.find(w => w.id === active);

  return <div className="desktop-frame tabbed-desktop">
    <div className="environment-tabbar">
      <div className="environment-tabs" role="tablist" aria-label="Linux applications">
        {!windows.length && <span className="environment-tab-placeholder"><Terminal size={16}/>Terminal</span>}
        {windows.map((window, index) => {
          const Icon = icons[window.kind];
          const label = window.kind === 'terminal' ? (terminalCount > 1 ? `Terminal ${windows.filter(w => w.kind === 'terminal').indexOf(window) + 1}` : 'Terminal') : window.title;
          const pinned = window.kind === 'terminal' && index === 0;
          return <div className={'environment-tab-item ' + (active === window.id ? 'selected' : '')} key={window.id}>
            <button role="tab" ref={node => { if (node) tabs.current.set(window.id, node); else tabs.current.delete(window.id); }} aria-selected={active === window.id} aria-controls="linux-app-display" tabIndex={active === window.id || (!active && index === 0) ? 0 : -1} title={window.title} onClick={() => select(window)} onKeyDown={event => {
              let next = index;
              if (event.key === 'ArrowRight') next = (index + 1) % windows.length;
              else if (event.key === 'ArrowLeft') next = (index + windows.length - 1) % windows.length;
              else if (event.key === 'Home') next = 0;
              else if (event.key === 'End') next = windows.length - 1;
              else return;
              event.preventDefault(); select(windows[next], true);
            }}><Icon size={15}/><span>{label}</span></button>
            {!pinned && <button className="close-application" aria-label={`Close ${label}`} title="Close application" disabled={busy} onClick={() => operate('close', { window: window.id })}><X size={14}/></button>}
          </div>;
        })}
        {pending && <span className="environment-tab-placeholder launching" role="status"><Loader2 size={15} className="spin"/>Opening {pending.kind === 'terminal' ? 'terminal' : launchNames[pending.kind]}…</span>}
      </div>
      <div className="environment-launchers">
        <button title="New terminal" aria-label="New terminal" disabled={!prepared || busy} onClick={() => launch('terminal')}><Plus size={17}/></button>
        <button title="Open gedit" aria-label="Open gedit" disabled={!prepared || busy} onClick={() => launch('editor')}><FilePenLine size={16}/></button>
        <button title="Open Firefox" aria-label="Open Firefox" disabled={!prepared || busy} onClick={() => launch('browser')}><Globe size={16}/></button>
      </div>
      <div className="environment-view-tools">
        <span className={'display-status ' + (status === 'Connected' ? 'connected' : '')} role="status" title={running ? status : 'Stopped'}><span className="dot"/><span>{running ? status : 'Stopped'}</span></span>
        <button title="Paste text" aria-label="Paste text" disabled={!prepared} onClick={() => setPaste('')}><ClipboardPaste size={16}/></button>
        <button title="Reconnect workspace" aria-label="Reconnect workspace" disabled={!running} onClick={() => setEpoch(e => e + 1)}><RefreshCw size={16}/></button>
        <button title={fullscreen ? 'Exit full screen' : 'Full screen'} aria-label={fullscreen ? 'Exit full screen' : 'Full screen'} onClick={toggleFullscreen}>{fullscreen ? <Shrink size={17}/> : <Expand size={17}/>}</button>
      </div>
    </div>
    <div className="environment-display" id="linux-app-display" role="tabpanel" aria-label={current?.title || 'Linux terminal'}>
      <div className="desktop-screen" ref={screen} style={{ visibility: running && prepared ? 'visible' : 'hidden' }}/>
      {!id && <div className="workspace-overlay"><Loader2 size={26} className="spin"/><h2>Opening environment</h2><p>Loading the environment details.</p></div>}
      {id && !running && <div className="workspace-overlay"><Terminal size={32}/><h2>Environment stopped</h2><p>Start the environment to open the terminal.</p></div>}
      {running && !prepared && <div className="workspace-overlay">{status === 'Unavailable' ? <AppWindow size={30}/> : <Loader2 size={26} className="spin"/>}<h2>{status === 'Unavailable' ? 'Workspace unavailable' : 'Preparing workspace'}</h2><p>{status === 'Unavailable' ? 'Reconnect to retry. Your Linux files are preserved.' : 'Installing desktop tools on older environments may take a moment.'}</p></div>}
      {running && prepared && !windows.length && status === 'Connected' && <div className="workspace-overlay"><Terminal size={30}/><h2>No applications open</h2><button className="button" disabled={busy} onClick={() => launch('terminal')}><Plus size={15}/>Open terminal</button></div>}
    </div>
    {running && prepared && status !== 'Connected' && <div className={'workspace-notice ' + (status === 'Connecting' ? '' : 'disconnected')}>{status === 'Connecting' ? <Loader2 size={14} className="spin"/> : <span className="dot"/>}{status === 'Connecting' ? 'Connecting…' : 'Disconnected. Reconnect to resume your workspace.'}</div>}
    {error && <div role="alert" className="workspace-error"><p>{error}</p><button aria-label="Dismiss workspace error" onClick={() => setError('')}><X size={15}/></button></div>}
    {paste !== null && <Modal title="Linux clipboard" className="small" onClose={() => setPaste(null)} description="Paste text here, send it to Linux, then use Ctrl+Shift+V in the terminal."><label className="field-label" htmlFor="linux-clipboard">Text to send</label><textarea id="linux-clipboard" autoFocus value={paste} onChange={e => setPaste(e.target.value)} rows={5}/><div className="modal-actions"><button className="button secondary" onClick={() => setPaste(null)}>Cancel</button><button className="button" disabled={!paste} onClick={() => { connection.current?.clipboardPasteFrom(paste); connection.current?.focus(); setPaste(null); }}>Send to clipboard</button></div></Modal>}
  </div>;
}
