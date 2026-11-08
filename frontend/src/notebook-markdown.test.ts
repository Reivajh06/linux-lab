import { describe, expect, it } from 'vitest';
import { highlightBash, inlineKind, outline, remarkCallouts, splitSections } from './notebook-markdown';

const kinds = (code: string) => highlightBash(code).filter(t => t.value.trim()).map(t => `${t.type}:${t.type === "prompt" ? t.value : t.value.trim()}`);

describe('highlightBash', () => {
  it('colours commands, options, strings, variables and comments', () => {
    expect(kinds(`grep -c "$1" /etc/passwd | sort -n # cuenta`)).toEqual(['command:grep', 'option:-c', 'string:"', 'variable:$1', 'string:"', 'text:/etc/passwd', 'operator:|', 'command:sort', 'option:-n', 'comment:# cuenta']);
  });
  it('knows keywords, assignments and command substitution', () => {
    expect(kinds('if [[ -f $f ]]; then n=$(wc -l < "$f"); fi')).toEqual(['keyword:if', 'operator:[[', 'option:-f', 'variable:$f', 'operator:]]', 'operator:;', 'keyword:then', 'variable:n', 'operator:=', 'operator:$(', 'command:wc', 'option:-l', 'operator:<', 'string:"', 'variable:$f', 'string:"', 'operator:)', 'operator:;', 'keyword:fi']);
  });
  it('keeps the full text intact', () => {
    const code = "for x in \"$@\"; do echo '#no' ${x%.txt} 2>&1; done\n$ ls -la";
    expect(highlightBash(code).map(t => t.value).join('')).toBe(code);
    expect(kinds('$ ls -la')).toEqual(['prompt:$ ', 'command:ls', 'option:-la']);
  });
});

describe('notebook markdown helpers', () => {
  it('classifies inline code', () => {
    expect(['-n', '$HOME', '/etc/passwd', 'chmod 755'].map(inlineKind)).toEqual(['option', 'variable', 'path', 'command']);
  });
  it('outlines headings outside code fences', () => {
    expect(outline('## Filtros de texto\n```bash\n## no\n```\n### `grep` básico')).toEqual([{ depth: 2, text: 'Filtros de texto', id: 'filtros-de-texto' }, { depth: 3, text: 'grep básico', id: 'grep-basico' }]);
  });
  it('turns [!tip] blockquotes into callouts', () => {
    const tree = { type: 'root', children: [{ type: 'blockquote', children: [{ type: 'paragraph', children: [{ type: 'text', value: '[!warning] Ojo\nresto' }] }] }] };
    remarkCallouts()(tree);
    const quote = tree.children[0] as unknown as { data: { hProperties: { className: string[] } }; children: { children: { value: string }[] }[] };
    expect(quote.data.hProperties.className).toEqual(['callout', 'tone-warning']);
    expect(quote.children[0].children[0].value).toBe('Ojo');
    expect(quote.children[1].children[0].value).toBe('resto');
  });
});

describe('splitSections', () => {
  it('splits at ## outside code fences and keeps the intro as a summary', () => {
    const sections = splitSections('Intro\n\n## Uno\ntexto\n```bash\n## comentario\n```\n### Sub\n\n## `grep` dos\nfin\n');
    expect(sections.map(s => s.title)).toEqual(['Resumen', 'Uno', 'grep dos']);
    expect(sections[1].body).toBe('texto\n```bash\n## comentario\n```\n### Sub\n');
    expect(splitSections('## Solo\nx').map(s => s.title)).toEqual(['Solo']);
    expect(splitSections('')).toHaveLength(1);
  });
});
