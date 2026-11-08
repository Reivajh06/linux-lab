import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Markdown from 'react-markdown';
import type { Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Activity, ArrowLeft, ArrowRight, BookOpenText, Braces, Check, ChevronRight, Code, Copy, Eye, FileText, Filter, Folder, Loader2, NotebookPen, Pencil, Plus, RotateCcw, Search, Server, Shield, SquareTerminal, Trash2, X } from 'lucide-react';
import Modal from './Modal';
import { api, post } from './api';
import type { Note, NoteSummary } from './api';
import { CALLOUTS, highlightBash, inlineKind, remarkCallouts, slugify, splitSections } from './notebook-markdown';

const ICONS: Record<string, typeof FileText> = { terminal: SquareTerminal, filter: Filter, shield: Shield, code: Code, brackets: Braces, activity: Activity, server: Server, book: BookOpenText, file: FileText };
const LAST_PAGE = 'linux-lab.notebook.page';
const SHELL = new Set(['', 'bash', 'sh', 'shell', 'console', 'zsh']);
// Reference pages first, then the practices, then the learner's own folders.
const FOLDER_ORDER = ['Referencia', 'Prácticas ASO'];
const UNFILED = 'Mis páginas';

type HastNode = { type: string; value?: string; tagName?: string; properties?: { className?: string[] }; children?: HastNode[] };
const textOf = (node?: HastNode): string => node ? node.value ?? (node.children || []).map(textOf).join('') : '';

export function PageIcon({ icon, size = 18 }: { icon: string; size?: number }) {
  const Icon = ICONS[icon] || FileText;
  return <Icon size={size}/>;
}

function CodeBlock({ code, language }: { code: string; language: string }) {
  const [copied, setCopied] = useState(false);
  const shell = SHELL.has(language);
  const copy = async () => { try { await navigator.clipboard.writeText(code); setCopied(true); setTimeout(() => setCopied(false), 1500); } catch { /* Clipboard unavailable. */ } };
  return <figure className="nb-code">
    <figcaption><span>{shell ? 'bash' : language}</span><button className="nb-copy" onClick={copy} aria-label="Copy code">{copied ? <><Check size={14}/>Copied</> : <><Copy size={14}/>Copy</>}</button></figcaption>
    <pre><code>{shell ? highlightBash(code).map((t, i) => t.type === 'text' ? t.value : <span key={i} className={'sh-' + t.type}>{t.value}</span>) : code}</code></pre>
  </figure>;
}

