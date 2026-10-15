import copy
import json
from pathlib import Path

import bashlex
import pytest
import yaml
from pydantic import ValidationError

from lab.schema import Course, course_yaml, parse_course


def test_yaml_roundtrip_and_schema(course_data):
    course = Course.model_validate(course_data)
    assert parse_course(course_yaml(course)) == course
    assert Course.model_validate_json(course.model_dump_json()) == course
    assert "Exercise" in Course.model_json_schema()["$defs"]


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
