import asyncio
import base64
import json

import pytest

from lab.db import now
from lab.evaluation import check_one, evaluate, run_case
from lab.runtime import Execution, Runtime
from lab.schema import CommandCheck, ContentCheck, RunCheck, StreamExpectation, course_yaml, Course


class Runner:
    def __init__(self, result): self.result = result
    def exec(self, *args, **kwargs): return self.result


class CaseRuntime:
    """Return separate results for the executable probe, program, and reference."""
    def __init__(self, *results):
        self.results = iter(results)
        self.calls = []

    def exec(self, *args):
        self.calls.append(args)
        return next(self.results)


def test_run_case_pass_and_wrong_exit():
    check = RunCheck(type='run', path='/home/learner/count.sh', args=['a'],
                     stdout=StreamExpectation(match='exact', value='42\n'),
                     stderr=StreamExpectation(match='empty'))
    runtime = CaseRuntime(Execution(0), Execution(0, '42\n'))
    result = run_case(runtime, 'env', check)
    assert result['status'] == 'pass' and result['expected_exit'] == 0
    assert runtime.calls[1] == ('env', 'cd /home/learner && /home/learner/count.sh a </dev/null', 'learner', 10)
    result = run_case(CaseRuntime(Execution(0), Execution(2, '42\n')), 'env', check)
    assert result['status'] == 'fail' and 'exit code 2, expected 0' in result['message']


@pytest.mark.parametrize('code,message', [(3, 'does not exist'), (4, 'not executable')])
def test_run_case_missing_or_not_executable(code, message):
    runtime = CaseRuntime(Execution(code))
    result = run_case(runtime, 'env', RunCheck(type='run', path='/home/learner/missing.sh'))
    assert result['status'] == 'fail' and message in result['message']
    assert len(runtime.calls) == 1


def test_run_case_from_command_reference():
    check = RunCheck(type='run', path='/home/learner/count.sh', cwd='/tmp/input files',
                     stdout=StreamExpectation(match='lines', from_command="printf '42\\n'"))
    runtime = CaseRuntime(Execution(0), Execution(0, '42  \n'), Execution(0, '42\n'))
    result = run_case(runtime, 'env', check)
    assert result['status'] == 'pass' and result['expected_stdout'] == '42\n'
    assert runtime.calls[2] == ('env', "cd '/tmp/input files' && { printf '42\\n'\n}", 'learner', 10)
    result = run_case(CaseRuntime(Execution(0), Execution(0, '41\n'), Execution(0, '42\n')), 'env', check)
    assert result['status'] == 'fail' and 'stdout' in result['message']


@pytest.mark.parametrize('code,stdout,stderr,status', [
    (2, '', 'One letter required\n', 'pass'),
    (0, '', 'One letter required\n', 'fail'),
    (2, 'unexpected result', 'One letter required\n', 'fail'),
    (2, '', '', 'fail'), (2, '', '  \n', 'fail'),
])
def test_run_case_requirement_stderr_defaults(course_data, code, stdout, stderr, status):
    data = course_data['exercises'][0]
    data['script'] = {'path': '/home/learner/count.sh'}
    data['output_requirements'] = [{'id': 'letter', 'description': 'One letter', 'exit_code': 2, 'stream': 'stderr', 'message': 'One letter required'}]
    data['tasks'][0]['checks'] = [{'type': 'run', 'args': ['ab'], 'requirement': 'letter'}]
    exercise = Course.model_validate(course_data).exercises[0]
    result = run_case(CaseRuntime(Execution(0), Execution(code, stdout, stderr)), 'env', exercise.evaluations[0].checks[0], exercise)
    assert result['status'] == status and result['expected_exit'] == 2
    assert result['command'] == '/home/learner/count.sh ab'


def test_run_case_stdin_piping_and_argument_quoting():
    stdin = "a'b\n$(touch /tmp/not-run)\ná\n"
    check = RunCheck(type='run', path='/home/learner/my script.sh', args=['a b', '$(false)', ''], stdin=stdin)
    runtime = CaseRuntime(Execution(0), Execution(0))
    assert run_case(runtime, 'env', check)['status'] == 'pass'
    encoded = base64.b64encode(stdin.encode()).decode()
    assert runtime.calls[1][1] == f"cd /home/learner && printf %s {encoded} | base64 -d | '/home/learner/my script.sh' 'a b' '$(false)' ''"


def test_run_case_timeout():
    check = RunCheck(type='run', path='/home/learner/loop.sh', timeout=1)
    runtime = CaseRuntime(Execution(0), Execution(124, stderr='partial', timed_out=True))
    result = run_case(runtime, 'env', check)
    assert result['status'] == 'fail' and 'Timed out after 1s' in result['message']
    assert result['stderr'] == 'partial' and runtime.calls[1][-1] == 1


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
    db.execute("INSERT INTO courses(key,course_id,version,yaml,created_at) VALUES('course','sample-course','1.0',?,?)", (course_yaml(Course.model_validate(course_data)), now()))
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
