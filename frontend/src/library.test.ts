import { describe, expect, it } from 'vitest';
import { groupCourses } from './Library';
import type { CourseSummary } from './api';

const course = (title: string, folder: string | null) => ({ key: title, title, folder } as CourseSummary);

describe('groupCourses', () => {
  it('keeps unfoldered collections loose and sorts folders and titles naturally', () => {
    const groups = groupCourses([course('P 3.1', 'B'), course('Foundations', null), course('P 10', 'B'), course('P 2', 'B'), course('X', 'A')]);
    expect(groups.loose.map(c => c.title)).toEqual(['Foundations']);
    expect(groups.folders.map(f => f.name)).toEqual(['A', 'B']);
    expect(groups.folders[1].courses.map(c => c.title)).toEqual(['P 2', 'P 3.1', 'P 10']);
  });
});
