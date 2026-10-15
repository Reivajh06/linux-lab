import pytest
from lab.db import Database


@pytest.fixture
def db(tmp_path):
    return Database(tmp_path)


@pytest.fixture
def course_data():
    return {"schema_version": 1, "id": "sample-course", "version": "1.0", "title": "Sample course", "description": "Practice working with files.", "exercises": [{"id": "make-note", "title": "Create a note", "description": "Create a file containing hello.", "tasks": [{"id": "save-note", "description": "Save the greeting", "points": 5, "checks": [{"type": "content", "path": "/home/learner/note.txt", "value": "hello"}]}], "tips": ["Try nano."]}]}
