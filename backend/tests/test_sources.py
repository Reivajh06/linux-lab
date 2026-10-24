import io
import threading

import pytest
from reportlab.pdfgen.canvas import Canvas
from pypdf import PdfReader, PdfWriter

from lab.sources import SourceService, source_text, text_pages


def pdf_bytes(pages):
    buffer = io.BytesIO()
    pdf = Canvas(buffer)
    for text in pages:
        if text: pdf.drawString(40, 750, text)
        pdf.showPage()
    pdf.save()
    return buffer.getvalue()


async def test_text_and_scanned_pages_retrieval_delete(db, monkeypatch):
    service = SourceService(db)
    monkeypatch.setattr(service, 'ocr', lambda path, page: 'Scanned group membership exercises and permissions practice.')
    added = await service.add('theory.pdf', pdf_bytes(['Linux users and permissions: create users with useradd and groups with groupadd.', None]))
    await service.tasks[added['id']]
    row = db.one('SELECT * FROM sources WHERE id=?', (added['id'],))
    assert row['state'] == 'ready' and row['pages'] == 2 and row['ocr_pages'] == 1
    matches = service.retrieve('membership', [added['id']])
    assert matches and int(matches[0]['page']) == 2
    assert matches[0]['document_hash'] == row['hash']
    assert service.retrieve('" OR * syntax', [added['id']])
    with pytest.raises(ValueError, match='already'): await service.add('duplicate.pdf', service.path(added['id']).read_bytes())
    await service.remove(added['id'])
    assert not service.path(added['id']).exists()
    assert not db.all('SELECT * FROM chunks')
    with pytest.raises(ValueError): service.retrieve('users', [added['id']])


async def test_corrupt_and_ocr_failure_are_visible(db, monkeypatch):
    service = SourceService(db)
    with pytest.raises(ValueError, match='valid PDF'): await service.add('not.pdf', b'hello')
    bad = await service.add('broken.pdf', b'%PDF-1.4\nnot a PDF')
    await service.tasks[bad['id']]
    assert db.one('SELECT state FROM sources WHERE id=?', (bad['id'],))['state'] == 'error'
    def no_ocr(*args): raise ValueError('OCR engine failed')
    monkeypatch.setattr(service, 'ocr', no_ocr)
    scan = await service.add('scan.pdf', pdf_bytes([None]))
    await service.tasks[scan['id']]
    row = db.one('SELECT * FROM sources WHERE id=?', (scan['id'],))
    assert row['state'] == 'error' and 'OCR engine failed' in row['warnings']


async def test_password_protected_pdf(db):
    service = SourceService(db)
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.encrypt('secret')
    payload = io.BytesIO(); writer.write(payload)
    source = await service.add('locked.pdf', payload.getvalue())
    await service.tasks[source['id']]
    assert 'Password-protected' in db.one('SELECT error FROM sources WHERE id=?', (source['id'],))['error']


async def test_default_searches_entire_ready_library_with_bounded_excerpts(db):
    import json
    service = SourceService(db)
    ids = []
    for n in range(10):
        source = await service.add(f'theory-{n}.pdf', pdf_bytes([f'Linux topic {n}: ' + ('membership ' if n == 9 else 'files ') * 100]))
        await service.tasks[source['id']]
        ids.append(source['id'])
    # Search can find a document beyond the first eight PDFs without explicit selection.
    matches = service.retrieve('membership', max_bytes=1600)
    assert matches[0]['source_id'] == ids[9]
    assert len(json.dumps(matches, ensure_ascii=False).encode()) <= 1600
    assert service.retrieve('membership', []) == []
    assert service.retrieve('membership', [ids[0]])[0]['source_id'] == ids[0]
    first = service.retrieve('unmatchedquery', max_bytes=12000)
    later = service.retrieve('unmatchedquery', max_bytes=12000, offset=8)
    assert ids[9] in {e['source_id'] for e in later}
    assert first[0]['source_id'] != later[0]['source_id']
    db.execute("UPDATE sources SET state='indexing' WHERE id=?", (ids[9],))
    assert ids[9] not in service.selected_sources()


async def test_retrieval_budget_handles_escaped_unicode_text(db):
    import json
    service = SourceService(db)
    source = await service.add('quoted.pdf', pdf_bytes(['Linux permissions and file ownership exercises for learners.']))
    await service.tasks[source['id']]
    db.execute('UPDATE chunks SET content=? WHERE source_id=?', ('\\"\n\tá' * 1000, source['id']))
    for budget in (256, 600, 1800):
        excerpts = service.retrieve('generic', max_bytes=budget)
        assert len(json.dumps(excerpts, ensure_ascii=False).encode()) <= budget


