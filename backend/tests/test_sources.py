import io
import threading

import pytest
from reportlab.pdfgen.canvas import Canvas
from pypdf import PdfReader, PdfWriter

from lab.sources import SourceService


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
