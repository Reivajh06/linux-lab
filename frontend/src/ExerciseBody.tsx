import React, { useEffect, useState } from 'react';
import Markdown from 'react-markdown';
import { ArrowRight, CheckCircle2, ChevronDown, Circle, CircleAlert, CircleX, ExternalLink, FileCode2, FileText, Lightbulb } from 'lucide-react';
import type { CheckResult, Exercise, Result } from './api';

type Tab = 'inputs' | 'outputs' | 'examples';

/** The specification and evaluation checklist of one exercise, shown beside the Linux desktop. */
export default function ExerciseBody({ exercise, index, result, actions }: { exercise: Exercise; index: number; result?: Result; actions: React.ReactNode }) {
  const tabs = ([['inputs', 'Inputs', exercise.input_requirements.length], ['outputs', 'Outputs', exercise.output_requirements.length], ['examples', 'Examples', exercise.examples.length]] as const).filter(t => t[2] > 0);
  const [tab, setTab] = useState<Tab | null>(tabs[0]?.[0] ?? null);
  useEffect(() => { setTab(tabs[0]?.[0] ?? null); }, [exercise.id]); // eslint-disable-line react-hooks/exhaustive-deps
  const outputs = Object.fromEntries(exercise.output_requirements.map(o => [o.id, o]));
  const total = exercise.evaluations.reduce((n, t) => n + t.points, 0);
  const passed = result?.tasks.filter(t => t.status === 'pass').length ?? 0;
  const program = exercise.script?.path.split('/').pop();
  return <div className="exercise-body">
    <div className="exercise-number">/{String(index + 1).padStart(2, '0')}</div>
    <h2>{exercise.title}</h2>
    <div className="spec-label">DESCRIPTION</div>
    <article className="markdown"><Markdown>{exercise.description}</Markdown></article>
    {exercise.script && <div className="deliverable"><FileCode2 size={18}/><div><small>DELIVER A SCRIPT AT</small><code>{exercise.script.path}</code>{exercise.script.usage && <span>Usage: <code>{exercise.script.usage}</code></span>}</div></div>}
    {tab && <section className="spec">
      <div className="spec-tabs" role="tablist">{tabs.map(([id, label, n]) => <button key={id} role="tab" aria-selected={tab === id} className={tab === id ? 'active' : ''} title={id === 'examples' ? 'Example runs' : `${label.slice(0, -1)} requirements`} onClick={() => setTab(id)}>{label}<span>{n}</span></button>)}</div>
      {tab === 'inputs' && <ol className="requirements">{exercise.input_requirements.map((r, i) => { const out = r.error ? outputs[r.error] : undefined; return <li key={i}><Markdown>{r.description}</Markdown>{out && <span className="on-error" title={out.description}>otherwise <ArrowRight size={11}/> <ExitBadge code={out.exit_code}/>{out.message && <code>{out.message}</code>}</span>}</li>; })}</ol>}
      {tab === 'outputs' && <div className="outputs">{exercise.output_requirements.map(o => <div className="output-row" key={o.id}><ExitBadge code={o.exit_code}/><div><Markdown>{o.description}</Markdown>{o.message && <code className="message">{o.message}</code>}</div><span className={'stream ' + o.stream}>{o.stream}</span></div>)}</div>}
      {tab === 'examples' && <div className="examples">{exercise.examples.map((e, i) => <figure key={i}>{e.description && <figcaption>{e.description}</figcaption>}<pre className="console"><span className="prompt">$ </span>{e.command}{'\n'}{e.stdout && <span>{e.stdout.replace(/\n$/, '')}{'\n'}</span>}{e.stderr && <span className="err">{e.stderr.replace(/\n$/, '')}{'\n'}</span>}{e.exit_code !== undefined && <span className="status"><span className="prompt">$ </span>echo $?{'\n'}{e.exit_code}</span>}</pre></figure>)}</div>}
    </section>}
    <div className="task-heading">EVALUATIONS <span>{result ? `${passed}/${exercise.evaluations.length} passed · ` : `${exercise.evaluations.length} cases · `}{result?.earned ?? 0}/{total} pts</span></div>
    <div className="tasks">{exercise.evaluations.map(task => {
      const evaluated = result?.tasks.find(t => t.id === task.id);
      const run = task.checks.find(c => c.type === 'run');
      return <div className={'task ' + (evaluated?.status || '')} key={task.id}>
        <div className="task-line">{evaluated?.status === 'pass' ? <CheckCircle2 size={18}/> : evaluated?.status === 'error' ? <CircleAlert size={18}/> : evaluated?.status === 'fail' ? <CircleX size={18}/> : <Circle size={18}/>}<div><Markdown>{task.description}</Markdown>{run && program && <code className="case-command">{program}{run.args?.map(a => ' ' + quote(a)).join('')}{run.requirement && outputs[run.requirement] && <em className={outputs[run.requirement].exit_code === 0 ? 'ok' : ''}> → exit {outputs[run.requirement].exit_code}</em>}</code>}</div><span>{evaluated?.earned ?? 0}/{task.points}</span></div>
        {evaluated && evaluated.status !== 'pass' && <details className="task-feedback" open={evaluated.checks.some(c => c.command)}><summary>{evaluated.status === 'error' ? 'Check error' : 'Not passing yet'} · details</summary>{evaluated.checks.filter(c => c.status !== 'pass').map((c, i) => <Feedback key={i} check={c}/>)}</details>}
      </div>;
    })}</div>
    {exercise.tips.length > 0 && <details className="tips"><summary><Lightbulb size={17}/> Tips<ChevronDown size={15}/></summary><ul>{exercise.tips.map((tip, i) => <li key={i}><Markdown>{tip}</Markdown></li>)}</ul></details>}
    {exercise.sources.length > 0 && <div className="exercise-sources"><div className="task-heading">SOURCE MATERIAL</div>{exercise.sources.map((s, i) => s.available ? <a key={i} href={`/api/sources/${s.source_id}/pdf#page=${s.pages[0]}`} target="_blank" rel="noreferrer"><FileText size={14}/>{s.title} · p. {s.pages.join(', ')}<ExternalLink size={12}/></a> : <span key={i}>{s.title} · p. {s.pages.join(', ')} (source unavailable)</span>)}</div>}
    {exercise.supplemental && <p className="supplemental">Additional Linux guidance: {exercise.supplemental}</p>}
    {actions}
  </div>;
}

