import threading

import pytest
import yaml
from fastapi.testclient import TestClient

from lab.main import create_app
from lab.runtime import Runtime


class NoDocker(Runtime):
    def health(self): return {"available": False, "image_ready": False, "message": "Docker not installed"}


def test_import_library_export_and_local_guard(db, course_data):
    app = create_app(db, NoDocker(db))
    with TestClient(app) as client:
        config = client.get('/api/config').json()
        assert not config['docker']['available']
        headers = {'X-Lab-Token': config['token']}
        initial_count = len(client.get('/api/courses').json())
        assert client.post('/api/courses/import', json={'yaml': yaml.safe_dump(course_data)}).status_code == 403
        assert client.post('/api/courses/import', headers={**headers, 'Origin': 'https://evil.example'}, json={'yaml': yaml.safe_dump(course_data)}).status_code == 403
        assert client.get('/api/config', headers={'Host': 'evil.example'}).status_code == 400
        response = client.post('/api/courses/import', headers=headers, json={'yaml': yaml.safe_dump(course_data)})
        assert response.status_code == 201
        key = response.json()['key']
        assert client.post('/api/courses/import', headers=headers, json={'yaml': yaml.safe_dump(course_data)}).status_code == 409
        detail = client.get('/api/courses/' + key).json()
        assert detail['environment']['state'] == 'new'
        exported = client.get(f'/api/courses/{key}/export')
        assert yaml.safe_load(exported.text)['id'] == course_data['id']
        assert len(client.get('/api/courses').json()) == initial_count + 1
        assert client.get('/api/courses/no-such-course').status_code == 404
        invalid = client.post('/api/courses/validate', headers=headers, json={'yaml': 'id: one\nid: two'})
        assert invalid.status_code == 422 and 'Duplicate' in invalid.text
        env = client.post('/api/environments', headers=headers, json={}).json()
        assert env['course_key'] is None and env['id'] != detail['environment']['id']


def test_drafts_persist_and_reject_concurrent_edits(db):
    with TestClient(create_app(db, NoDocker(db))) as client:
        headers = {'X-Lab-Token': client.get('/api/config').json()['token']}
        chat_id = client.post('/api/chats', headers=headers).json()['id']
        saved = client.put(f'/api/chats/{chat_id}/draft', headers=headers, json={'yaml': 'unfinished draft'})
        assert saved.status_code == 200
        assert client.get(f'/api/chats/{chat_id}').json()['draft'] == 'unfinished draft'
        assert client.get('/api/chats').json()[0]['id'] == chat_id


@pytest.mark.parametrize('extension', ['txt', 'md', 'htm', 'html'])
def test_text_source_upload_page_and_safe_preview(db, monkeypatch, extension):
    app = create_app(db, NoDocker(db))
    service = app.state.sources
    monkeypatch.setattr(service, 'start', lambda source_id: service.index(source_id, threading.Event()))
    content = b'Pr\xe1ctica\n\nLinux permissions'
    if extension in ('htm', 'html'):
        content = b'<h1>Pr\xe1ctica</h1><script>alert(1)</script><p>Linux permissions</p>'
    with TestClient(app) as client:
        headers = {'X-Lab-Token': client.get('/api/config').json()['token']}
        response = client.post('/api/sources', headers=headers, files={'file': ('practice.' + extension, content)})
        assert response.status_code == 201, response.text
        source = response.json()
        assert source['state'] == 'ready' and source['ocr_pages'] == 0
        page = client.get(f"/api/sources/{source['id']}/pages/1")
        assert page.status_code == 200 and 'Práctica' in page.json()['content']
        preview = client.get(f"/api/sources/{source['id']}/pdf")
        assert preview.status_code == 200 and preview.headers['content-type'].startswith('text/plain')
        assert 'Práctica' in preview.text and 'Linux permissions' in preview.text
        assert '<script>' not in preview.text and 'alert(1)' not in preview.text
        assert client.post('/api/sources', headers=headers, files={'file': ('bad.exe', b'bad')}).status_code == 422


def test_chats_can_be_deleted_with_their_messages(db):
    app = create_app(db, NoDocker(db))
    with TestClient(app) as client:
        headers = {'X-Lab-Token': client.get('/api/config').json()['token']}
        chat_id = client.post('/api/chats', headers=headers).json()['id']
        db.message(chat_id, 'user', 'hello')
        assert client.delete(f'/api/chats/{chat_id}').status_code == 403
        assert client.delete(f'/api/chats/{chat_id}', headers=headers).json() == {'deleted': True}
        assert client.get(f'/api/chats/{chat_id}').status_code == 404
        assert db.all('SELECT * FROM messages') == []
        assert client.delete(f'/api/chats/{chat_id}', headers=headers).status_code == 404


def test_environment_assistant_streams_without_storing(db, monkeypatch):
    app = create_app(db, NoDocker(db))
    generator = app.state.generator
    async def assist(model, context, history):
        assert 'free practice' in context and history[-1]['content'] == 'What is ls?'
        async def reply():
            yield 'It lists '
            yield 'files.'
        return reply()
    monkeypatch.setattr(generator, 'assist', assist)
    with TestClient(app) as client:
        headers = {'X-Lab-Token': client.get('/api/config').json()['token']}
        env = client.post('/api/environments', headers=headers, json={}).json()
        body = {'model': 'test', 'messages': [{'role': 'user', 'content': 'What is ls?'}]}
        response = client.post(f"/api/environments/{env['id']}/assistant", headers=headers, json=body)
        assert response.status_code == 200 and response.text == 'It lists files.'
        assert client.post('/api/environments/missing/assistant', headers=headers, json=body).status_code == 404
        wrong = {'model': 'test', 'messages': [{'role': 'assistant', 'content': 'Hi'}]}
        assert client.post(f"/api/environments/{env['id']}/assistant", headers=headers, json=wrong).status_code == 422
        assert db.all('SELECT * FROM chats') == []


def test_collections_are_grouped_into_folders(db, course_data):
    with TestClient(create_app(db, NoDocker(db))) as client:
        headers = {'X-Lab-Token': client.get('/api/config').json()['token']}
        listed = {c['id']: c for c in client.get('/api/courses').json()}
        assert listed['aso-bash-p1-2']['folder'] == 'ASO Bash'
        assert listed['linux-foundations']['folder'] is None
        key = client.post('/api/courses/import', headers=headers, json={'yaml': yaml.safe_dump({**course_data, 'folder': 'Mine'})}).json()['key']
        folder = lambda: next(c['folder'] for c in client.get('/api/courses').json() if c['key'] == key)
        assert folder() == 'Mine'
        assert client.patch(f'/api/courses/{key}', headers=headers, json={'folder': ' Repaso '}).json()['folder'] == 'Repaso'
        assert folder() == 'Repaso'
        client.patch(f'/api/courses/{key}', headers=headers, json={'folder': ''})
        assert folder() is None
        assert client.patch('/api/courses/missing', headers=headers, json={'folder': 'x'}).status_code == 404
