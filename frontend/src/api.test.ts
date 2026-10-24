import { describe, expect, it } from 'vitest';
import { progressPercent, selectLocalModel } from './api';

describe('course progress', () => {
  it('handles an empty library and partial points', () => {
    expect(progressPercent(0, 0)).toBe(0);
    expect(progressPercent(5, 30)).toBe(17);
    expect(progressPercent(30, 30)).toBe(100);
  });
});

describe('local model selection', () => {
  const models = [{ name: 'qwen3:14b' }, { name: 'gemma4:26b-a4b-it-qat' }];
  it('selects an available model when the saved model was removed', () => {
    expect(selectLocalModel(models, 'gemma3:12b-it-qat')).toBe('qwen3:14b');
  });
  it('keeps the saved model when available and handles an empty list', () => {
    expect(selectLocalModel(models, models[1].name)).toBe(models[1].name);
    expect(selectLocalModel([], 'old-model')).toBe('');
  });
});
