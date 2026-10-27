import { Sparkles } from 'lucide-react';
import Markdown from 'react-markdown';

export default function ChatMessage({ role, content }: { role: string; content: string }) {
  return <div className={'message ' + (role === 'user' ? 'user' : 'assistant')}>
    {role !== 'user' && <span className="message-avatar" aria-hidden="true"><Sparkles size={15}/></span>}
    <div className="message-content"><article className="markdown">{content ? <Markdown>{content}</Markdown> : <span className="message-pending" role="status">Thinking…</span>}</article></div>
  </div>;
}
