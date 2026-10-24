import asyncio
import copy
import json

import httpx
import pytest

from lab.generation import AUTHORING, Generator
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
    # Fail promptly if generation exits before reaching the model (e.g. budget overflow).
    await asyncio.wait_for(entered.wait(), timeout=2)
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


def mock_ollama(monkeypatch, handler):
    original = httpx.AsyncClient
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs))


async def test_thinking_disabled_and_empty_or_truncated_answers_repaired(db, course_data, monkeypatch):
    generator = Generator(db, SourceService(db))
    chat_id = generator.create_chat()
    requests = []

    def handler(request):
        if request.url.path == '/api/tags':
            return httpx.Response(200, json={'models': [{'name': 'qwen3:14b', 'capabilities': ['completion', 'thinking'], 'details': {'context_length': 40960}}]})
        if request.url.path == '/api/show':
            return httpx.Response(200, json={'thinking': {'values': [False, True], 'default': True}})
        payload = json.loads(request.content)
        requests.append(payload)
        if len(requests) == 1:
            return httpx.Response(200, json={'message': {'content': '', 'thinking': 'reasoning'}, 'done_reason': 'stop'})
        if len(requests) == 2:
            return httpx.Response(200, json={'message': {'content': '{'}, 'done_reason': 'length'})
        return httpx.Response(200, json={'message': {'content': json.dumps(course_data)}, 'done_reason': 'stop'})

    mock_ollama(monkeypatch, handler)
    job = generator.start(chat_id, 'Generate a file exercise', 'qwen3:14b', None, 1)
    await generator.tasks[job]
    assert db.one('SELECT state FROM jobs WHERE id=?', (job,))['state'] == 'done'
    assert len(requests) == 3
    for payload in requests:
        assert payload['think'] is False
        assert payload['options']['num_ctx'] == 8192
        assert payload['options']['num_predict'] == 2048
        assert generator.message_tokens(payload['messages']) + 2048 + 512 <= 8192
    assert len(requests[1]['messages']) == len(requests[2]['messages'])


async def test_all_pdfs_default_and_multiple_batches_stay_in_budget(db, course_data, monkeypatch):
    service = SourceService(db)
    digest = 'a' * 64
    db.execute("INSERT INTO sources(id,hash,title,filename,state,created_at) VALUES(?,?,?,?,?,?)", ('theory', digest, 'Permissions', 'theory.pdf', 'ready', '2026'))
    db.execute('INSERT INTO chunks(source_id,page,content) VALUES(?,?,?)', ('theory', 7, 'Linux permissions with chmod. ' * 500))
    generator = Generator(db, service)
    chat_id = generator.create_chat()
    calls = []
    async def models(): return [{'name': 'test'}]
    async def request(model, messages):
        calls.append(copy.deepcopy(messages))
        assert generator.message_tokens(messages) + 2048 + 512 <= 8192
        source_message = next(m['content'] for m in messages if m['content'].startswith('SOURCE EXCERPTS'))
        assert digest in source_message
        candidate = copy.deepcopy(course_data)
        candidate['exercises'][0]['id'] = f'exercise-{len(calls)}'
        candidate['exercises'][0]['sources'] = [{'document_hash': digest, 'title': 'Permissions', 'pages': [7]}]
        return json.dumps(candidate)
    monkeypatch.setattr(generator, 'models', models)
    monkeypatch.setattr(generator, 'request', request)
    job = generator.start(chat_id, 'Generate Linux permissions exercises', 'test', None, 4)
    await generator.tasks[job]
    assert db.one('SELECT state,error FROM jobs WHERE id=?', (job,))['state'] == 'done'
    draft = parse_course(db.one('SELECT draft FROM chats WHERE id=?', (chat_id,))['draft'])
    assert len(draft.exercises) == 4 and len(calls) == 4


async def test_context_overflow_preserves_draft_before_contacting_model(db, monkeypatch):
    generator = Generator(db, SourceService(db))
    chat_id = generator.create_chat()
    previous = 'long draft ' * 5000
    db.execute('UPDATE chats SET draft=? WHERE id=?', (previous, chat_id))
    async def models(): return [{'name': 'test'}]
    async def request(*args): pytest.fail('Oversized drafts must not be sent to Ollama')
    monkeypatch.setattr(generator, 'models', models)
    monkeypatch.setattr(generator, 'request', request)
    job = generator.start(chat_id, 'Revise', 'test', [], 1)
    await generator.tasks[job]
    assert 'context budget' in db.one('SELECT error FROM jobs WHERE id=?', (job,))['error']
    assert db.one('SELECT draft FROM chats WHERE id=?', (chat_id,))['draft'] == previous


