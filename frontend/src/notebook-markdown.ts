/** Helpers for Notebook pages: Bash colouring, Obsidian-style callouts and the page outline. */

export type Token = { type: 'text' | 'comment' | 'string' | 'variable' | 'keyword' | 'command' | 'option' | 'operator' | 'number' | 'prompt'; value: string };

const KEYWORDS = new Set(['if', 'then', 'elif', 'else', 'fi', 'for', 'in', 'do', 'done', 'while', 'until', 'case', 'esac', 'function', 'return', 'exit', 'local', 'declare', 'readonly', 'export', 'break', 'continue', 'shift', 'set', 'unset', 'select', 'time']);
// After these, the next word is a new command (pipes, lists, keywords that open a command position).
const COMMAND_START = new Set(['|', '||', '&&', ';', '&', '(', '$(', '`', 'then', 'do', 'else', 'elif', 'if', 'while', 'until', '!', '{', 'time', 'sudo', 'exec', 'xargs', 'nohup', 'env', 'command', 'builtin']);

/** Tokenise Bash for colouring. It is a reader's aid, not a parser: unusual syntax falls back to plain text. */
export function highlightBash(code: string): Token[] {
  const tokens: Token[] = [];
  const push = (type: Token['type'], value: string) => {
    const last = tokens[tokens.length - 1];
    if (last && last.type === type && type === 'text') last.value += value; else tokens.push({ type, value });
  };
  let expectCommand = true;
  let i = 0;
  while (i < code.length) {
    const rest = code.slice(i);
    const ch = code[i];
    const atLineStart = i === 0 || code[i - 1] === '\n';
    let m: RegExpMatchArray | null;
    if (ch === '\n') { push('text', ch); i++; expectCommand = true; continue; }
    if (atLineStart && (m = rest.match(/^(\$|#) (?=\S)/)) && m[1] === '$') { push('prompt', m[0]); i += m[0].length; expectCommand = true; continue; }
    if (/\s/.test(ch)) { m = rest.match(/^[ \t]+/)!; push('text', m[0]); i += m[0].length; continue; }
    if (ch === '#' && (i === 0 || /[\s;|&(]/.test(code[i - 1]))) { m = rest.match(/^#[^\n]*/)!; push('comment', m[0]); i += m[0].length; continue; }
    if (ch === "'") { const end = code.indexOf("'", i + 1); const stop = end < 0 ? code.length : end + 1; push('string', code.slice(i, stop)); i = stop; expectCommand = false; continue; }
    if (ch === '"') {
      // Keep variables inside double quotes coloured as variables.
      let j = i + 1, chunk = '"';
      while (j < code.length && code[j] !== '"') {
        if (code[j] === '\\' && j + 1 < code.length) { chunk += code.slice(j, j + 2); j += 2; continue; }
        const v = code.slice(j).match(/^\$(\{[^}\n]*\}|[A-Za-z_][A-Za-z0-9_]*|[0-9#?@*$!-])/);
        if (v) { push('string', chunk); chunk = ''; push('variable', v[0]); j += v[0].length; continue; }
        chunk += code[j]; j++;
      }
      if (j < code.length) { chunk += '"'; j++; }
      push('string', chunk); i = j; expectCommand = false; continue;
    }
    if ((m = rest.match(/^\$\(\(|^\$\(/))) { push('operator', m[0]); i += m[0].length; expectCommand = m[0] === '$('; continue; }
    if ((m = rest.match(/^\$(\{[^}\n]*\}|[A-Za-z_][A-Za-z0-9_]*|[0-9#?@*$!-])/))) { push('variable', m[0]); i += m[0].length; expectCommand = false; continue; }
    if ((m = rest.match(/^(\|\||&&|;;|\[\[|\]\]|[0-9]?>>?&?[0-9-]?|<<<|<<-?|[0-9]?<&?|&>|[|;&(){}\[\]<>`!])/))) {
      push('operator', m[0]); i += m[0].length;
      expectCommand = COMMAND_START.has(m[0]);
      continue;
    }
    m = rest.match(/^(\\.|[^\s|;&(){}<>`'"$#\\]|#(?<=\S#))+/) || rest.match(/^\S/)!;
    const word = m[0];
    i += word.length;
    if (/^[A-Za-z_][A-Za-z0-9_]*\+?=/.test(word) && expectCommand) { const eq = word.indexOf('='); push('variable', word.slice(0, eq)); push('operator', '='); if (word.length > eq + 1) push('text', word.slice(eq + 1)); continue; }
    if (KEYWORDS.has(word) && expectCommand) { push('keyword', word); expectCommand = COMMAND_START.has(word); continue; }
    if (expectCommand) { push('command', word); expectCommand = COMMAND_START.has(word); continue; }
    if (/^--?[A-Za-z0-9]/.test(word)) push('option', word);
    else if (/^-?\d+(\.\d+)?$/.test(word)) push('number', word);
    else push('text', word);
  }
  return tokens;
}

/** Colour class for inline code: options, variables, paths and commands read differently at a glance. */
export function inlineKind(code: string): 'option' | 'variable' | 'path' | 'command' {
  if (/^--?[A-Za-z0-9]/.test(code)) return 'option';
  if (/^\$/.test(code)) return 'variable';
  if (/^(\/|~\/|\.\/)/.test(code)) return 'path';
  return 'command';
}

export function slugify(text: string): string {
  return text.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'section';
}

export type Heading = { depth: 2 | 3; text: string; id: string };

/** `##` and `###` headings outside fenced code, with the ids the renderer gives them. */
export function outline(markdown: string): Heading[] {
  const headings: Heading[] = [];
  let fence: string | null = null;
  for (const line of markdown.split('\n')) {
    const f = line.match(/^\s*(```|~~~)/);
    if (f) { fence = fence === f[1] ? null : fence ?? f[1]; continue; }
    if (fence) continue;
    const h = line.match(/^(##|###)\s+(.+?)\s*#*\s*$/);
    if (h) { const text = h[2].replace(/[`*_]/g, ''); headings.push({ depth: h[1].length as 2 | 3, text, id: slugify(text) }); }
  }
  return headings;
}

export const CALLOUTS: Record<string, { label: string; tone: string }> = {
  note: { label: 'Nota', tone: 'info' }, info: { label: 'Info', tone: 'info' }, summary: { label: 'Resumen', tone: 'accent' }, abstract: { label: 'Resumen', tone: 'accent' },
  tip: { label: 'Consejo', tone: 'success' }, hint: { label: 'Consejo', tone: 'success' }, success: { label: 'Correcto', tone: 'success' },
  warning: { label: 'Cuidado', tone: 'warning' }, caution: { label: 'Cuidado', tone: 'warning' }, important: { label: 'Importante', tone: 'warning' },
  danger: { label: 'Peligro', tone: 'danger' }, error: { label: 'Error', tone: 'danger' }, bug: { label: 'Error', tone: 'danger' },
  example: { label: 'Ejemplo', tone: 'violet' }, question: { label: 'Pregunta', tone: 'violet' }, quote: { label: 'Cita', tone: 'muted' },
};

type MdNode = { type: string; value?: string; children?: MdNode[]; data?: Record<string, unknown> };

/** Remark plugin: `> [!tip] Title` blockquotes become callout blocks with a title row. */
export function remarkCallouts() {
  return (tree: MdNode) => {
    const visit = (node: MdNode) => {
      node.children?.forEach(visit);
      if (node.type !== 'blockquote') return;
      const first = node.children?.[0];
      const text = first?.type === 'paragraph' ? first.children?.[0] : undefined;
      const m = text?.type === 'text' ? text.value!.match(/^\[!(\w+)\][+-]?[ \t]*([^\n]*)\n?/) : null;
      if (!m || !first || !text) return;
      const kind = m[1].toLowerCase();
      const style = CALLOUTS[kind] || CALLOUTS.note;
      text.value = text.value!.slice(m[0].length);
      if (!text.value) first.children!.shift();
      if (!first.children!.length) node.children!.shift();
      node.data = { hName: 'aside', hProperties: { className: ['callout', 'tone-' + style.tone], 'data-kind': kind } };
      node.children!.unshift({ type: 'paragraph', data: { hName: 'div', hProperties: { className: ['callout-title'] } }, children: [{ type: 'text', value: m[2].trim() || style.label }] });
    };
    visit(tree);
  };
}

export type Section = { title: string; id: string; body: string };

/** Split a page into sections at `##` headings (outside code fences); text before the first one is the summary. */
export function splitSections(markdown: string, introTitle = 'Resumen'): Section[] {
  const sections: Section[] = [];
  let current: Section = { title: introTitle, id: 'resumen', body: '' };
  let fence: string | null = null;
  for (const line of markdown.split('\n')) {
    const f = line.match(/^\s*(```|~~~)/);
    if (f) fence = fence === f[1] ? null : fence ?? f[1];
    const h = !fence && !f ? line.match(/^##\s+(.+?)\s*#*\s*$/) : null;
    if (h) {
      if (current.body.trim()) sections.push(current);
      const title = h[1].replace(/[`*_]/g, '');
      current = { title, id: slugify(title), body: '' };
      continue;
    }
    current.body += line + '\n';
  }
  if (current.body.trim() || !sections.length) sections.push(current);
  return sections.map(s => ({ ...s, body: s.body.replace(/^\n+|\n+$/g, '') + '\n' }));
}
