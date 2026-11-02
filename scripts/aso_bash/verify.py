"""Check the ASO Bash courses in real lab containers and record their example output.

For each course: a do-nothing stub must earn no points, the solutions must earn all of
them on two consecutive evaluations, and every example is executed to capture its output.
Run it, then rerun scripts/build_aso_bash.py to bake the captured examples into the YAML.
"""
import asyncio
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))
os.environ["LAB_DATA_DIR"] = tempfile.mkdtemp(prefix="aso-bash-verify-")

from aso_bash.framework import EXAMPLES
from build_aso_bash import PRACTICES
from lab.db import Database, now
from lab.evaluation import evaluate
from lab.runtime import Runtime
from lab.schema import Course, course_yaml


def failures(grades):
    return [f"{r['exercise_id']}/{t['id']}: " + "; ".join(str(c.get("message")) + " | out=" + repr(c.get("stdout", ""))[:300] + " err=" + repr(c.get("stderr", ""))[:200] for c in t["checks"] if c["status"] != "pass")
            for r in grades["results"] for t in r["tasks"] if t["status"] != "pass"]


async def verify(practice, db, runtime):
    course = Course.model_validate(practice.course())
    key = f"p{practice.slug}"
    db.execute("INSERT INTO courses VALUES(?,?,?,?,?)", (key, course.id, course.version, course_yaml(course), now()))
    env = runtime.environment(key)
    problems, captured = [], {}
    try:
        await runtime.start(env["id"])
        for exercise in course.exercises:
            path = exercise.script.path
            runtime.exec(env["id"], f"printf '#!/bin/bash\\nexit 0\\n' > {path}; chmod 755 {path}; chown learner:learner {path}")
        stub = await evaluate(runtime, db, env["id"])
        for result in stub["results"]:
            for task in result["tasks"]:
                if task["status"] == "pass":
                    problems.append(f"STUB PASSES {result['exercise_id']}/{task['id']}")
        for exercise in course.exercises:
            result = runtime.exec(env["id"], "set -e\n" + practice.solutions[exercise.id], "root", 30)
            if result.code != 0:
                problems.append(f"SOLUTION INSTALL {exercise.id}: {result.stderr}")
        for name, specs in practice.example_specs.items():
            for index, spec in enumerate(specs):
                if spec.get("prepare"):
                    runtime.exec(env["id"], spec["prepare"], "root", 15)
                path = next(e.script.path for e in course.exercises if e.id == name)
                result = runtime.exec(env["id"], f"cd /home/learner && {path} </dev/null {spec['args']}", spec.get("user") or "learner", 20)
                captured.setdefault(name, {})[str(index)] = dict(stdout=result.stdout[:9000], stderr=result.stderr[:2000], exit_code=result.code)
        for attempt in (1, 2):
            grades = await evaluate(runtime, db, env["id"])
            problems += [f"SOLUTION FAILS (run {attempt}) {line}" for line in failures(grades)]
        return problems, captured
    finally:
        row = runtime.get(env["id"])
        if row["container_id"]:
            runtime.client.containers.get(row["container_id"]).remove(force=True)
        await runtime.delete(env["id"])


async def main():
    only = set(sys.argv[1:])
    db, runtime = Database(), None
    runtime = Runtime(db)
    examples = json.loads(EXAMPLES.read_text(encoding="utf-8")) if EXAMPLES.exists() else {}
    status = 0
    for practice in PRACTICES:
        if only and practice.slug not in only:
            continue
        problems, captured = await verify(practice, db, runtime)
        examples[practice.slug] = captured
        print(f"== {practice.number}: {len(practice.exercises)} exercises, {len(problems)} problems", flush=True)
        for problem in problems:
            print("  " + problem, flush=True)
            status = 1
    EXAMPLES.write_text(json.dumps(examples, indent=1, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return status


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
