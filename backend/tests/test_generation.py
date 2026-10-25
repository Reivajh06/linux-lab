import asyncio
import copy
import json

import httpx
import pytest
import yaml

from lab.generation import AUTHORING, EXAMPLE, Generator
from lab.schema import Course, parse_course
from lab.sources import SourceService


def generator_with(db, monkeypatch, *replies):
    """A generator whose model returns each reply in turn as (text, truncated)."""
    generator = Generator(db, SourceService(db))
    calls = []
    async def models(): return [{'name': 'test'}]
    async def request(model, messages, on_progress=None):
        calls.append(copy.deepcopy(messages))
        reply = replies[len(calls) - 1]
        return reply if isinstance(reply, tuple) else (reply, False)
    monkeypatch.setattr(generator, 'models', models)
    monkeypatch.setattr(generator, 'request', request)
    return generator, calls


async def generate(generator, chat_id, prompt='Make exercises', count=1, sources=()):
    job = generator.start(chat_id, prompt, 'test', list(sources), count)
    await asyncio.wait_for(generator.tasks[job], timeout=5)
    return generator.db.one('SELECT * FROM jobs WHERE id=?', (job,))


async def test_yaml_reply_becomes_valid_draft_without_running_scripts(db, monkeypatch):
    fenced = 'Here is your collection:\n```yaml\n' + yaml.safe_dump(EXAMPLE, sort_keys=False) + '```\nEnjoy!'
    generator, calls = generator_with(db, monkeypatch, fenced)
    chat_id = generator.create_chat()
    job = await generate(generator, chat_id, count=3)
    assert job['state'] == 'done' and job['progress'] == 'Draft ready for review', job['error']
    course = parse_course(db.one('SELECT draft FROM chats WHERE id=?', (chat_id,))['draft'])
    assert course.id == 'generated-' + chat_id[:12] and len(course.exercises) == 1
    assert len(calls) == 1 and 'YAML' in calls[0][0]['content'] and 'Fedora' in calls[0][0]['content']
    assert 'Write 3 exercises' in calls[0][-1]['content']
    assert not db.all('SELECT * FROM environments')
    assert not db.all('SELECT * FROM courses')


async def test_invalid_yaml_is_still_saved_with_issues_listed(db, course_data, monkeypatch):
    del course_data['exercises'][0]['title']
    generator, _ = generator_with(db, monkeypatch, yaml.safe_dump(course_data), 'exercises: [unclosed')
    chat_id = generator.create_chat()
    job = await generate(generator, chat_id)
    assert job['state'] == 'done' and 'issues' in job['progress']
    draft = db.one('SELECT draft FROM chats WHERE id=?', (chat_id,))['draft']
    assert 'make-note' in draft
    reply = db.all('SELECT content FROM messages WHERE chat_id=? ORDER BY id', (chat_id,))[-1]['content']
    assert 'exercises.0.title' in reply
    job = await generate(generator, chat_id, 'Revise')
    assert job['state'] == 'done'
    assert db.one('SELECT draft FROM chats WHERE id=?', (chat_id,))['draft'].startswith('exercises: [unclosed')
    assert 'could not be parsed' in db.all('SELECT content FROM messages WHERE chat_id=? ORDER BY id', (chat_id,))[-1]['content']


async def test_truncated_reply_warns_and_revision_includes_previous_draft(db, monkeypatch):
    generator, calls = generator_with(db, monkeypatch, (yaml.safe_dump(EXAMPLE), True))
    chat_id = generator.create_chat()
    db.execute('UPDATE chats SET draft=? WHERE id=?', ('title: previous', chat_id))
    job = await generate(generator, chat_id, 'Add one more')
    assert job['state'] == 'done'
    assert any('Revise this existing YAML draft' in m['content'] and 'title: previous' in m['content'] for m in calls[0])
    assert 'output limit' in db.all('SELECT content FROM messages WHERE chat_id=? ORDER BY id', (chat_id,))[-1]['content']


async def test_cancel_and_unavailable_models(db, monkeypatch):
    generator = Generator(db, SourceService(db))
    chat_id = generator.create_chat()
    entered = asyncio.Event()
    async def models(): return [{'name': 'test'}]
    async def request(*args, **kwargs): entered.set(); await asyncio.sleep(60)
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


def stream(*chunks, reason='stop'):
    lines = [json.dumps({'message': {'content': c}, 'done': False}) for c in chunks]
    lines.append(json.dumps({'message': {'content': ''}, 'done': True, 'done_reason': reason}))
    return httpx.Response(200, content='\n'.join(lines).encode())


