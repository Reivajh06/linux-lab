import { useCallback, useEffect, useState } from 'react';
import { Cpu, ExternalLink, HardDrive, Layers3, Loader2, Pencil, Play, Plus, RefreshCw, Square, Terminal, Trash2 } from 'lucide-react';
import Modal from './Modal';
import { api, post } from './api';
import type { CourseSummary, Environment } from './api';

type Definition = { name: string; course_key: string; cpus: number; memory_mb: number; pids: number };
const fresh: Definition = { name: '', course_key: '', cpus: 2, memory_mb: 2048, pids: 256 };
const message = (e: unknown) => e instanceof Error ? e.message : String(e);

export default function Environments({ courses, onOpen, onError, onChanged }: { courses: CourseSummary[]; onOpen: (environment: Environment) => void; onError: (error: unknown) => void; onChanged: () => Promise<void> }) {
  const [environments, setEnvironments] = useState<Environment[]>([]);
  const [definition, setDefinition] = useState<Definition | null>(null);
  const [editing, setEditing] = useState<Environment | null>(null);
  const [deleting, setDeleting] = useState<Environment | null>(null);
  const [busy, setBusy] = useState('');
  const [dialogError, setDialogError] = useState('');
  const [loaded, setLoaded] = useState(false);
  const load = useCallback(async () => { setEnvironments(await api<Environment[]>('/environments')); setLoaded(true); }, []);
  useEffect(() => { load().catch(onError); }, [load, onError]);
  const action = async (environment: Environment, operation: string) => {
    setBusy(environment.id);
    try { await post(`/environments/${environment.id}/${operation}`); await load(); await onChanged(); }
    catch (e) { onError(e); await load().catch(onError); } finally { setBusy(''); }
  };
  const save = async () => {
    if (!definition) return; setBusy('save'); setDialogError('');
    try {
      if (editing) await api(`/environments/${editing.id}`, { method: 'PATCH', body: JSON.stringify({ name: definition.name, cpus: definition.cpus, memory_mb: definition.memory_mb, pids: definition.pids }) });
      else await post('/environments', { ...definition, course_key: definition.course_key || null });
      setDefinition(null); setEditing(null); await load();
    } catch (e) { setDialogError(message(e)); } finally { setBusy(''); }
  };
  const remove = async () => {
    if (!deleting) return; setBusy('delete'); setDialogError('');
    try { await api(`/environments/${deleting.id}`, { method: 'DELETE' }); setDeleting(null); await load(); await onChanged(); }
    catch (e) { setDialogError(message(e)); } finally { setBusy(''); }
  };
  const edit = (environment: Environment | null) => {
    setEditing(environment); setDialogError('');
    setDefinition(environment ? { name: environment.name, course_key: environment.course_key || '', cpus: environment.cpus, memory_mb: environment.memory_mb, pids: environment.pids } : { ...fresh });
  };
  const running = environments.filter(e => e.state === 'running').length;
  return <div className="page environments-page">
    <div className="page-heading"><div><h1>Environments</h1><p>Create and manage Linux environments for practice or a course.</p></div><button className="button" onClick={() => edit(null)}><Plus size={17}/>Create environment</button></div>
    <div className="environment-summary"><span><Layers3 size={16}/>{environments.length} {environments.length === 1 ? 'environment' : 'environments'}</span><span><span className={'dot ' + (running ? '' : 'warn')}/>{running} running</span><button className="text-button" onClick={() => load().catch(onError)}><RefreshCw size={14}/>Refresh</button></div>
    <div className="environment-grid">
      {!loaded && <div className="loading-state" role="status"><Loader2 className="spin" size={18}/>Loading environments…</div>}
      {loaded && !environments.length && <div className="empty-state"><Terminal size={30}/><h3>No environments yet</h3><p>Create an environment, or open a course from the Exercise Library to get one automatically.</p><button className="button" onClick={() => edit(null)}><Plus size={16}/>Create environment</button></div>}
      {environments.map(environment => <section className="environment-card" key={environment.id} aria-label={environment.name}>
        <div className="environment-top"><span className="collection-icon"><Terminal size={22}/></span><span className={'environment-status ' + environment.state}><span className="dot"/>{environment.state}</span></div>
        <h2>{environment.name}</h2>
        <p className="environment-course">{environment.course_key ? courses.find(c => c.key === environment.course_key)?.title || 'Course environment' : 'Free practice'}{environment.is_default ? ' · Primary' : ''}</p>
        <div className="environment-resources"><span><Cpu size={14}/>{environment.cpus} {environment.cpus === 1 ? 'CPU' : 'CPUs'}</span><span><HardDrive size={14}/>{environment.memory_mb >= 1024 && environment.memory_mb % 1024 === 0 ? `${environment.memory_mb / 1024} GB` : `${environment.memory_mb} MB`}</span><span>{environment.pids} processes</span></div>
        <p className="environment-image">Fedora 44 · vim, nano, gedit, Firefox</p>
        {environment.error && <p className="inline-error">{environment.error}</p>}
        <div className="environment-actions">
          <button className="button" disabled={!!busy} onClick={() => onOpen(environment)}><ExternalLink size={14}/>Open</button>
          <button className="button secondary" disabled={!!busy} onClick={() => action(environment, environment.state === 'running' ? 'stop' : 'start')}>{busy === environment.id ? <Loader2 size={14} className="spin"/> : environment.state === 'running' ? <Square size={13}/> : <Play size={14}/>}{environment.state === 'running' ? 'Stop' : 'Start'}</button>
          <button className="icon-button environment-edit" title="Edit environment" aria-label={`Edit ${environment.name}`} disabled={!!busy} onClick={() => edit(environment)}><Pencil size={16}/></button>
          <button className="icon-button delete-button" title="Delete environment" aria-label={`Delete ${environment.name}`} disabled={!!busy} onClick={() => { setDialogError(''); setDeleting(environment); }}><Trash2 size={16}/></button>
        </div>
      </section>)}
    </div>
    {definition && <Modal title={editing ? 'Edit environment' : 'Create environment'} className="small" closeLabel="Close environment editor" onClose={() => setDefinition(null)}>
      <form onSubmit={e => { e.preventDefault(); save(); }}>
        <label className="form-field">Name<input autoFocus required maxLength={100} value={definition.name} placeholder="e.g. Users and groups practice" onChange={e => setDefinition({ ...definition, name: e.target.value })}/></label>
        <label className="form-field">Environment type<select disabled={!!editing} value={definition.course_key} onChange={e => setDefinition({ ...definition, course_key: e.target.value })}><option value="">Free practice</option>{courses.map(course => <option key={course.key} value={course.key}>{course.title} · v{course.version}</option>)}</select></label>
        <div className="resource-fields">
          <label className="form-field">CPUs<input type="number" required min={.5} max={32} step={.5} disabled={editing?.state === 'running'} value={definition.cpus} onChange={e => setDefinition({ ...definition, cpus: Number(e.target.value) })}/></label>
          <label className="form-field">Memory (MB)<input type="number" required min={512} max={65536} step={256} disabled={editing?.state === 'running'} value={definition.memory_mb} onChange={e => setDefinition({ ...definition, memory_mb: Number(e.target.value) })}/></label>
          <label className="form-field">Process limit<input type="number" required min={64} max={4096} disabled={editing?.state === 'running'} value={definition.pids} onChange={e => setDefinition({ ...definition, pids: Number(e.target.value) })}/></label>
        </div>
        {editing?.state === 'running' && <p className="field-help">Stop the environment to change resource limits.</p>}
        <p className="field-help">Fedora 44 with a desktop, command-line tools, editors, and offline manuals. Course setup runs when the environment first starts.</p>
        {dialogError && <pre role="alert" className="inline-error">{dialogError}</pre>}
        <div className="modal-actions"><button type="button" className="button secondary" onClick={() => setDefinition(null)}>Cancel</button><button className="button" disabled={busy === 'save' || !definition.name.trim()}>{busy === 'save' && <Loader2 size={15} className="spin"/>}{busy === 'save' ? 'Saving…' : editing ? 'Save changes' : 'Create environment'}</button></div>
      </form>
    </Modal>}
    {deleting && <Modal title={`Delete ${deleting.name}?`} className="small" onClose={busy ? undefined : () => setDeleting(null)} description="This permanently removes the environment, its files, users, installed packages, and scores. Imported courses and sources remain available.">
      {dialogError && <pre role="alert" className="inline-error">{dialogError}</pre>}
      <div className="modal-actions"><button className="button secondary" autoFocus disabled={!!busy} onClick={() => setDeleting(null)}>Cancel</button><button className="button danger" disabled={!!busy} onClick={remove}>{busy === 'delete' && <Loader2 size={15} className="spin"/>}{busy === 'delete' ? 'Deleting…' : 'Delete environment'}</button></div>
    </Modal>}
  </div>;
}
