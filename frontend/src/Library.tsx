import { useState } from 'react';
import type React from 'react';
import { ChevronRight, Folder, FolderOpen } from 'lucide-react';
import { progressPercent } from './api';
import type { CourseSummary } from './api';

const OPEN_KEY = 'linux-lab.library.open-folders';
export type CourseGroups = { loose: CourseSummary[]; folders: { name: string; courses: CourseSummary[] }[] };

/** Collections without a folder stay loose; folders sort by name, their collections by title (numeric aware). */
export function groupCourses(courses: CourseSummary[]): CourseGroups {
  const byTitle = (a: CourseSummary, b: CourseSummary) => a.title.localeCompare(b.title, undefined, { numeric: true });
  const folders = new Map<string, CourseSummary[]>();
  const loose: CourseSummary[] = [];
  for (const course of courses) {
    if (course.folder) folders.set(course.folder, [...(folders.get(course.folder) || []), course]);
    else loose.push(course);
  }
  return { loose, folders: [...folders].sort(([a], [b]) => a.localeCompare(b, undefined, { numeric: true })).map(([name, items]) => ({ name, courses: items.sort(byTitle) })) };
}

function readOpen(): string[] {
  try { const saved = JSON.parse(localStorage.getItem(OPEN_KEY) || '[]'); return Array.isArray(saved) ? saved : []; } catch { return []; }
}

export function CourseFolders({ groups, searching, renderCard, trailing }: { groups: CourseGroups; searching: boolean; renderCard: (course: CourseSummary) => React.ReactNode; trailing?: React.ReactNode }) {
  const [open, setOpen] = useState<string[]>(readOpen);
  const toggle = (name: string) => setOpen(current => {
    const next = current.includes(name) ? current.filter(n => n !== name) : [...current, name];
    try { localStorage.setItem(OPEN_KEY, JSON.stringify(next)); } catch { /* Not persisted. */ }
    return next;
  });
  return <>
    {(groups.loose.length > 0 || trailing) && <div className="course-grid">{groups.loose.map(renderCard)}{trailing}</div>}
    {groups.folders.map(({ name, courses }) => {
      // Search results are always shown, so a match is never hidden in a closed folder.
      const expanded = searching || open.includes(name);
      const exercises = courses.reduce((n, c) => n + c.exercise_count, 0);
      const done = courses.reduce((n, c) => n + c.completed, 0);
      const earned = courses.reduce((n, c) => n + c.earned, 0), points = courses.reduce((n, c) => n + c.points, 0);
      const running = courses.filter(c => c.environment?.state === 'running').length;
      const id = 'folder-' + name.replace(/[^a-zA-Z0-9]+/g, '-');
      return <section className={'course-folder' + (expanded ? ' open' : '')} key={name} aria-label={name}>
        <button className="course-folder-header" aria-expanded={expanded} aria-controls={id} disabled={searching} onClick={() => toggle(name)}>
          <ChevronRight className="folder-chevron" size={18}/>
          <span className="collection-icon">{expanded ? <FolderOpen size={20}/> : <Folder size={20}/>}</span>
          <span className="folder-title"><strong>{name}</strong><span>{courses.length} {courses.length === 1 ? 'collection' : 'collections'} · {exercises} exercises{running ? ` · ${running} running` : ''}</span></span>
          <span className="folder-progress"><span className="progress-track" aria-hidden="true"><span style={{ width: `${progressPercent(earned, points)}%` }}/></span><span>{done}/{exercises} complete</span></span>
        </button>
        {expanded && <div className="course-grid" id={id}>{courses.map(renderCard)}</div>}
      </section>;
    })}
  </>;
}
