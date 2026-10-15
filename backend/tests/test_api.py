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
        assert len(client.get('/api/courses').json()) == 2  # starter plus import
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