async def test_streamed_plain_text_request_disables_thinking_and_fits_budget(db, monkeypatch):
    generator = Generator(db, SourceService(db))
    chat_id = generator.create_chat()
    requests = []
    text = yaml.safe_dump(EXAMPLE, sort_keys=False)

    def handler(request):
        if request.url.path == '/api/tags':
            return httpx.Response(200, json={'models': [{'name': 'qwen3:14b', 'capabilities': ['completion', 'thinking'], 'details': {'context_length': 40960}}]})
        if request.url.path == '/api/show':
            return httpx.Response(200, json={'thinking': {'values': [False, True], 'default': True}})
        payload = json.loads(request.content)
        requests.append(payload)
        return stream(text[:100], text[100:])

    mock_ollama(monkeypatch, handler)
    job = generator.start(chat_id, 'Generate a file exercise', 'qwen3:14b', None, 1)
    await generator.tasks[job]
    result = db.one('SELECT state,error FROM jobs WHERE id=?', (job,))
    assert result['state'] == 'done', result['error']
    assert len(requests) == 1
    payload = requests[0]
    assert payload['stream'] is True and 'format' not in payload and payload['think'] is False
    assert payload['options'] == {'temperature': 0.2, 'num_ctx': 8192, 'num_predict': 4096}
    assert generator.message_tokens(payload['messages']) + 4096 + 512 <= 8192
    assert len(parse_course(db.one('SELECT draft FROM chats WHERE id=?', (chat_id,))['draft']).exercises) == 1


async def test_empty_reply_fails_and_keeps_previous_draft(db, monkeypatch):
    generator = Generator(db, SourceService(db))
    chat_id = generator.create_chat()
    db.execute('UPDATE chats SET draft=? WHERE id=?', ('saved previous draft', chat_id))
    def handler(request):
        if request.url.path == '/api/tags':
            return httpx.Response(200, json={'models': [{'name': 'test'}]})
        return stream('', '  ')
    mock_ollama(monkeypatch, handler)
    job = generator.start(chat_id, 'Revise', 'test', [], 1)
    await generator.tasks[job]
    assert 'no text' in db.one('SELECT error FROM jobs WHERE id=?', (job,))['error']
    assert db.one('SELECT draft FROM chats WHERE id=?', (chat_id,))['draft'] == 'saved previous draft'


async def test_sources_are_sent_and_citations_checked(db, monkeypatch):
    service = SourceService(db)
    digest = 'a' * 64
    db.execute("INSERT INTO sources(id,hash,title,filename,state,created_at) VALUES(?,?,?,?,?,?)", ('theory', digest, 'Permissions', 'theory.pdf', 'ready', '2026'))
    db.execute('INSERT INTO chunks(source_id,page,content) VALUES(?,?,?)', ('theory', 7, 'Linux permissions with chmod. ' * 500))
    cited = copy.deepcopy(EXAMPLE)
    cited['exercises'][0]['sources'] = [{'document_hash': digest, 'title': 'Permissions', 'pages': [7]}]
    generator, calls = generator_with(db, monkeypatch, yaml.safe_dump(cited))
    generator.sources = service
    chat_id = generator.create_chat()
    job = generator.start(chat_id, 'Generate Linux permissions exercises', 'test', None, 4)
    await generator.tasks[job]
    assert db.one('SELECT progress FROM jobs WHERE id=?', (job,))['progress'] == 'Draft ready for review'
    source_message = next(m['content'] for m in calls[0] if m['content'].startswith('SOURCE EXCERPTS'))
    assert digest in source_message
    assert calls[0][-1]['content'].startswith('Generate Linux permissions exercises')


async def test_context_overflow_preserves_draft_before_contacting_model(db, monkeypatch):
    generator = Generator(db, SourceService(db))
    chat_id = generator.create_chat()
    previous = 'long draft ' * 5000
    db.execute('UPDATE chats SET draft=? WHERE id=?', (previous, chat_id))
    async def models(): return [{'name': 'test'}]
    async def request(*args, **kwargs): pytest.fail('Oversized drafts must not be sent to Ollama')
    monkeypatch.setattr(generator, 'models', models)
    monkeypatch.setattr(generator, 'request', request)
    job = generator.start(chat_id, 'Revise', 'test', [], 1)
    await generator.tasks[job]
    assert 'context budget' in db.one('SELECT error FROM jobs WHERE id=?', (job,))['error']
    assert db.one('SELECT draft FROM chats WHERE id=?', (chat_id,))['draft'] == previous


@pytest.mark.parametrize('failure,expected', [('timeout', 'stopped responding'), ('connection', 'Start Ollama'), ('http', 'requires more memory')])
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
    assert settings == {'num_ctx': 8192, 'num_predict': 4096, 'think': 'low'}


def test_authoring_example_is_a_valid_collection():
    assert yaml.safe_dump(EXAMPLE, sort_keys=False, allow_unicode=True) in AUTHORING
    Course.model_validate(EXAMPLE)


async def test_missing_script_path_is_inferred_instead_of_failing(db, monkeypatch):
    two = copy.deepcopy(EXAMPLE)
    del two['exercises'][0]['script']
    fallback = copy.deepcopy(two['exercises'][0])
    fallback['examples'] = []
    fallback['id'] = 'line-counter'
    two['exercises'].append(fallback)
    generator, _ = generator_with(db, monkeypatch, yaml.safe_dump(two))
    chat_id = generator.create_chat()
    job = await generate(generator, chat_id, 'Write scripting exercises', 2)
    assert job['progress'] == 'Draft ready for review', job['error']
    course = parse_course(db.one('SELECT draft FROM chats WHERE id=?', (chat_id,))['draft'])
    assert [e.script.path for e in course.exercises] == ['/home/learner/lab/hello.sh', '/home/learner/lab/line-counter/line-counter.sh']
