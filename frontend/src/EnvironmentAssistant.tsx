import { useEffect, useRef, useState } from 'react';
import { ArrowRight, ChevronDown, Loader2, Send, Square } from 'lucide-react';
import { api, selectLocalModel, stream } from './api';
import type { Preferences } from './theme';
import ChatMessage from './ChatMessage';

type Message = { role: 'user' | 'assistant'; content: string };
type Models = { name: string }[];

export default function EnvironmentAssistant({ environmentId, exerciseId, active }: { environmentId: string; exerciseId: string | null; active: boolean }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [prompt, setPrompt] = useState('');
  const [models, setModels] = useState<Models>([]);
  const [model, setModel] = useState('');
  const [loading, setLoading] = useState(true);
  const [modelError, setModelError] = useState('');
  const [error, setError] = useState('');
  const [streaming, setStreaming] = useState(false);
  const controller = useRef<AbortController | null>(null);
  const messageList = useRef<HTMLDivElement>(null);
  const composer = useRef<HTMLTextAreaElement>(null);
  useEffect(() => {
    let disposed = false;
    (async () => {
      try {
        const [response, saved] = await Promise.all([api<Models | { models: Models; available?: boolean; message?: string }>('/ollama/models'), api<Preferences>('/preferences').catch(() => null)]);
        if (disposed) return;
        const local = Array.isArray(response) ? response : response.models;
        const unavailable = !Array.isArray(response) && response.available === false;
        setModels(unavailable ? [] : local); setModel(selectLocalModel(unavailable ? [] : local, saved?.model || ''));
        setModelError(unavailable ? response.message || 'Ollama is unreachable.' : local.length ? '' : 'Ollama has no local models. Download a model to start chatting.');
      } catch { if (!disposed) setModelError('Ollama is unreachable. Check that it is running.'); }
      finally { if (!disposed) setLoading(false); }
    })();
    return () => { disposed = true; controller.current?.abort(); controller.current = null; };
  }, []);
  useEffect(() => { if (active && messageList.current) messageList.current.scrollTop = messageList.current.scrollHeight; }, [messages, active, error]);
  const clear = () => { controller.current?.abort(); controller.current = null; setStreaming(false); setMessages([]); setPrompt(''); setError(''); composer.current?.focus(); };
  const submit = async () => {
    if (!prompt.trim() || !model || controller.current) return;
    const conversation: Message[] = [...messages, { role: 'user', content: prompt.trim() }];
    const request = new AbortController(); controller.current = request;
    setMessages([...conversation, { role: 'assistant', content: '' }]); setPrompt(''); setError(''); setStreaming(true);
    try {
      await stream(`/environments/${environmentId}/assistant`, { model, exercise_id: exerciseId, messages: conversation }, text => {
        if (controller.current !== request) return;
        setMessages(current => current.map((message, i) => i === current.length - 1 ? { ...message, content: message.content + text } : message));
      }, request.signal);
    } catch (e) { if (!request.signal.aborted && controller.current === request) setError(e instanceof Error ? e.message : String(e)); }
    finally {
      if (controller.current === request) {
        controller.current = null; setStreaming(false);
        setMessages(current => current.filter((message, i) => i !== current.length - 1 || message.content));
      }
    }
  };
  const suggestions = exerciseId ? ['Explain what this exercise asks', 'Give me a hint for the next step', 'Which commands should I look at?'] : ['Help me explore this environment', 'Suggest a Linux task to practice', 'Which commands should I learn first?'];
  return <section className="environment-assistant" aria-label="Environment assistant">
    <div className="assistant-header"><div><span>Temporary chat · not saved</span><button className="text-button" onClick={clear} disabled={!messages.length && !prompt}>Clear</button></div>
      <div className="select-wrap"><select aria-label="Assistant model" value={model} disabled={loading || streaming || !models.length} onChange={e => setModel(e.target.value)}>{!models.length && <option value="">{loading ? 'Loading models…' : 'No local models'}</option>}{models.map(m => <option key={m.name} value={m.name}>{m.name}</option>)}</select><ChevronDown size={14}/></div>
      {modelError && <p className="assistant-model-error" role="status">{modelError}</p>}
    </div>
    <div className="messages" ref={messageList} aria-live="polite" aria-relevant="additions text">
      {!messages.length && <div className="chat-welcome assistant-welcome"><p>Ask about this environment or the current exercise.</p><div className="prompt-suggestions">{suggestions.map(text => <button key={text} onClick={() => { setPrompt(text); composer.current?.focus(); }}>{text}<ArrowRight size={14}/></button>)}</div></div>}
      {messages.map((message, i) => <ChatMessage key={i} {...message}/>)}
      {error && <p className="inline-error" role="alert">{error}</p>}
    </div>
    <form className="chat-composer" onSubmit={e => { e.preventDefault(); submit(); }}>
      <textarea ref={composer} aria-label="Ask the environment assistant" aria-describedby="assistant-composer-hint" placeholder="Ask a question…" value={prompt} onChange={e => setPrompt(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); submit(); } }}/>
      <div><span id="assistant-composer-hint">Enter to send · Shift+Enter for a new line</span>{streaming ? <button type="button" className="button secondary" onClick={() => controller.current?.abort()}><Square size={13}/>Stop</button> : <button className="send-button" aria-label="Send to assistant" disabled={!prompt.trim() || !model || loading}>{loading ? <Loader2 size={17} className="spin"/> : <Send size={17}/>}</button>}</div>
    </form>
  </section>;
}
