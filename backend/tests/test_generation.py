import asyncio
import copy
import json

import pytest

from lab.generation import Generator
from lab.schema import Course, parse_course
from lab.sources import SourceService


async def test_generation_repairs_validates_saves_without_running_scripts(db, course_data, monkeypatch):
    generator = Generator(db, SourceService(db))
    chat_id = generator.create_chat()
    async def models(): return [{'name': 'local-test'}]
    monkeypatch.setattr(generator, 'models', models)
    attempts = []
    async def request(model, messages):
        attempts.append(messages)
        if len(attempts) == 1: return '{"invalid":true}'
        return json.dumps(course_data)
    monkeypatch.setattr(generator, 'request', request)
    job = generator.start(chat_id, 'Make one exercise', 'local-test', [], 1)
    await generator.tasks[job]
    assert db.one('SELECT state FROM jobs WHERE id=?', (job,))['state'] == 'done'
    saved = db.one('SELECT * FROM chats WHERE id=?', (chat_id,))
    assert len(parse_course(saved['draft']).exercises) == 1
    assert len(attempts) == 2
    assert not db.all('SELECT * FROM environments')
    assert not db.all('SELECT * FROM courses')
    assert 'JSON SCHEMA' in attempts[0][0]['content']
    assert 'Repair' in attempts[1][-1]['content']


async def test_failed_revision_preserves_draft_and_stops_after_two_repairs(db, monkeypatch):
    generator = Generator(db, SourceService(db))
    chat_id = generator.create_chat()
    db.execute('UPDATE chats SET draft=? WHERE id=?', ('saved previous draft', chat_id))
    async def models(): return [{'name': 'test'}]
    calls = []
    async def request(*args): calls.append(1); return '{}'
    monkeypatch.setattr(generator, 'models', models)
    monkeypatch.setattr(generator, 'request', request)
    job = generator.start(chat_id, 'Revise', 'test', [], 1)
    await generator.tasks[job]
    assert len(calls) == 3
    assert db.one('SELECT draft FROM chats WHERE id=?', (chat_id,))['draft'] == 'saved previous draft'
    assert 'two repairs' in db.one('SELECT error FROM jobs WHERE id=?', (job,))['error']


async def test_cancel_and_unavailable_models(db, monkeypatch):
    generator = Generator(db, SourceService(db))
    chat_id = generator.create_chat()
    entered = asyncio.Event()
    async def models(): return [{'name': 'test'}]
    async def request(*args): entered.set(); await asyncio.sleep(60)
    monkeypatch.setattr(generator, 'models', models)
    monkeypatch.setattr(generator, 'request', request)
    job = generator.start(chat_id, 'Generate', 'test', [], 1)
    await entered.wait()
    await generator.cancel(job)
    assert db.one('SELECT state FROM jobs WHERE id=?', (job,))['state'] == 'cancelled'
    missing = generator.start(chat_id, 'Generate', 'missing-model', [], 1)
    await generator.tasks[missing]
    assert 'unavailable' in db.one('SELECT error FROM jobs WHERE id=?', (missing,))['error']


def test_source_citations_cannot_invent_pages(course_data):
    digest = 'a' * 64
    course_data['exercises'][0]['sources'] = [{'document_hash': digest, 'title': 'Theory', 'pages': [9]}]
    course = Course.model_validate(course_data)
    with pytest.raises(ValueError, match='not supplied'): Generator.validate_references(course, [{'document_hash': digest, 'page': 2}])
    Generator.validate_references(course, [{'document_hash': digest, 'page': 9}])