def test_html_stripping_preserves_structure_and_code():
    html = b'''<!doctype html><html><head><style>body {color:red}</style>
    <script>secret();</script></head><body><h1>Practice &amp; learn</h1>
    <p>First <strong>paragraph</strong>.</p><h2>Commands</h2>
    <ul><li>Use ls</li><li>Use pwd</li></ul><pre>printf 'hello'\n  echo done</pre>
    <code>one\ntwo</code><p>Last<br>line</p></body></html>'''
    text = source_text(html, 'practice.html')
    assert 'color:red' not in text and 'secret' not in text and '<h1>' not in text
    assert 'Practice & learn' in text and 'First paragraph.' in text
    assert 'Use ls' in text and 'Use pwd' in text
    assert '\n' in text[text.index('Use ls') + len('Use ls'):text.index('Use pwd')]
    assert "printf 'hello'\n  echo done" in text
    assert 'one\ntwo' in text and 'Last\nline' in text
    assert source_text(b'<pre><code>  echo one\n    echo two</code></pre>', 'code.html') == '  echo one\n    echo two'


@pytest.mark.parametrize('filename,data,expected', [
    ('utf8.md', b'\xef\xbb\xbfPr\xc3\xa1ctica\n\nLinux', 'Práctica\n\nLinux'),
    ('windows.txt', b'Pr\xe1ctica \x93Linux\x94', 'Práctica “Linux”'),
    ('latin.txt', b'Pr\xe1ctica \x81', 'Práctica \x81'),
    ('plain.htm', b'Pr\xe1ctica\n  ls -l\n\nUse grep', 'Práctica\n  ls -l\n\nUse grep'),
    ('notes.HTML', b'<h1>Pr\xe1ctica</h1><p>Permisos</p>', 'Práctica\n\nPermisos'),
])
def test_text_encoding_fallback_and_plain_htm(filename, data, expected):
    assert source_text(data, filename) == expected


def test_text_paging_at_paragraph_boundaries_and_long_paragraphs():
    paragraphs = [str(n) + 'x' * 1399 for n in range(5)]
    pages = text_pages('\n\n'.join(paragraphs))
    assert pages == ['\n\n'.join(paragraphs[:2]), '\n\n'.join(paragraphs[2:4]), paragraphs[4]]
    for text in ('word ' * 2000, 'x' * 7001, 'line\n' * 1600):
        pages = text_pages(text)
        assert all(0 < len(page) <= 3000 for page in pages)
        assert ''.join(''.join(p.split()) for p in pages) == ''.join(text.split())


@pytest.mark.parametrize('extension', ['.txt', '.md', '.htm', '.html'])
async def test_text_sources_index_search_retry_and_remove_without_ocr(db, monkeypatch, extension):
    service = SourceService(db)
    def no_ocr(*args): pytest.fail('Text sources must never invoke OCR')
    monkeypatch.setattr(service, 'ocr', no_ocr)
    paragraphs = [f'Paragraph {n}: ' + 'Linux permissions ' * 75 for n in range(6)]
    raw = '\n\n'.join(paragraphs)
    if extension == '.html':
        raw = '<h1>Practice sheet</h1>' + ''.join(f'<p>{p}</p>' for p in paragraphs)
    added = await service.add('practice' + extension, raw.encode())
    await service.tasks[added['id']]
    row = db.one('SELECT * FROM sources WHERE id=?', (added['id'],))
    pages = db.all('SELECT * FROM pages WHERE source_id=? ORDER BY page', (added['id'],))
    assert row['state'] == 'ready' and row['ocr_pages'] == 0
    assert row['pages'] == row['indexed_pages'] == len(pages) > 1
    assert all(page['ocr'] == 0 and len(page['content']) <= 3000 for page in pages)
    assert [page['page'] for page in pages] == list(range(1, len(pages) + 1))
    assert service.retrieve('permissions', [added['id']])[0]['document_hash'] == row['hash']
    service.start(added['id'])
    await service.tasks[added['id']]
    assert len(db.all('SELECT * FROM pages WHERE source_id=?', (added['id'],))) == len(pages)
    path = service.path(added['id'])
    await service.remove(added['id'])
    assert not path.exists() and not db.all('SELECT * FROM pages') and not db.all('SELECT * FROM chunks')


async def test_source_upload_validation(db):
    service = SourceService(db)
    with pytest.raises(ValueError, match='PDF, TXT'):
        await service.add('program.exe', b'not supported')
    with pytest.raises(ValueError, match='25 MB'):
        await service.add('big.txt', b'x' * (25 * 1024 * 1024 + 1))
    empty = await service.add('empty.html', b'<style>hidden</style><script>hidden</script>')
    await service.tasks[empty['id']]
    assert db.one('SELECT state,error FROM sources WHERE id=?', (empty['id'],))['state'] == 'error'
