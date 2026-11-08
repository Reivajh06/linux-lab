from fastapi.testclient import TestClient

from lab.main import create_app
from lab.notebook import Notebook, parse_page
from test_api import NoDocker


def write(directory, slug, body, title='Procesos'):
    (directory / f'{slug}.md').write_text(f'---\ntitle: {title}\nfolder: Prácticas ASO\norder: 31\ntags: [ps]\n---\n{body}', encoding='utf-8')


def test_parse_page_reads_frontmatter():
    page = parse_page('---\ntitle: Uno\norder: 2\ntags: [a, b]\n---\n\n## Hola\n', 'uno')
    assert page['title'] == 'Uno' and page['ord'] == 2 and page['folder'] is None and page['body'] == '## Hola\n'
    assert parse_page('Sin cabecera', 'x')['title'] == 'x'


def test_shipped_pages_refresh_until_the_learner_edits_them(db, tmp_path):
    notes = tmp_path / 'notebook'
    notes.mkdir()
    write(notes, 'aso-3-1', 'v1')
    book = Notebook(db, notes)
    book.seed()
    [page] = book.list()
    assert page['shipped'] and not page['edited'] and page['folder'] == 'Prácticas ASO' and page['tags'] == ['ps']
    write(notes, 'aso-3-1', 'v2')
    book.seed()
    assert book.get(page['id'])['body'] == 'v2\n'
    book.update(page['id'], 'Mis procesos', 'Prácticas ASO', 'mío')
    write(notes, 'aso-3-1', 'v3')
    book.seed()
    assert book.get(page['id'])['body'] == 'mío' and book.get(page['id'])['edited']
    restored = book.restore(page['id'])
    assert restored['body'] == 'v3\n' and restored['title'] == 'Procesos' and not restored['edited']


def test_notes_api(db):
    with TestClient(create_app(db, NoDocker(db))) as client:
        headers = {'X-Lab-Token': client.get('/api/config').json()['token']}
        created = client.post('/api/notes', headers=headers, json={'title': ' Repaso ', 'folder': '', 'body': '# zqxhola'})
        assert created.status_code == 201
        page = created.json()
        assert page['title'] == 'Repaso' and page['folder'] is None and not page['shipped']
        assert any(p['id'] == page['id'] and 'body' not in p for p in client.get('/api/notes').json())
        assert [p['id'] for p in client.get('/api/notes', params={'q': 'ZQXHOLA rep'}).json()] == [page['id']]
        assert client.get('/api/notes', params={'q': '100%_'}).json() == []
        updated = client.put(f"/api/notes/{page['id']}", headers=headers, json={'title': 'Repaso', 'folder': 'Mis notas', 'body': 'texto'}).json()
        assert updated['folder'] == 'Mis notas' and updated['body'] == 'texto'
        assert client.post(f"/api/notes/{page['id']}/restore", headers=headers).status_code == 422
        assert client.delete(f"/api/notes/{page['id']}", headers=headers).json() == {'deleted': True}
        assert client.get(f"/api/notes/{page['id']}").status_code == 404
