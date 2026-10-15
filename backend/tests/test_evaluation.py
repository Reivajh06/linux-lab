import asyncio
import json

import pytest

from lab.db import now
from lab.evaluation import check_one, evaluate
from lab.runtime import Execution, Runtime
from lab.schema import CommandCheck, ContentCheck, course_yaml, Course


class Runner:
    def __init__(self, result): self.result = result
    def exec(self, *args, **kwargs): return self.result


def test_command_checks_exit_stdout_and_timeout():
    command = CommandCheck(type="command", script="printf hello", stdout_contains="hello")
    assert check_one(Runner(Execution(0, "hello")), "env", command)["status"] == "pass"
    assert check_one(Runner(Execution(0, "different")), "env", command)["status"] == "fail"
    assert check_one(Runner(Execution(1, "hello")), "env", command)["status"] == "fail"
    assert check_one(Runner(Execution(124, timed_out=True)), "env", command)["status"] == "error"
    command.expected_exit = 3
    assert check_one(Runner(Execution(3, "hello")), "env", command)["status"] == "pass"


def test_probe_failures_are_errors():
    check = ContentCheck(type="content", path="/tmp/no", value="yes")
    assert check_one(Runner(Execution(0, "not JSON")), "env", check)["status"] == "error"
    assert check_one(Runner(Execution(0, '{"error":"unreadable file"}')), "env", check)["status"] == "error"
    assert check_one(Runner(Execution(0, '{"passed":false,"message":"Required path does not exist"}')), "env", check)["status"] == "fail"


class EvaluationRuntime(Runtime):
    def refresh(self, environment_id): return self.get(environment_id)
    def exec(self, environment_id, script, *args, **kwargs):
        if script == "false": return Execution(1, "", "No match")
        if script == "sleep 10": return Execution(124, timed_out=True)
        return Execution(0, "ok")


async def test_scoring_recomputes_and_serializes(db, course_data):
    course_data["exercises"][0]["tasks"] = [
        {"id": "both", "description": "Both checks must pass", "points": 10, "checks": [{"type": "command", "script": "true"}, {"type": "command", "script": "false"}]},
        {"id": "timeout", "description": "A check times out", "points": 7, "checks": [{"type": "command", "script": "sleep 10", "timeout": 1}]},
        {"id": "pass", "description": "This passes", "points": 3, "checks": [{"type": "command", "script": "true"}]},
    ]
    db.execute("INSERT INTO courses VALUES('course','sample-course','1.0',?,?)", (course_yaml(Course.model_validate(course_data)), now()))
    runtime = EvaluationRuntime(db)
    env = runtime.environment("course")
    db.execute("UPDATE environments SET state='running',setup_done=1 WHERE id=?", (env["id"],))
    async with runtime.lock(env["id"]):
        pending = asyncio.create_task(evaluate(runtime, db, env["id"]))
        await asyncio.sleep(.02)
        assert not pending.done()
    result = (await pending)["results"][0]
    assert result["earned"] == 3 and result["available"] == 20
    assert [t["status"] for t in result["tasks"]] == ["fail", "error", "pass"]
    assert db.results(env["id"])["make-note"]["earned"] == 3
    second = await evaluate(runtime, db, env["id"], "make-note")
    assert second["results"][0]["checked_at"] != result["checked_at"]
    with pytest.raises(KeyError): await evaluate(runtime, db, env["id"], "missing-exercise")
