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

COURSE_FILES = sorted((Path(__file__).resolve().parents[2] / 'courses').glob('*.yaml'))


def apply_answer(runtime, environment_id, script, user):
    """Run an answer the way the learner's terminal would.

    Runtime.exec caps written files at 1 MB for grading probes; a terminal has no such
    cap, and answers such as `dnf install` write larger files. Some answers also wait
    for crond's next minute, hence the generous timeout.
    """
    result = runtime.container(environment_id).exec_run(
        ['timeout', '300', 'bash', '-lc', 'set -e\n' + script], user=user, demux=True,
        environment={'DISPLAY': ':1', 'HOME': '/home/learner' if user == 'learner' else '/root'},
        workdir='/home/learner')
    stdout, stderr = result.output or (b'', b'')
    return result.exit_code, (stdout or b'').decode(errors='replace'), (stderr or b'').decode(errors='replace')


@pytest.mark.parametrize('course_file', COURSE_FILES, ids=lambda path: path.stem)
async def test_all_course_solutions_and_lifecycle(db, course_file):
    course = parse_course(course_file.read_text(encoding='utf-8'))
    course_key = course_file.stem
    db.execute("INSERT INTO courses(key,course_id,version,yaml,created_at) VALUES(?,?,?,?,?)", (course_key, course.id, course.version, course_yaml(course), now()))
    runtime = Runtime(db)
    env = runtime.environment(course_key)
    free = runtime.environment()
    try:
        await runtime.start(env['id'])
        baseline = await evaluate(runtime, db, env['id'])
        assert sum(r['earned'] for r in baseline['results']) < sum(r['available'] for r in baseline['results'])
        solutions = json.loads(course_file.with_name(course_key + '-solutions.json').read_text(encoding='utf-8'))
        for exercise in course.exercises:
            # Original foundations answers use the learner's home/session;
            # ASO answer scripts also create accounts and set ownership.
            user = 'learner' if course_key == 'foundations' else 'root'
            code, stdout, stderr = apply_answer(runtime, env['id'], solutions[exercise.id], user)
            assert code == 0, (course_key, exercise.id, stdout, stderr)
        grades = await evaluate(runtime, db, env['id'])
        for grade in grades['results']:
            assert grade['earned'] == grade['available'], (course_key, grade)
            assert all(evaluation['status'] == 'pass' for evaluation in grade['tasks']), (course_key, grade)
        if course_key != 'foundations':
            return
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