const heading = (Tag: 'h2' | 'h3'): Components['h2'] => ({ node, children }) => {
  const id = slugify(textOf(node as HastNode).replace(/[`*_]/g, ''));
  return <Tag id={id}><a href={'#' + id} className="nb-anchor" aria-hidden="true" tabIndex={-1} onClick={e => { e.preventDefault(); document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' }); }}>#</a>{children}</Tag>;
};

const components: Components = {
  h2: heading('h2'),
  h3: heading('h3'),
  pre: ({ node }) => {
    const code = (node as HastNode).children?.find(c => c.tagName === 'code');
    const language = (code?.properties?.className || []).find(c => c.startsWith('language-'))?.slice(9).toLowerCase() || '';
    return <CodeBlock code={textOf(code).replace(/\n$/, '')} language={language}/>;
  },
  code: ({ children }) => {
    const text = String(children);
    return <code className={'nb-inline ic-' + inlineKind(text)}>{children}</code>;
  },
  table: ({ children }) => <div className="nb-table"><table>{children}</table></div>,
  a: ({ href, children }) => <a href={href} target={href?.startsWith('#') ? undefined : '_blank'} rel="noreferrer">{children}</a>,
};

export function NotebookMarkdown({ body }: { body: string }) {
  return <article className="nb-prose"><Markdown remarkPlugins={[remarkGfm, remarkCallouts]} components={components}>{body}</Markdown></article>;
}

function groupPages(pages: NoteSummary[]) {
  const groups = new Map<string, NoteSummary[]>();
  for (const page of pages) groups.set(page.folder || UNFILED, [...(groups.get(page.folder || UNFILED) || []), page]);
  const rank = (name: string) => { const i = FOLDER_ORDER.indexOf(name); return i < 0 ? (name === UNFILED ? 99 : 50) : i; };
  return [...groups].sort(([a], [b]) => rank(a) - rank(b) || a.localeCompare(b));
}

type Draft = { title: string; folder: string; body: string };

export default function Notebook({ onError, onDirtyChange }: { onError: (e: unknown) => void; onDirtyChange: (dirty: boolean) => void }) {
  const [pages, setPages] = useState<NoteSummary[] | null>(null);
  const [matches, setMatches] = useState<Set<string> | null>(null);
  const [query, setQuery] = useState('');
  const [page, setPage] = useState<Note | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [collapsed, setCollapsed] = useState<string[]>([]);
  const [confirm, setConfirm] = useState<'delete' | 'restore' | null>(null);
  const [busy, setBusy] = useState(false);
  const [section, setSection] = useState(0);
  const reader = useRef<HTMLDivElement>(null);
  const dirty = !!draft && !!page && (draft.title !== page.title || draft.folder !== (page.folder || '') || draft.body !== page.body);
  useEffect(() => onDirtyChange(dirty), [dirty, onDirtyChange]);

  const refresh = useCallback(async () => { const list = await api<NoteSummary[]>('/notes'); setPages(list); return list; }, []);
  const open = useCallback(async (id: string) => {
    const note = await api<Note>(`/notes/${encodeURIComponent(id)}`);
    setPage(note); setDraft(null);
    // Open at the first section that mentions the search, otherwise at the summary.
    const words = query.trim().toLowerCase().split(/\s+/).filter(Boolean);
    const hit = words.length ? splitSections(note.body).findIndex(s => words.every(w => (s.title + ' ' + s.body).toLowerCase().includes(w))) : -1;
    setSection(Math.max(0, hit));
    try { localStorage.setItem(LAST_PAGE, id); } catch { /* Not persisted. */ }
    reader.current?.scrollTo({ top: 0 });
  }, [query]);
  useEffect(() => {
    refresh().then(list => {
      let saved = ''; try { saved = localStorage.getItem(LAST_PAGE) || ''; } catch { /* Not persisted. */ }
      const first = list.find(p => p.id === saved) || groupPages(list)[0]?.[1][0];
      if (first) return open(first.id);
    }).catch(onError);
  }, [refresh]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    const q = query.trim();
    if (!q) { setMatches(null); return; }
    const timer = setTimeout(() => api<NoteSummary[]>('/notes?q=' + encodeURIComponent(q)).then(r => setMatches(new Set(r.map(p => p.id)))).catch(onError), 180);
    return () => clearTimeout(timer);
  }, [query, onError]);

  const leave = () => !dirty || window.confirm('Discard unsaved changes to this page?');
  const select = (id: string) => { if (id !== page?.id && leave()) open(id).catch(onError); };
  const save = useCallback(async () => {
    if (!page || !draft) return; setBusy(true);
    try { const saved = await api<Note>(`/notes/${page.id}`, { method: 'PUT', body: JSON.stringify(draft) }); setPage(saved); setDraft(null); await refresh(); }
    catch (e) { onError(e); } finally { setBusy(false); }
  }, [page, draft, refresh, onError]);
  const create = async () => {
    if (!leave()) return;
    try {
      const note = await post<Note>('/notes', { title: 'Nueva página', folder: page?.folder && !page.shipped ? page.folder : '', body: '## Apuntes\n\nEscribe aquí en **Markdown**.\n\n```bash\n# tus comandos\n```\n' });
      await refresh(); setPage(note); setDraft({ title: note.title, folder: note.folder || '', body: note.body });
    } catch (e) { onError(e); }
  };
  const finish = async () => {
    if (!page || !confirm) return; setBusy(true);
    try {
      if (confirm === 'delete') { await api(`/notes/${page.id}`, { method: 'DELETE' }); const list = await refresh(); setPage(null); if (list[0]) await open(groupPages(list)[0][1][0].id); }
      else { setPage(await post<Note>(`/notes/${page.id}/restore`)); setDraft(null); await refresh(); }
      setConfirm(null);
    } catch (e) { onError(e); } finally { setBusy(false); }
  };
  useEffect(() => {
    if (!draft) return;
    const key = (e: KeyboardEvent) => { if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') { e.preventDefault(); save(); } };
    window.addEventListener('keydown', key); return () => window.removeEventListener('keydown', key);
  }, [draft, save]);

  const body = draft?.body ?? page?.body ?? '';
  const sections = useMemo(() => splitSections(page?.body ?? ''), [page?.body]);
  const current = sections[Math.min(section, sections.length - 1)];
  const go = useCallback((index: number) => { setSection(Math.max(0, Math.min(sections.length - 1, index))); reader.current?.scrollTo({ top: 0 }); }, [sections.length]);
  useEffect(() => {
    if (draft) return;
    const key = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (target.closest('input,textarea,select,[contenteditable=true]') || e.altKey || e.ctrlKey || e.metaKey) return;
      if (e.key === 'ArrowRight') { e.preventDefault(); go(section + 1); }
      if (e.key === 'ArrowLeft') { e.preventDefault(); go(section - 1); }
    };
    window.addEventListener('keydown', key); return () => window.removeEventListener('keydown', key);
  }, [draft, section, go]);

  const folders = [...new Set((pages || []).map(p => p.folder).filter(Boolean) as string[])].sort();
  const visible = (pages || []).filter(p => !matches || matches.has(p.id));
  const groups = groupPages(visible);
  const words = body.split(/\s+/).filter(Boolean).length;
  const sectionWords = current ? current.body.split(/\s+/).filter(Boolean).length : 0;
  // Practice pages show their practice number like a man section, e.g. ASO-1-2(1.2); others use section 7 (overviews).
  const sectionNumber = page?.slug?.match(/^aso-(\d+)-(\d+)$/)?.slice(1).join('.') ?? null;

  return <div className="notebook">
    <aside className="nb-tree" aria-label="Notebook pages">
      <div className="nb-tree-head"><span><NotebookPen size={18}/>Notebook</span><button className="icon-button" title="New page" aria-label="New page" onClick={create}><Plus size={18}/></button></div>
      <label className="search-input nb-search"><Search size={16}/><input aria-label="Search notebook" placeholder="Search pages and commands…" value={query} onChange={e => setQuery(e.target.value)}/>{query && <button className="icon-button" aria-label="Clear search" onClick={() => setQuery('')}><X size={14}/></button>}</label>
      <nav className="nb-groups">
        {!pages && <div className="loading-state" role="status"><Loader2 className="spin" size={16}/>Loading…</div>}
        {pages && !visible.length && <p className="nb-empty">{query ? `No pages mention “${query.trim()}”.` : 'No pages yet.'}</p>}
        {groups.map(([folder, items]) => {
          const closed = !matches && collapsed.includes(folder);
          return <div className="nb-group" key={folder}>
            <button className="nb-group-title" aria-expanded={!closed} onClick={() => setCollapsed(c => c.includes(folder) ? c.filter(f => f !== folder) : [...c, folder])}><ChevronRight size={14} className={closed ? '' : 'open'}/><Folder size={14}/>{folder}<span>{items.length}</span></button>
            {!closed && items.map(p => <button key={p.id} className={'nb-link' + (p.id === page?.id ? ' active' : '')} aria-current={p.id === page?.id ? 'page' : undefined} onClick={() => select(p.id)}><PageIcon icon={p.icon} size={16}/><span>{p.title}</span>{p.edited && p.shipped && <i title="Edited by you"/>}</button>)}
          </div>;
        })}
      </nav>
    </aside>
    <div className="nb-reader" ref={reader}>
      {page && <div className={'nb-sheet' + (draft ? ' editing' : '')}>
        <div className="nb-manbar" aria-hidden="true"><span>{(page.slug || slugify(page.title)).toUpperCase()}{sectionNumber ? `(${sectionNumber})` : '(7)'}</span><span>{page.folder || UNFILED}</span><span>LINUX LAB NOTEBOOK</span></div>
        <header className="nb-header">
          <span className="nb-icon"><PageIcon icon={page.icon} size={26}/></span>
          <div className="nb-heading">
            {draft ? <input className="nb-title-input" aria-label="Page title" value={draft.title} maxLength={200} onChange={e => setDraft({ ...draft, title: e.target.value })}/> : <h1>{page.title}</h1>}
            <div className="nb-meta">
              {page.tags.map(t => <span className="nb-tag" key={t}>#{t}</span>)}
              <span>{Math.max(1, Math.round(words / 200))} min de lectura</span>
              <span>{page.shipped ? (page.edited ? 'Built-in · edited by you' : 'Built-in page') : 'Your page'}</span>
            </div>
          </div>
          <div className="nb-actions">
            {draft ? <>
              <button className="button secondary" disabled={busy} onClick={() => { if (leave()) setDraft(null); }}>Cancel</button>
              <button className="button" disabled={busy || !dirty || !draft.title.trim()} onClick={save}>{busy ? <Loader2 size={15} className="spin"/> : <Check size={15}/>}Save</button>
            </> : <>
              {page.shipped && page.edited && <button className="icon-button" title="Restore original" aria-label="Restore original page" onClick={() => setConfirm('restore')}><RotateCcw size={17}/></button>}
              {!page.shipped && <button className="icon-button delete-button" title="Delete page" aria-label="Delete page" onClick={() => setConfirm('delete')}><Trash2 size={17}/></button>}
              <button className="button secondary" onClick={() => setDraft({ title: page.title, folder: page.folder || '', body: page.body })}><Pencil size={15}/>Edit</button>
            </>}
          </div>
        </header>
        {draft ? <div className="nb-editor">
          <div className="nb-editor-pane">
            <label className="form-field nb-folder-field">Folder<input list="nb-folders" maxLength={80} placeholder={UNFILED} value={draft.folder} onChange={e => setDraft({ ...draft, folder: e.target.value })}/></label>
            <datalist id="nb-folders">{folders.map(f => <option key={f} value={f}/>)}</datalist>
            <textarea aria-label="Page Markdown" spellCheck={false} value={draft.body} onChange={e => setDraft({ ...draft, body: e.target.value })}/>
            <p className="field-help">Markdown with tables, <code>```bash</code> blocks and callouts: {Object.keys(CALLOUTS).slice(0, 6).map(k => `[!${k}]`).join(' ')}. Ctrl+S saves.</p>
          </div>
          <div className="nb-preview"><div className="nb-preview-label"><Eye size={14}/>Preview</div><NotebookMarkdown body={draft.body}/></div>
        </div> : <>
          <nav className="nb-sections" aria-label="Sections of this page">{sections.map((s, i) => <button key={s.id + i} className={i === section ? 'active' : ''} aria-current={i === section ? 'true' : undefined} onClick={() => go(i)}><span>{String(i + 1).padStart(2, '0')}</span>{s.title}</button>)}</nav>
          {current && <section className="nb-section" aria-label={current.title}>
            <div className="nb-section-head"><span className="nb-section-number">{String(section + 1).padStart(2, '0')}</span><h2 id={current.id}>{current.title}</h2><span className="nb-section-count">Sección {section + 1} de {sections.length} · {Math.max(1, Math.round(sectionWords / 200))} min</span></div>
            <NotebookMarkdown body={current.body}/>
          </section>}
          {sections.length > 1 && <div className="nb-pager">
            {section > 0 ? <button onClick={() => go(section - 1)}><ArrowLeft size={18}/><span><small>Anterior</small>{sections[section - 1].title}</span></button> : <span/>}
            {section < sections.length - 1 && <button className="next" onClick={() => go(section + 1)}><span><small>Siguiente</small>{sections[section + 1].title}</span><ArrowRight size={18}/></button>}
          </div>}
        </>}
      </div>}
    </div>
    {confirm && page && <Modal title={confirm === 'delete' ? `Delete “${page.title}”?` : 'Restore the original page?'} className="small" onClose={busy ? undefined : () => setConfirm(null)} description={confirm === 'delete' ? 'This permanently removes the page from your notebook.' : 'Your edits to this built-in page are replaced by the version that ships with Linux Lab. Future updates will apply again.'}>
      <div className="modal-actions"><button className="button secondary" autoFocus disabled={busy} onClick={() => setConfirm(null)}>Cancel</button><button className={'button' + (confirm === 'delete' ? ' danger' : '')} disabled={busy} onClick={finish}>{busy && <Loader2 size={15} className="spin"/>}{confirm === 'delete' ? 'Delete page' : 'Restore original'}</button></div>
    </Modal>}
  </div>;
}
