"""Validate shipped collections and their executable acceptance-test answers."""
import json
from pathlib import Path

import pytest
import yaml

from lab.schema import parse_course


COURSES = sorted((Path(__file__).resolve().parents[2] / "courses").glob("*.yaml"))


@pytest.mark.parametrize("path", COURSES, ids=lambda path: path.stem)
def test_collection_contract_and_solutions(path):
    source = path.read_text(encoding="utf-8")
    course = parse_course(source)
    raw = yaml.safe_load(source)
    solutions = json.loads(path.with_name(path.stem + "-solutions.json").read_text(encoding="utf-8"))
    assert set(solutions) == {exercise.id for exercise in course.exercises}
    assert all(isinstance(answer, str) and answer.strip() for answer in solutions.values())
    assert all("evaluations" in exercise and "tasks" not in exercise for exercise in raw["exercises"])

    for exercise in course.exercises:
        assert exercise.description.strip()
        assert exercise.evaluations
        if exercise.script is None:
            continue
        context = f"{path.stem}/{exercise.id}"
        assert exercise.input_requirements, context
        assert exercise.examples, context
        assert all(example.stdout is not None or example.stderr is not None
                   for example in exercise.examples), context
        outputs = exercise.output_requirements
        errors = {output.id for output in outputs if output.exit_code != 0}
        assert errors, context
        assert any(output.exit_code == 0 and output.stream == "stdout" for output in outputs), context
        assert all(output.stream == "stderr" and output.message for output in outputs if output.id in errors), context
        assert len({output.exit_code for output in outputs}) == len(outputs), context
        assert {requirement.error for requirement in exercise.input_requirements} == errors, context
        checks = [check for evaluation in exercise.evaluations for check in evaluation.checks]
        assert all(check.type == "run" for check in checks), context
        assert errors <= {check.requirement for check in checks}, context
        assert any(check.requirement in {output.id for output in outputs if output.exit_code == 0}
                   for check in checks), context
