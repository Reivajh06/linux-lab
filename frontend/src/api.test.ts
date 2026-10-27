import { afterEach, describe, expect, it, vi } from 'vitest';
import { configure, progressPercent, selectLocalModel, stream } from './api';

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

describe('streaming requests', () => {
  afterEach(() => vi.unstubAllGlobals());
  it('sends the lab token and JSON and decodes split UTF-8 chunks as they arrive', async () => {
    const bytes = new TextEncoder().encode('Hi 🌍\n\n**Error:** model stopped');
    const fetch = vi.fn().mockResolvedValueOnce(new Response(JSON.stringify({ token: 'lab-token' }))).mockResolvedValueOnce(new Response(new ReadableStream({ start(controller) {
      controller.enqueue(bytes.slice(0, 5)); controller.enqueue(bytes.slice(5)); controller.close();
    } })));
    vi.stubGlobal('fetch', fetch);
    await configure();
    const onText = vi.fn(), controller = new AbortController();
    const data = { model: 'local', exercise_id: null, messages: [{ role: 'user', content: 'Hello' }] };
    await stream('/environments/lab/assistant', data, onText, controller.signal);
    expect(onText.mock.calls.map(([text]) => text).join('')).toBe('Hi 🌍\n\n**Error:** model stopped');
    expect(onText).toHaveBeenCalledTimes(2);
    const [path, options] = fetch.mock.calls[1];
    expect(path).toBe('/api/environments/lab/assistant');
    expect(options.method).toBe('POST');
    expect(options.headers.get('X-Lab-Token')).toBe('lab-token');
    expect(options.headers.get('Content-Type')).toBe('application/json');
    expect(JSON.parse(options.body)).toEqual(data);
    expect(options.signal).toBe(controller.signal);
  });
  it('throws the server detail on non-success responses', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: 'Model not found' }), { status: 404 })));
    await expect(stream('/assistant', {}, vi.fn())).rejects.toThrow('Model not found');
  });
  it('preserves delivered text and propagates a stream failure', async () => {
    let source: ReadableStreamDefaultController<Uint8Array>;
    const body = new ReadableStream<Uint8Array>({ start(controller) { source = controller; controller.enqueue(new TextEncoder().encode('Partial')); } });
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(body)));
    const onText = vi.fn(() => source.error(new Error('Connection lost')));
    await expect(stream('/assistant', {}, onText)).rejects.toThrow('Connection lost');
    expect(onText).toHaveBeenCalledWith('Partial');
    expect(body.locked).toBe(false);
  });
  it('propagates an abort after keeping partial text', async () => {
    const controller = new AbortController();
    const body = new ReadableStream<Uint8Array>({ start(source) {
      source.enqueue(new TextEncoder().encode('Partial'));
      controller.signal.addEventListener('abort', () => source.error(new DOMException('Aborted', 'AbortError')));
    } });
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(body)));
    const onText = vi.fn(() => controller.abort());
    await expect(stream('/assistant', {}, onText, controller.signal)).rejects.toMatchObject({ name: 'AbortError' });
    expect(onText).toHaveBeenCalledWith('Partial');
    expect(body.locked).toBe(false);
  });
});
