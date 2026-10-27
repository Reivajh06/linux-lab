import React, { useCallback, useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import Markdown from 'react-markdown';
import { ArrowDownToLine, ArrowLeft, ArrowRight, BookOpen, Check, CheckCircle2, ChevronDown, ChevronRight, CircleAlert, FileText, FolderOpen, GraduationCap, HardDrive, Layers3, Library, Loader2, Plus, Search, Send, Sparkles, Square, Terminal, Trash2, Upload, X, RefreshCw, Cpu, ExternalLink, Palette, Play } from 'lucide-react';
import Desktop from './Desktop';
import Environments from './Environments';
import ExerciseBody from './ExerciseBody';
import Modal from './Modal';
import ChatMessage from './ChatMessage';
import EnvironmentAssistant from './EnvironmentAssistant';
import { applyTheme, defaults, palettes } from './theme';
import type { Preferences } from './theme';
import { api, configure, download, post, progressPercent, selectLocalModel } from './api';
import type { Chat, Config, CourseDetail, CourseSummary, Environment, Result, Source } from './api';
import './styles.css';

type Page = 'environments' | 'library' | 'practice' | 'sources' | 'chat';
const nav = [
  { id: 'environments', label: 'Environments', icon: HardDrive },
  { id: 'practice', label: 'Free Practice', icon: Terminal },
  { id: 'library', label: 'Exercise Library', icon: Library },
  { id: 'sources', label: 'Sources', icon: FileText },
  { id: 'chat', label: 'Exercise Chat', icon: Sparkles },
] as const;

function App() {
  const [page, setPage] = useState<Page>('environments');
  const [config, setConfig] = useState<Config | null>(null);
  const [courses, setCourses] = useState<CourseSummary[]>([]);
  const [coursesLoaded, setCoursesLoaded] = useState(false);
  const [sources, setSources] = useState<Source[]>([]);
  const [environmentId, setEnvironmentId] = useState<string | null>(null);
  const [preferences, setPreferences] = useState<Preferences>(defaults);
  const [courseKey, setCourseKey] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [modal, setModal] = useState<'import' | 'format' | 'setup' | 'appearance' | null>(null);
  const [importText, setImportText] = useState('');
  const [format, setFormat] = useState('');
  const [busy, setBusy] = useState(false);
  const [build, setBuild] = useState({ state: 'idle', log: '' });
  const [search, setSearch] = useState('');
  const [chatDirty, setChatDirty] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);
  const fail = useCallback((e: unknown) => setError(e instanceof Error ? e.message : String(e)), []);
  const refreshCourses = useCallback(async () => { setCourses(await api<CourseSummary[]>('/courses')); setCoursesLoaded(true); }, []);
  const refreshSources = useCallback(async () => setSources(await api<Source[]>('/sources')), []);
  const refreshConfig = useCallback(async () => setConfig(await configure()), []);
  useEffect(() => { (async () => { await refreshConfig(); await Promise.all([refreshCourses(), refreshSources(), api<Preferences>('/preferences').then(setPreferences)]); })().catch(fail); }, [refreshConfig, refreshCourses, refreshSources, fail]);
  useEffect(() => {
    if (!sources.some(s => s.state === 'indexing')) return;
    const timer = setInterval(() => refreshSources().catch(fail), 2000); return () => clearInterval(timer);
  }, [sources, refreshSources, fail]);
  useEffect(() => {
    if (modal !== 'setup') return;
    const poll = () => api<typeof build>('/runtime/build').then(setBuild).catch(fail);
    poll(); const timer = setInterval(poll, 1500); return () => clearInterval(timer);
  }, [modal, fail]);
  useEffect(() => applyTheme(preferences), [preferences]);
  const saveAppearance = async (patch: Partial<Preferences>) => {
    setPreferences(p => ({ ...p, ...patch }));
    try { await api('/preferences', { method: 'PATCH', body: JSON.stringify(patch) }); } catch (e) { fail(e); }
  };
  const navigate = (next: Page) => {
    if (page === 'chat' && next !== 'chat' && chatDirty && !window.confirm('Leave Exercise Chat and discard unsaved draft edits?')) return;
    setPage(next); setCourseKey(null); setEnvironmentId(null); setError('');
  };
  const importCourse = async (text: string) => {
    setBusy(true); setError('');
    try { const imported = await post<{ key: string }>('/courses/import', { yaml: text }); await refreshCourses(); setModal(null); setImportText(''); setPage('library'); setCourseKey(imported.key); }
    catch (e) { fail(e); } finally { setBusy(false); }
  };
  const showFormat = async () => { try { setFormat(await (await fetch('/api/docs/exercise-format')).text()); setModal('format'); } catch (e) { fail(e); } };
  const closeModal = () => { setModal(null); setError(''); };
  const totalExercises = courses.reduce((n, c) => n + c.exercise_count, 0);
  const completed = courses.reduce((n, c) => n + c.completed, 0);
  const visibleCourses = courses.filter(c => (c.title + ' ' + c.description).toLowerCase().includes(search.trim().toLowerCase()));
  const currentAccent = preferences.accent || palettes.find(p => p.id === preferences.palette)!.accent;
  const openCourse = courseKey ? courses.find(c => c.key === courseKey) : undefined;

  return <div className="app-shell">
    <aside className="sidebar">
      <button aria-label="Linux Lab home" className="brand" onClick={() => navigate('library')}><span className="brand-mark" aria-hidden="true">&gt;_</span><span>linux<span className="brand-light">lab</span><span className="brand-dot">.</span></span></button>
      <div className="sidebar-caption">Your workspace</div>
      <nav aria-label="Main">{nav.map(item => <button key={item.id} aria-label={item.label} title={item.label} aria-current={page === item.id ? 'page' : undefined} className={'nav-item ' + (page === item.id ? 'active' : '')} onClick={() => navigate(item.id)}><item.icon size={19}/><span>{item.label}</span>{item.id === 'chat' && <span className="local-badge">LOCAL</span>}</button>)}</nav>
      <div className="sidebar-bottom">
        <button title="Environment setup" onClick={() => setModal('setup')}><span className={'dot ' + (config?.docker.image_ready ? '' : 'warn')}/><span>{config?.docker.image_ready ? 'Lab image ready' : 'Set up environment'}</span><ChevronRight size={14}/></button>
      </div>
    </aside>
    <div className="main-shell">
      <header className="topbar">
        <div className="breadcrumb">Workspace <ChevronRight size={13}/> <strong>{nav.find(n => n.id === page)?.label}</strong>{openCourse && <><ChevronRight size={13}/><span>{openCourse.title}</span></>}</div>
        <div className="topbar-right">
          <button className="icon-button" title="Appearance" aria-label="Appearance" onClick={() => setModal('appearance')}><Palette size={18}/></button>
          <button className={'status-pill ' + (config?.docker.available ? 'ready' : '')} title={config?.docker.message || 'Docker status'} aria-label={config?.docker.available ? 'Docker connected. Open environment setup' : 'Docker setup needed. Open environment setup'} onClick={() => setModal('setup')}><span className="dot"/><span>{config ? config.docker.available ? 'Docker connected' : 'Docker setup needed' : 'Checking Docker…'}</span></button>
        </div>
      </header>
      {error && modal !== 'import' && modal !== 'setup' && <div role="alert" className="error-banner"><CircleAlert size={18}/><pre>{error}</pre><button aria-label="Dismiss error" onClick={() => setError('')}><X size={17}/></button></div>}
      <main>
        {page === 'environments' && !environmentId && <Environments courses={courses} onError={fail} onChanged={refreshCourses} onOpen={environment => { setEnvironmentId(environment.id); setCourseKey(environment.course_key); }}/>}
        {page === 'library' && !courseKey && <div className="page library-page">
          <div className="page-heading">
            <div><h1>Exercise Library</h1><p>Import a collection or open its Linux environment.</p></div>
            <button className="button" onClick={() => navigate('chat')}><Sparkles size={17}/>Generate exercises</button>
          </div>
          <div className="stats-grid">
            <Stat icon={Layers3} value={courses.length} label="Exercise collections" foot="Your growing learning library"/>
            <Stat icon={GraduationCap} value={totalExercises} label="Guided exercises" foot="Real tasks. Real Linux skills."/>
            <Stat icon={CheckCircle2} value={completed} label="Exercises completed" foot={completed ? 'Keep your momentum going' : 'Your next step starts here'}/>
          </div>
          <div className="section-heading"><h2>Your exercise library <span className="count-badge">{courses.length}</span></h2><button className="button secondary" onClick={() => setModal('import')}><Upload size={16}/>Import YAML</button></div>
          <div className="library-controls">
            <label className="search-input"><Search size={17}/><input aria-label="Search collections" placeholder="Find your next exercise…" value={search} onChange={e => setSearch(e.target.value)}/>{search && <button className="icon-button" aria-label="Clear search" onClick={() => setSearch('')}><X size={14}/></button>}</label>
            <button className="text-button" onClick={showFormat}><BookOpen size={16}/>Exercise format guide</button>
          </div>
          <div className="course-grid">
            {!coursesLoaded && <div className="loading-state" role="status"><Loader2 className="spin" size={18}/>Loading collections…</div>}
            {coursesLoaded && search.trim() && !visibleCourses.length && <div className="empty-state"><Search size={28}/><h3>No collections match “{search.trim()}”</h3><p>Try a different word, or clear the search to see your whole library.</p><button className="button secondary" onClick={() => setSearch('')}>Clear search</button></div>}
            {visibleCourses.map(c => <button className="course-card" key={c.key} onClick={() => setCourseKey(c.key)}>
              <div className="course-card-top"><span className="collection-icon"><Terminal size={22}/></span><span className="tag">{c.id === 'linux-foundations' ? 'FOUNDATIONS' : 'YOUR COLLECTION'}</span></div>
              <h3>{c.title}</h3>
              <p className="course-description">{c.description}</p>
              <div className="course-meta"><span><Layers3 size={14}/>{c.exercise_count} exercises</span><span><GraduationCap size={15}/>{c.points} points</span></div>
              <div className="course-progress"><div className="progress-track" role="progressbar" aria-label={`${c.title} progress`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={progressPercent(c.earned, c.points)}><span style={{ width: `${progressPercent(c.earned, c.points)}%` }}/></div><span>{c.completed}/{c.exercise_count} complete</span></div>
              <div className="course-card-bottom"><span>{c.environment?.state === 'running' ? <><span className="dot"/>Environment running</> : <>v{c.version} · Saved locally</>}</span><span className="course-link">{c.environment ? 'Open course' : 'Start learning'}<ArrowRight size={15}/></span></div>
            </button>)}
            {!search.trim() && <button className="create-card" onClick={() => navigate('chat')}><span className="create-icon"><Sparkles size={25}/></span><h3>Generate exercises</h3><p>Create a YAML collection using a local model and selected sources.</p><span>Open Exercise Chat <ArrowRight size={15}/></span><div className="mini-tag"><Cpu size={12}/> LOCAL OLLAMA</div></button>}
          </div>
        </div>}
        {(page === 'practice' || (page === 'library' && courseKey) || (page === 'environments' && environmentId)) && <Workspace environmentId={page === 'environments' ? environmentId : null} courseKey={page === 'practice' ? null : courseKey} onBack={() => { setCourseKey(null); setEnvironmentId(null); }} onError={fail} onChanged={refreshCourses} onSetup={() => setModal('setup')}/>}
        {page === 'sources' && <Sources sources={sources} refresh={refreshSources} onError={fail} onChat={() => navigate('chat')}/>}
        {page === 'chat' && <ExerciseChat sources={sources} onError={fail} onImport={importCourse} onDirtyChange={setChatDirty}/>}
      </main>
    </div>
    {modal === 'import' && <Modal title="Import an exercise collection" onClose={closeModal} description="Choose a YAML file or paste its contents. Setup scripts run inside the lab when you start the course; import files you trust.">
      <input hidden ref={fileInput} type="file" accept=".yaml,.yml" onChange={async e => { const file = e.target.files?.[0]; if (file) setImportText(await file.text()); }}/>
      <button className="button secondary" onClick={() => fileInput.current?.click()}><FolderOpen size={16}/>Choose YAML file</button>
      <label className="field-label" htmlFor="import-yaml">Collection YAML</label>
      <textarea id="import-yaml" className="yaml-editor" value={importText} onChange={e => setImportText(e.target.value)} spellCheck={false} rows={14} placeholder={'schema_version: 1\nid: my-first-course\nversion: "1.0"\n…'}/>
      {error && <pre role="alert" className="inline-error">{error}</pre>}
      <div className="modal-actions"><button className="text-button" onClick={showFormat}><BookOpen size={15}/>Read the format guide</button><button className="button" disabled={busy || !importText.trim()} onClick={() => importCourse(importText)}>{busy ? <Loader2 className="spin" size={16}/> : <Plus size={16}/>}Import collection</button></div>
    </Modal>}
    {modal === 'appearance' && <Modal title="Appearance" onClose={closeModal} description="Select a dark palette or choose a custom accent color.">
      <div className="palette-grid" role="group" aria-label="Palettes">{palettes.map(palette => <button className={'palette-option ' + (preferences.palette === palette.id ? 'selected' : '')} aria-pressed={preferences.palette === palette.id} key={palette.id} onClick={() => saveAppearance({ palette: palette.id, accent: null })}><span className="palette-preview" aria-hidden="true" style={{ background: palette.background }}><span style={{ background: palette.sidebar }}/><i style={{ background: palette.surface }}/><b style={{ background: palette.accent }}/></span><strong>{palette.name}</strong>{preferences.palette === palette.id && <Check size={15}/>}</button>)}</div>
      <label className="accent-picker">Accent color<input type="color" value={currentAccent} onChange={e => setPreferences(p => ({ ...p, accent: e.target.value }))} onBlur={e => saveAppearance({ accent: e.target.value })}/><code>{currentAccent}</code></label>
      <div className="modal-actions"><button className="button secondary" onClick={() => saveAppearance({ palette: 'tux', accent: null })}>Reset appearance</button><button className="button" onClick={() => { if (preferences.accent) saveAppearance({ accent: preferences.accent }); closeModal(); }}>Done</button></div>
    </Modal>}
    {modal === 'format' && <Modal title="Exercise format guide" className="wide" onClose={closeModal}><article className="markdown docs"><Markdown>{format}</Markdown></article></Modal>}
    {modal === 'setup' && <Modal title="Environment setup" onClose={closeModal}>
      <div className="setup-status"><HardDrive size={24}/><div><strong>{config?.docker.available ? 'Docker is connected' : 'Docker Desktop is required'}</strong><p>{config?.docker.message || 'Checking connection…'}</p></div></div>
      <ol className="setup-steps">
        <li>Install and start <a href="https://docs.docker.com/desktop/setup/install/windows-install/" target="_blank" rel="noreferrer">Docker Desktop for Windows</a> with the WSL 2 Linux container backend.</li>
        <li>{config?.desktop ? 'Build the Linux lab image using the button below. The first build downloads Fedora 44, editors, manuals, and OCR tools.' : <>Run <code>docker compose build lab-image</code> on the host to build the Linux image.</>}</li>
        <li>Start a course or Free Practice. Your environment opens inside this app.</li>
      </ol>
      <div className="notice">Local Ollama: <code>{config?.ollama_url}</code><br/>Practice works without a model. PDF scans need the lab image or local OCR tools.</div>
      {build.log && <pre className="build-log">{build.log}</pre>}
      {error && <pre role="alert" className="inline-error">{error}</pre>}
      <div className="modal-actions"><button className="button secondary" disabled={busy} onClick={() => { setBusy(true); refreshConfig().catch(fail).finally(() => setBusy(false)); }}>{busy ? <Loader2 className="spin" size={15}/> : <RefreshCw size={15}/>}Check again</button>{config?.desktop && <button className="button" disabled={build.state === 'running'} onClick={async () => { try { setBuild(await post('/runtime/build')); } catch (e) { fail(e); } }}>{build.state === 'running' ? <Loader2 size={16} className="spin"/> : <Layers3 size={16}/>}{build.state === 'running' ? 'Building image…' : 'Build lab image'}</button>}</div>
    </Modal>}
  </div>;
}

function Stat({ icon: Icon, value, label, foot }: { icon: typeof Layers3; value: number; label: string; foot: string }) {
  return <div className="stat"><span className="stat-icon"><Icon size={20}/></span><div><span className="stat-value">{value}</span><strong>{label}</strong><p>{foot}</p></div></div>;
}

function Workspace({ courseKey, environmentId, onBack, onError, onChanged, onSetup }: { courseKey: string | null; environmentId: string | null; onBack: () => void; onError: (e: unknown) => void; onChanged: () => Promise<void>; onSetup: () => void }) {
  const [detail, setDetail] = useState<CourseDetail | null>(null);
  const [environment, setEnvironment] = useState<Environment | null>(null);
  const [selected, setSelected] = useState(0);
  const [busy, setBusy] = useState('');
  const [reset, setReset] = useState(false);
  const [desktopKey, setDesktopKey] = useState(0);
  const [panel, setPanel] = useState<'exercise' | 'assistant'>('exercise');
  const exercise = detail?.course.exercises[selected];
  const result = exercise ? detail?.results[exercise.id] : undefined;
  const load = useCallback(async () => {
    if (environmentId) { const data = await api<CourseDetail>(`/environments/${environmentId}/workspace`); setDetail(data.course ? data : null); setEnvironment(data.environment); }
    else if (courseKey) { const data = await api<CourseDetail>(`/courses/${courseKey}`); setDetail(data); setEnvironment(data.environment); }
    else { setDetail(null); setEnvironment(await post<Environment>('/environments', {})); }
  }, [courseKey, environmentId]);
  useEffect(() => { setSelected(0); setEnvironment(null); setDetail(null); setPanel('exercise'); load().catch(onError); }, [load, onError]);
  const lifecycle = async (action: string) => {
    if (!environment) return; setBusy(action);
    try { setEnvironment(await post<Environment>(`/environments/${environment.id}/${action}`)); setDesktopKey(n => n + 1); if (action === 'recreate') await load(); await onChanged(); }
    catch (e) { onError(e); await load().catch(onError); } finally { setBusy(''); setReset(false); }
  };
  const grade = async (all: boolean) => {
    if (!environment || !detail) return; setBusy(all ? 'evaluate-all' : 'evaluate');
    try { const response = await post<{ results: Result[] }>(`/environments/${environment.id}/evaluate`, { exercise_id: all ? null : exercise?.id }); setDetail(d => d ? { ...d, results: { ...d.results, ...Object.fromEntries(response.results.map(r => [r.exercise_id, r])) } } : null); await onChanged(); }
    catch (e) { onError(e); } finally { setBusy(''); }
  };
  const earned = detail ? Object.values(detail.results).reduce((n, r) => n + r.earned, 0) : 0;
  const points = detail?.course.exercises.reduce((n, e) => n + e.evaluations.reduce((m, t) => m + t.points, 0), 0) || 0;
  const running = environment?.state === 'running';
  const changing = !!busy && !busy.startsWith('evaluate');
  return <div className="page workspace-page">
    {(courseKey || environmentId) && <button className="text-button back-button" onClick={onBack}><ArrowLeft size={15}/>{environmentId ? 'Back to environments' : 'Back to library'}</button>}
    <div className="section-heading workspace-heading">
      <div><h1>{environmentId ? environment?.name || 'Opening environment…' : detail?.course.title || (courseKey ? 'Opening course…' : 'Free Practice')}</h1><p>{courseKey ? `${detail?.course.exercises.length || 0} exercises · ${earned}/${points} points · One shared Linux environment` : 'Independent Linux environment with sudo access.'}</p></div>
      <div className="button-row">
        {detail && courseKey && <a className="icon-button" title="Export YAML" aria-label="Export collection as YAML" href={`/api/courses/${courseKey}/export`}><ArrowDownToLine size={18}/></a>}
        <button className="button secondary" disabled={!environment || !!busy} onClick={() => setReset(true)}><RefreshCw size={15}/>Recreate</button>
        <button className="button" disabled={!environment || !!busy} onClick={() => lifecycle(running ? 'stop' : 'start')}>{changing ? <Loader2 size={16} className="spin"/> : running ? <Square size={14}/> : <Play size={16}/>}{changing ? 'Please wait…' : running ? 'Stop environment' : 'Start environment'}</button>
      </div>
    </div>
    {environment?.error && <div className="notice error-note"><CircleAlert size={17}/><span>{environment.error}</span><button className="text-button" onClick={onSetup}>Environment setup</button></div>}
    <div className="workspace-grid">
      <aside className="exercise-panel" aria-label="Environment guidance">
        <div className="workspace-panel-tabs" role="tablist" aria-label="Environment guidance">
          {detail && <button id="exercise-tab" role="tab" aria-selected={panel === 'exercise'} aria-controls="exercise-content" onClick={() => setPanel('exercise')}>Exercise</button>}
          <button id="assistant-tab" role="tab" aria-selected={!detail || panel === 'assistant'} aria-controls="assistant-content" onClick={() => setPanel('assistant')}><Sparkles size={15}/>Assistant</button>
        </div>
        {detail && <div id="exercise-content" role="tabpanel" aria-labelledby="exercise-tab" hidden={panel !== 'exercise'}>
        <div className="exercise-selector"><label htmlFor="exercise-picker">Exercise {selected + 1} of {detail.course.exercises.length}</label><div className="select-wrap"><select id="exercise-picker" value={selected} onChange={e => setSelected(Number(e.target.value))}>{detail.course.exercises.map((e, i) => <option key={e.id} value={i}>{detail.results[e.id]?.earned === detail.results[e.id]?.available && detail.results[e.id] ? '✓ ' : ''}{String(i + 1).padStart(2, '0')} · {e.title}</option>)}</select><ChevronDown size={16}/></div></div>
        {exercise && <ExerciseBody exercise={exercise} index={selected} result={result} actions={<>
          <div className="evaluate-actions">
            <button className="button" disabled={!!busy || !running} title={running ? undefined : 'Start the environment to evaluate'} onClick={() => grade(false)}>{busy === 'evaluate' ? <Loader2 size={16} className="spin"/> : <Check size={16}/>}{busy === 'evaluate' ? 'Evaluating…' : 'Evaluate exercise'}</button>
            <button className="text-button" disabled={!!busy || !running} onClick={() => grade(true)}>{busy === 'evaluate-all' && <Loader2 size={14} className="spin"/>}{busy === 'evaluate-all' ? 'Evaluating course…' : 'Evaluate all exercises'}</button>
            {result && <span className="last-checked">Last checked {new Date(result.checked_at).toLocaleString()}</span>}
          </div>
          <div className="exercise-pagination"><button disabled={selected === 0} onClick={() => setSelected(n => n - 1)}><ArrowLeft size={16}/>Previous</button><button disabled={selected === detail.course.exercises.length - 1} onClick={() => setSelected(n => n + 1)}>Next<ArrowRight size={16}/></button></div>
        </>}/>}
        </div>}
        <div id="assistant-content" role="tabpanel" aria-labelledby="assistant-tab" hidden={!!detail && panel !== 'assistant'}>{environment && <EnvironmentAssistant key={environment.id} environmentId={environment.id} exerciseId={exercise?.id || null} active={!detail || panel === 'assistant'}/>}</div>
      </aside>
      <div className="workspace-desktop"><Desktop key={desktopKey} id={environment?.id || ''} running={running}/></div>
    </div>
    {reset && <Modal title="Start fresh?" className="small" onClose={busy ? undefined : () => setReset(false)} description="Recreating this environment permanently removes its files, users, installed packages, and current scores. The imported course stays in your library.">
      <div className="modal-actions"><button className="button secondary" autoFocus disabled={!!busy} onClick={() => setReset(false)}>Keep my environment</button><button className="button danger" disabled={!!busy} onClick={() => lifecycle('recreate')}>{busy ? <><Loader2 size={15} className="spin"/>Recreating…</> : 'Recreate environment'}</button></div>
    </Modal>}
  </div>;
}

const sourceKind = (filename: string) => (filename.split('.').pop() || '').replace(/^htm$/i, 'html').replace(/^markdown$/i, 'md').toUpperCase().slice(0, 4) || 'FILE';

function Sources({ sources, refresh, onError, onChat }: { sources: Source[]; refresh: () => Promise<void>; onError: (e: unknown) => void; onChat: () => void }) {
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [preview, setPreview] = useState<Source | null>(null);
  const input = useRef<HTMLInputElement>(null);
  const upload = async (files: FileList | null) => { if (!files) return; setBusy(true); try { for (const file of Array.from(files)) { const data = new FormData(); data.append('file', file); await api('/sources', { method: 'POST', body: data }); } await refresh(); } catch (e) { onError(e); await refresh(); } finally { setBusy(false); if (input.current) input.current.value = ''; } };
  const remove = async (source: Source) => { if (!window.confirm(`Remove “${source.title}” and its search index? Existing exercise citations will be marked unavailable.`)) return; try { await api(`/sources/${source.id}`, { method: 'DELETE' }); await refresh(); } catch (e) { onError(e); } };
  const retry = async (source: Source) => { try { await post(`/sources/${source.id}/retry`); await refresh(); } catch (e) { onError(e); } };
  return <div className="page sources-page">
    <div className="page-heading"><div><h1>Sources</h1><p>PDF, text, Markdown, and HTML practice sheets used to generate exercises.</p></div><button className="button" disabled={busy} onClick={() => input.current?.click()}>{busy ? <Loader2 className="spin" size={17}/> : <Plus size={17}/>}Add sources</button></div>
    <input hidden ref={input} type="file" accept="application/pdf,text/plain,text/markdown,text/html,.pdf,.txt,.md,.htm,.html" multiple onChange={e => upload(e.target.files)}/>
    <button className={'upload-zone ' + (dragging ? 'dragging' : '')} disabled={busy} onClick={() => input.current?.click()} onDragOver={e => { e.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={e => { e.preventDefault(); setDragging(false); upload(e.dataTransfer.files); }}>
      <span>{busy ? <Loader2 className="spin" size={26}/> : <Upload size={26}/>}</span><h3>{busy ? 'Uploading…' : dragging ? 'Drop to upload' : 'Upload sources'}</h3><p>Drop files here, or click to choose PDF, text, Markdown, or HTML files.</p><small>Up to 25 MB per file · PDFs: 500 pages with local OCR · Text and HTML: pages of about 3000 characters</small>
    </button>
    <div className="section-heading"><h2>Source library <span className="count-badge">{sources.length}</span></h2><button className="text-button" onClick={onChat}>Create exercises from these sources<ArrowRight size={15}/></button></div>
    <div className="source-list">
      {sources.length === 0 && <div className="empty-state"><BookOpen size={30}/><h3>No sources yet</h3><p>Add a PDF, text, Markdown, or HTML file to use it in Exercise Chat.</p></div>}
      {sources.map(source => <div className="source-card" key={source.id}>
        <span className="pdf-icon" aria-hidden="true"><FileText size={22}/><small>{sourceKind(source.filename)}</small></span>
        <div className="source-info">
          <button onClick={() => setPreview(source)}><h3>{source.title}</h3></button>
          <p>{source.pages || '—'} pages · {source.ocr_pages} OCR pages · {source.filename}</p>
          <div className={'source-state ' + source.state} role="status">{source.state === 'indexing' && <Loader2 size={13} className="spin"/>}{source.state === 'ready' && <CheckCircle2 size={13}/>}{['error', 'interrupted'].includes(source.state) && <CircleAlert size={13}/>}{source.state === 'ready' ? 'Ready for exercises' : source.state === 'indexing' ? `Indexing ${source.indexed_pages}/${source.pages || '?'} pages` : source.state[0].toUpperCase() + source.state.slice(1)}</div>
          {source.state === 'indexing' && <div className="progress-track"><span style={{ width: `${progressPercent(source.indexed_pages, source.pages)}%` }}/></div>}
          {source.error && <p className="inline-error">{source.error}</p>}
          {source.warnings.length > 0 && <details className="source-warnings"><summary>{source.warnings.length} extraction {source.warnings.length === 1 ? 'note' : 'notes'}</summary>{source.warnings.map((w, i) => <p key={i}>{w}</p>)}</details>}
        </div>
        <div className="source-actions">
          <button className="icon-button" title="Preview" aria-label={`Preview ${source.title}`} onClick={() => setPreview(source)}><ExternalLink size={17}/></button>
          {['error', 'interrupted'].includes(source.state) && <button className="icon-button" title="Retry indexing" aria-label={`Retry indexing ${source.title}`} onClick={() => retry(source)}><RefreshCw size={17}/></button>}
          <button className="icon-button delete-button" title="Remove" aria-label={`Remove ${source.title}`} onClick={() => remove(source)}><Trash2 size={17}/></button>
        </div>
      </div>)}
    </div>
    {preview && <Modal title={preview.title} className="pdf-modal" closeLabel="Close preview" onClose={() => setPreview(null)}><iframe title={preview.title} src={`/api/sources/${preview.id}/pdf`}/></Modal>}
  </div>;
}

function ExerciseChat({ sources, onError, onImport, onDirtyChange }: { sources: Source[]; onError: (e: unknown) => void; onImport: (text: string) => Promise<void>; onDirtyChange: (dirty: boolean) => void }) {
  const [chats, setChats] = useState<{ id: string; title: string; created_at: string; updated_at: string }[]>([]);
  const [chat, setChat] = useState<Chat | null>(null);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [deleteChat, setDeleteChat] = useState<{ id: string; title: string } | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [loadingChat, setLoadingChat] = useState(false);
  const [deleteError, setDeleteError] = useState('');
  const historyToggle = useRef<HTMLButtonElement>(null);
  const chatLoad = useRef(0);
  const [models, setModels] = useState<{ name: string; size?: number }[]>([]);
  const [model, setModel] = useState('gemma3:12b-it-qat');
  const [ollamaError, setOllamaError] = useState('');
  const [selectedSources, setSelectedSources] = useState<string[] | null>(null);
  const [prompt, setPrompt] = useState('');
  const [count, setCount] = useState(5);
  const [draft, setDraft] = useState('');
  const [draftDirty, setDraftDirty] = useState(false);
  const [busy, setBusy] = useState(false);
  const [validation, setValidation] = useState('');
  const messagesEnd = useRef<HTMLDivElement>(null);
  const running = ['queued', 'running'].includes(chat?.job?.state || '');
  const readySources = sources.filter(s => s.state === 'ready');
  const loadModels = useCallback(async () => {
    const response = await api<{ name: string }[] | { available: boolean; models: { name: string }[]; message?: string }>('/ollama/models');
    const saved = await api<Preferences>('/preferences');
    const local = Array.isArray(response) ? response : response.models;
    setModels(local); setOllamaError(!Array.isArray(response) && !response.available ? response.message || 'Local Ollama unavailable' : local.length ? '' : 'Ollama has no local models.');
    setModel(selectLocalModel(local, saved.model));
  }, []);
  const loadChat = useCallback(async (id: string, replaceDraft = true) => { const request = ++chatLoad.current; const result = await api<Chat>(`/chats/${id}`); if (request !== chatLoad.current) return; setChat(result); if (replaceDraft) { setDraft(result.draft); setDraftDirty(false); setValidation(''); } }, []);
  const refreshChats = useCallback(async () => setChats(await api<typeof chats>('/chats')), []);
  useEffect(() => { refreshChats().catch(onError); loadModels().catch(onError); return () => { chatLoad.current++; }; }, [refreshChats, loadModels, onError]);
  useEffect(() => {
    if (!running || !chat || deleting || loadingChat) return;
    const timer = setInterval(() => loadChat(chat.id).catch(onError), 1500); return () => clearInterval(timer);
  }, [running, chat?.id, deleting, loadingChat, loadChat, onError]);
  useEffect(() => { messagesEnd.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); }, [chat?.messages.length]);
  useEffect(() => { onDirtyChange(draftDirty); }, [draftDirty, onDirtyChange]);
  useEffect(() => () => onDirtyChange(false), [onDirtyChange]);
  const save = async () => { if (!chat) return; await api(`/chats/${chat.id}/draft`, { method: 'PUT', body: JSON.stringify({ yaml: draft }) }); setDraftDirty(false); };
  const submit = async () => {
    if (!prompt.trim() || !model || running || busy || loadingChat) return; setBusy(true); setValidation('');
    try {
      let id = chat?.id;
      if (!id) { id = (await post<{ id: string }>('/chats')).id; }
      if (draftDirty && chat) await save();
      await post(`/chats/${id}/generate`, { prompt, model, source_ids: selectedSources?.filter(id => sources.some(s => s.id === id && s.state === 'ready')) ?? null, count });
      setPrompt(''); await api('/preferences', { method: 'PATCH', body: JSON.stringify({ model }) }); await loadChat(id);
      await refreshChats();
    } catch (e) { onError(e); } finally { setBusy(false); }
  };
  const closeHistory = () => { setHistoryOpen(false); if (historyOpen) historyToggle.current?.focus(); };
  const resetChat = () => { chatLoad.current++; setChat(null); setDraft(''); setDraftDirty(false); setValidation(''); setPrompt(''); closeHistory(); };
  const newChat = () => { if (draftDirty && !window.confirm('Discard unsaved edits?')) return; resetChat(); };
  const changeChat = async (id: string) => { if (id === chat?.id) { closeHistory(); return; } if (draftDirty && !window.confirm('Discard unsaved draft edits?')) return; setLoadingChat(true); try { await loadChat(id); closeHistory(); } catch (e) { onError(e); } finally { setLoadingChat(false); } };
  const removeChat = async () => {
    if (!deleteChat) return; setDeleting(true); setDeleteError(''); chatLoad.current++;
    try {
      await api(`/chats/${deleteChat.id}`, { method: 'DELETE' });
      if (chat?.id === deleteChat.id) resetChat();
      setDeleteChat(null); await refreshChats().catch(onError);
    } catch (e) { setDeleteError(e instanceof Error ? e.message : String(e)); } finally { setDeleting(false); }
  };
  const prompts = ['Create beginner exercises about users, groups, and permissions.', 'Build a course on files and text processing from my notes.', 'How should I approach the local-hostname exercise?'];
  return <div className="page chat-page">
    <div className="section-heading"><div><h1>Exercise Chat</h1><p>Generate and revise exercise collections, or ask questions about your exercises.</p></div><button ref={historyToggle} className="button secondary history-toggle" aria-expanded={historyOpen} aria-controls="chat-history" onClick={() => setHistoryOpen(open => !open)}><Library size={16}/>History</button></div>
    <div className="chat-settings">
      <label><span>Local model</span><div className="select-wrap"><select value={model} onChange={e => { setModel(e.target.value); api('/preferences', { method: 'PATCH', body: JSON.stringify({ model: e.target.value }) }).catch(onError); }}>{models.length === 0 && <option value="">No local models found</option>}{models.map(m => <option key={m.name}>{m.name}</option>)}</select><ChevronDown size={15}/></div></label>
      <button className="icon-button" title="Refresh models" aria-label="Refresh local models" onClick={() => loadModels().catch(onError)}><RefreshCw size={17}/></button>
      <label className="count-select"><span>Exercises</span><input type="number" min={1} max={30} value={count} onChange={e => setCount(Math.max(1, Math.min(30, Number(e.target.value) || 1)))}/></label>
    </div>
    {ollamaError && <div className="notice error-note" role="alert"><CircleAlert size={17}/>{ollamaError}</div>}
    <div className="chat-grid">
      <aside id="chat-history" className={'chat-history ' + (historyOpen ? 'open' : '')} aria-label="Conversation history" onKeyDown={e => { if (e.key === 'Escape') closeHistory(); }}>
        <div className="history-header"><button className="button secondary" disabled={busy || deleting || loadingChat} onClick={newChat}><Plus size={16}/>New conversation</button><button className="icon-button history-close" aria-label="Close history" onClick={closeHistory}><X size={17}/></button></div>
        <div className="history-items">{chats.map(c => {
          const date = new Date(c.updated_at || c.created_at);
          return <div className={'history-item ' + (chat?.id === c.id ? 'active' : '')} key={c.id}>
            <button className="history-item-open" aria-current={chat?.id === c.id ? 'true' : undefined} disabled={busy || deleting || loadingChat} title={c.title} onClick={() => changeChat(c.id)}><span>{c.title}</span>{!Number.isNaN(date.getTime()) && <time dateTime={date.toISOString()}>{date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}</time>}</button>
            <button className="icon-button delete-button history-delete" aria-label={`Delete conversation: ${c.title}`} disabled={busy || deleting || loadingChat} onClick={() => { setDeleteError(''); setDeleteChat(c); }}><Trash2 size={15}/></button>
          </div>;
        })}{!chats.length && <p className="history-empty">Your saved conversations appear here.</p>}</div>
      </aside>
      <section className="chat-conversation" aria-label="Conversation">
        <div className="source-picker"><details><summary><FileText size={16}/>{selectedSources === null ? 'All indexed sources · relevant excerpts' : selectedSources.length ? `${selectedSources.length} ${selectedSources.length === 1 ? 'source' : 'sources'} selected` : 'No sources'}<ChevronDown size={14}/></summary><div className="source-options">
          <label><input type="checkbox" checked={selectedSources === null} onChange={e => setSelectedSources(e.target.checked ? null : [])}/>Use all indexed sources automatically</label>
          <p>Searches across the library and sends relevant excerpts within the model context budget.</p>
          {readySources.map(s => <label key={s.id}><input type="checkbox" checked={selectedSources === null || selectedSources.includes(s.id)} onChange={e => setSelectedSources(ids => { const chosen = ids ?? readySources.map(source => source.id); return e.target.checked ? [...chosen, s.id] : chosen.filter(id => id !== s.id); })}/>{s.title}<small>{s.pages} pages</small></label>)}
          {!readySources.length && <p>Add files in Sources to ground exercises in your materials.</p>}
        </div></details></div>
        <div className="messages" aria-live="polite">
          {!chat?.messages.length && <div className="chat-welcome"><span className="create-icon"><Sparkles size={27}/></span><h2>Describe exercises to generate, or ask about your exercises.</h2><div className="prompt-suggestions">{prompts.map(p => <button key={p} onClick={() => setPrompt(p)}>{p}<ArrowRight size={14}/></button>)}</div></div>}
          {chat?.messages.map(m => <ChatMessage key={m.id} role={m.role} content={m.content}/>)}
          {running && <div className="job-progress" role="status"><Loader2 size={16} className="spin"/>{chat?.job?.progress || 'Working…'}<button className="text-button" onClick={async () => { try { await post(`/jobs/${chat?.job?.id}/cancel`); if (chat) await loadChat(chat.id); } catch (e) { onError(e); } }}>Cancel</button></div>}
          {chat?.job?.error && <pre className="inline-error">{chat.job.error}</pre>}
          <div ref={messagesEnd}/>
        </div>
        <form className="chat-composer" onSubmit={e => { e.preventDefault(); submit(); }}>
          <textarea aria-label="Message" aria-describedby="composer-hint" placeholder="Describe exercises to create, or ask about an exercise…" value={prompt} disabled={running} onChange={e => setPrompt(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); submit(); } }}/>
          <div><span id="composer-hint">Enter to send · Shift+Enter for a new line</span><button className="send-button" aria-label="Send" title="Send" disabled={!model || !prompt.trim() || running || busy || loadingChat}>{busy ? <Loader2 size={18} className="spin"/> : <Send size={18}/>}</button></div>
        </form>
      </section>
      <section className="draft-panel" aria-label="Exercise draft">
        <div className="draft-header"><div><FileText size={17}/><strong>Exercise draft</strong>{draftDirty && <span>Unsaved</span>}</div><button className="icon-button" title="Download YAML" aria-label="Download draft as YAML" disabled={!draft} onClick={() => download(draft, 'exercise-collection.yaml')}><ArrowDownToLine size={17}/></button></div>
        {draft ? <>
          <textarea className="yaml-editor draft-editor" aria-label="Exercise YAML draft" spellCheck={false} value={draft} disabled={running} onChange={e => { setDraft(e.target.value); setDraftDirty(true); setValidation(''); }}/>
          <div className="draft-actions">
            <div className="button-row">
              <button className="button secondary" disabled={running} onClick={async () => { try { const valid = await post<{ yaml: string }>('/courses/validate', { yaml: draft }); setDraft(valid.yaml); await api(`/chats/${chat?.id}/draft`, { method: 'PUT', body: JSON.stringify({ yaml: valid.yaml }) }); setDraftDirty(false); setValidation('Valid collection. Saved locally.'); } catch (e) { setValidation(''); onError(e); } }}><Check size={15}/>Validate &amp; save</button>
              <button className="button" disabled={running} onClick={async () => { try { await save(); await onImport(draft); } catch (e) { onError(e); } }}><Plus size={15}/>Import to library</button>
            </div>
            {validation && <p className="validation-success" role="status"><CheckCircle2 size={14}/>{validation}</p>}
            <p>Review setup commands and checks before importing. Generation does not run them.</p>
          </div>
        </> : <div className="draft-empty"><FileText size={35}/><h3>No draft yet</h3><p>The editable YAML collection appears here once the model generates one.</p></div>}
      </section>
    </div>
    {deleteChat && <Modal title="Delete conversation?" className="small" onClose={deleting ? undefined : () => setDeleteChat(null)} description={<>Permanently delete “{deleteChat.title}” and its draft? Any running generation in this conversation will be cancelled.</>}>
      {deleteError && <p className="inline-error" role="alert">{deleteError}</p>}
      <div className="modal-actions"><button className="button secondary" autoFocus disabled={deleting} onClick={() => setDeleteChat(null)}>Cancel</button><button className="button danger" disabled={deleting} onClick={removeChat}>{deleting ? <><Loader2 size={15} className="spin"/>Deleting…</> : 'Delete conversation'}</button></div>
    </Modal>}
  </div>;
}

createRoot(document.getElementById('root')!).render(<React.StrictMode><App/></React.StrictMode>);
