import copy
import json
from pathlib import Path

import bashlex
import pytest
import yaml
from pydantic import ValidationError

from lab.schema import Course, StreamExpectation, course_yaml, parse_course


def test_yaml_roundtrip_and_schema(course_data):
    course = Course.model_validate(course_data)
    assert parse_course(course_yaml(course)) == course
    assert Course.model_validate_json(course.model_dump_json()) == course
    assert "Exercise" in Course.model_json_schema()["$defs"]


def test_legacy_tasks_export_as_evaluations(course_data):
    course = Course.model_validate(course_data)
    exercise = course.exercises[0]
    assert exercise.tasks is exercise.evaluations
    exported = yaml.safe_load(course_yaml(course))['exercises'][0]
    assert exported['evaluations'] == exercise.model_dump(exclude_none=True)['evaluations']
    assert exported['evaluations'][0]['id'] == course_data['exercises'][0]['tasks'][0]['id']
    assert 'tasks' not in exported
    assert Course.model_validate_json(course.model_dump_json()) == course


@pytest.mark.parametrize('change,match', [
    ('both-keys', 'not both'), ('unknown-error', 'unknown output'),
    ('zero-error', 'must not be 0'), ('run-no-path', 'script.path'),
])
def test_requirement_and_run_contract(course_data, change, match):
    exercise = course_data['exercises'][0]
    if change == 'both-keys':
        exercise['evaluations'] = copy.deepcopy(exercise['tasks'])
    elif change in ('unknown-error', 'zero-error'):
        exercise['input_requirements'] = [{'description': 'One argument', 'error': 'arity'}]
        exercise['output_requirements'] = [] if change == 'unknown-error' else [
            {'id': 'arity', 'description': 'Invalid count', 'exit_code': 0, 'stream': 'stderr'}]
    else:
        exercise['tasks'][0]['checks'] = [{'type': 'run'}]
    with pytest.raises(ValidationError, match=match):
        Course.model_validate(course_data)


@pytest.mark.parametrize('match', ['exact', 'lines', 'contains', 'regex'])
def test_stream_expectation_operand_rules(match):
    assert StreamExpectation(match=match, value='hello').value == 'hello'
    with pytest.raises(ValidationError): StreamExpectation(match=match)
    with pytest.raises(ValidationError): StreamExpectation(match=match, value='hello', from_command='printf hello')
    if match == 'regex':
        with pytest.raises(ValidationError): StreamExpectation(match=match, from_command='printf hello')
        with pytest.raises(ValidationError): StreamExpectation(match=match, value='[')
    else:
        assert StreamExpectation(match=match, from_command='printf hello').from_command == 'printf hello'
        assert StreamExpectation(match=match, value='').value == ''
        with pytest.raises(ValidationError): StreamExpectation(match=match, from_command='if then')


@pytest.mark.parametrize('match', ['empty', 'nonempty'])
def test_stream_expectation_no_operand_modes(match):
    assert StreamExpectation(match=match).match == match
    for operand in ({'value': ''}, {'from_command': 'true'}, {'value': '', 'from_command': 'true'}):
        with pytest.raises(ValidationError): StreamExpectation(match=match, **operand)


@pytest.mark.parametrize("change", ["duplicate-exercise", "duplicate-task", "unknown-check", "negative-points", "float-points", "bad-shell", "bad-regex", "unknown-field", "no-checks"])
def test_reject_invalid(course_data, change):
    task = course_data["exercises"][0]["tasks"][0]
    if change == "duplicate-exercise": course_data["exercises"].append(copy.deepcopy(course_data["exercises"][0]))
    if change == "duplicate-task": course_data["exercises"][0]["tasks"].append(copy.deepcopy(task))
    if change == "unknown-check": task["checks"][0]["type"] = "invented"
    if change == "negative-points": task["points"] = -1
    if change == "float-points": task["points"] = 2.5
    if change == "bad-shell": task["checks"] = [{"type": "command", "script": "if then"}]
    if change == "bad-regex": task["checks"][0].update(match="regex", value="[")
    if change == "unknown-field": course_data["mystery"] = 42
    if change == "no-checks": task["checks"] = []
    with pytest.raises(ValidationError): Course.model_validate(course_data)


@pytest.mark.parametrize("content", ["id: one\nid: two", "a: &x hello\nb: *x", "!!python/object/apply:os.system ['echo no']", "version: [unterminated"])
def test_reject_yaml_hazards(content):
    with pytest.raises((ValueError, yaml.YAMLError)): parse_course(content)


def test_starter_course_is_complete():
    root = Path(__file__).resolve().parents[2]
    course = parse_course((root / "courses/foundations.yaml").read_text(encoding="utf-8"))
    solutions = json.loads((root / "courses/foundations-solutions.json").read_text())
    assert len(course.exercises) == 30
    assert set(solutions) == {e.id for e in course.exercises}
    assert {"editor-vi", "editor-vim", "editor-nano", "editor-gedit", "read-manuals"}.issubset(solutions)
    for solution in solutions.values(): bashlex.parse(solution)
