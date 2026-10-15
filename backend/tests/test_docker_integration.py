"""Run only with RUN_DOCKER_TESTS=1 and a built linux-lab-environment:local image."""
import json
import os
from pathlib import Path

import pytest

from lab.db import now
from lab.evaluation import evaluate
from lab.runtime import Runtime
from lab.schema import parse_course, course_yaml

pytestmark = pytest.mark.skipif(os.getenv('RUN_DOCKER_TESTS') != '1', reason='Docker acceptance tests require Docker and a built lab image')


async def test_all_starter_solutions_and_lifecycle(db):
    root = Path(__file__).resolve().parents[2]
    course = parse_course((root / 'courses/foundations.yaml').read_text(encoding='utf-8'))
    db.execute("INSERT INTO courses VALUES('foundations',?,?,?,?)", (course.id, course.version, course_yaml(course), now()))
    runtime = Runtime(db)
    env = runtime.environment('foundations')
    free = runtime.environment()
    try:
        await runtime.start(env['id'])
        baseline = await evaluate(runtime, db, env['id'])
        assert sum(r['earned'] for r in baseline['results']) < sum(r['available'] for r in baseline['results'])
        solutions = json.loads((root / 'courses/foundations-solutions.json').read_text())
        for exercise in course.exercises:
            result = runtime.exec(env['id'], solutions[exercise.id], 'learner', 15)
            assert result.code == 0, (exercise.id, result.stderr)
        grades = await evaluate(runtime, db, env['id'])
        for grade in grades['results']:
            assert grade['earned'] == grade['available'], grade
        for executable in ['vi', 'vim', 'nano', 'gedit', 'man', 'info']:
            assert runtime.exec(env['id'], f'command -v {executable}').code == 0
        assert runtime.exec(env['id'], 'man -w ls && info --where coreutils').code == 0
        assert runtime.exec(env['id'], "gedit --version", 'learner').code == 0
        await runtime.stop(env['id']); await runtime.start(env['id'])
        assert runtime.exec(env['id'], 'test -f /home/learner/lab/greet.sh').code == 0
        await runtime.start(free['id'])
        assert runtime.exec(free['id'], 'test ! -e /home/learner/lab/greet.sh').code == 0
        await runtime.recreate(env['id'])
        assert runtime.exec(env['id'], 'test ! -e /home/learner/lab/greet.sh').code == 0
        assert db.results(env['id']) == {}
    finally:
        for row in [runtime.get(env['id']), runtime.get(free['id'])]:
            if row['container_id']:
                runtime.client.containers.get(row['container_id']).remove(force=True)