function ExitBadge({ code }: { code: number }) { return <span className={'exit-badge ' + (code === 0 ? 'ok' : 'err')}>exit {code}</span>; }

function quote(arg: string) { return /^[\w@%+=:,./-]+$/.test(arg) ? arg : `'${arg.replace(/'/g, `'\\''`)}'`; }

function Feedback({ check }: { check: CheckResult }) {
  if (!check.command) return <div><strong>{check.status}</strong> — {check.message}{check.stdout && <pre>{check.stdout}</pre>}{check.stderr && <pre>{check.stderr}</pre>}</div>;
  return <div className="run-feedback">
    <pre className="console"><span className="prompt">$ </span>{check.command}</pre>
    <p>{check.message}</p>
    {check.exit_code !== undefined && <div className="exit-compare">exit code <ExitBadge code={check.exit_code}/> expected <ExitBadge code={check.expected_exit ?? 0}/></div>}
    {(['stdout', 'stderr'] as const).map(stream => {
      const actual = check[stream] ?? '', expected = check[stream === 'stdout' ? 'expected_stdout' : 'expected_stderr'];
      if (!actual && expected === undefined) return null;
      return <div className="stream-compare" key={stream}><div><small>YOUR {stream.toUpperCase()}</small><pre>{actual || '(empty)'}</pre></div>{expected !== undefined && <div><small>EXPECTED</small><pre>{expected || '(empty)'}</pre></div>}</div>;
    })}
  </div>;
}