@pytest.mark.parametrize('failure,expected', [('timeout', 'timed out'), ('connection', 'Start Ollama'), ('http', 'requires more memory')])
async def test_ollama_failures_have_actionable_messages(db, monkeypatch, failure, expected):
    generator = Generator(db, SourceService(db))
    chat_id = generator.create_chat()
    async def models(): return [{'name': 'test'}]
    monkeypatch.setattr(generator, 'models', models)
    def handler(request):
        if failure == 'timeout': raise httpx.ReadTimeout('', request=request)
        if failure == 'connection': raise httpx.ConnectError('', request=request)
        return httpx.Response(500, json={'error': 'model requires more memory'})
    mock_ollama(monkeypatch, handler)
    job = generator.start(chat_id, 'Generate', 'test', [], 1)
    await generator.tasks[job]
    assert expected in db.one('SELECT error FROM jobs WHERE id=?', (job,))['error']


async def test_model_profile_respects_context_limit_and_named_thinking_levels(db, monkeypatch):
    monkeypatch.setenv('OLLAMA_NUM_CTX', '16384')
    generator = Generator(db, SourceService(db))
    mock_ollama(monkeypatch, lambda request: httpx.Response(200, json={'thinking': {'values': ['low', 'medium', 'high']}}))
    settings = await generator.configure_model({'name': 'reasoner', 'details': {'context_length': 8192}, 'capabilities': ['thinking']})
    assert settings == {'num_ctx': 8192, 'num_predict': 2048, 'think': 'low'}


async def test_new_format_generated_batches_validate_and_include_all_paths(db, monkeypatch):
    generator = Generator(db, SourceService(db))
    chat_id = generator.create_chat()
    example = json.loads(AUTHORING.split('Minimal example:\n', 1)[1])
    exercise = example['exercises'][0]
    # Include a run with an explicit path as well as ones using script.path.
    exercise['evaluations'][0]['checks'].append({'type': 'run', 'path': '/usr/bin/true'})
    calls = []

    def handler(request):
        if request.url.path == '/api/tags':
            return httpx.Response(200, json={'models': [{'name': 'test'}]})
        payload = json.loads(request.content)
        calls.append(payload)
        assert 'evaluations' in payload['format']['$defs']['Exercise']['properties']
        assert 'tasks' not in payload['format']['$defs']['Exercise']['properties']
        assert generator.message_tokens(payload['messages']) + 2048 + 512 <= 8192
        if len(calls) == 2:
            summary = next(m['content'] for m in payload['messages'] if m['content'].startswith('Existing batches'))
            assert exercise['script']['path'] in summary
            assert '/usr/bin/true' in summary
            assert 'null' not in summary
        candidate = copy.deepcopy(example)
        candidate['exercises'][0]['id'] = f'hello-{len(calls)}'
        return httpx.Response(200, json={'message': {'content': json.dumps(candidate)}})

    mock_ollama(monkeypatch, handler)
    job = generator.start(chat_id, 'Write two scripting exercises', 'test', [], 2)
    await asyncio.wait_for(generator.tasks[job], timeout=5)
    result = db.one('SELECT state,error FROM jobs WHERE id=?', (job,))
    assert result['state'] == 'done', result['error']
    draft = db.one('SELECT draft FROM chats WHERE id=?', (chat_id,))['draft']
    assert 'tasks:' not in draft
    course = parse_course(draft)
    assert len(course.exercises) == 2 and len(calls) == 2
    for exercise in course.exercises:
        errors = {r.error for r in exercise.input_requirements}
        assert errors <= {c.requirement for c in exercise.evaluations[0].checks}
        outputs = {o.id: o for o in exercise.output_requirements}
        assert all(outputs[e].stream == 'stderr' and outputs[e].exit_code != 0 for e in errors)
        assert len({outputs[e].exit_code for e in errors}) == len(errors)
