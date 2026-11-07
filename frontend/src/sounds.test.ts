import { describe, expect, it } from 'vitest';
import type { Result } from './api';
import { evaluationSound } from './sounds';

const result = (id: string, earned: number, available = 10, status = earned >= available ? 'pass' : 'fail'): Result =>
  ({ exercise_id: id, earned, available, checked_at: '', tasks: [{ id: 't', status, earned, available, checks: [] }] });

describe('evaluationSound', () => {
  const ids = ['a', 'b'];
  it('celebrates completing the last exercise of a course', () => {
    expect(evaluationSound({ a: result('a', 10) }, [result('b', 10)], ids)).toBe('course');
  });
  it('plays the completion sound for one finished exercise', () => {
    expect(evaluationSound({}, [result('a', 10)], ids)).toBe('complete');
  });
  it('rewards partial progress', () => {
    expect(evaluationSound({ a: result('a', 2) }, [result('a', 6)], ids)).toBe('progress');
  });
  it('warns when points are lost', () => {
    expect(evaluationSound({ a: result('a', 10) }, [result('a', 4)], ids)).toBe('regress');
  });
  it('buzzes when nothing improved', () => {
    expect(evaluationSound({}, [result('a', 0)], ids)).toBe('wrong');
    expect(evaluationSound({ a: result('a', 4) }, [result('a', 4)], ids)).toBe('wrong');
  });
  it('flags check errors', () => {
    expect(evaluationSound({}, [result('a', 0, 10, 'error')], ids)).toBe('error');
  });
  it('re-confirms an exercise that is still complete', () => {
    expect(evaluationSound({ a: result('a', 10) }, [result('a', 10)], ids)).toBe('complete');
  });
});
