"""Compact authoring helpers for the ASO Bash courses.

`@D` expands to the practice's working directory and `@S` to the exercise's script.
Every script exercise follows the contract enforced by backend/tests/test_courses.py.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXAMPLES = HERE / "examples.json"


def ok(args=(), ref=None, val=None, has=None, rx=None, prepare=None, stdin=None, cwd=None, user=None, err="empty", timeout=None):
    """A successful run. `ref` is a live reference command, compared line by line."""
    stdout = (dict(match="lines", from_command=ref) if ref is not None else
              dict(match="exact", value=val) if val is not None else
              dict(match="contains", value=has) if has is not None else
              dict(match="regex", value=rx) if rx is not None else None)
    return dict(kind="ok", args=list(args), stdout=stdout, prepare=prepare, stdin=stdin, cwd=cwd, user=user, err=err, timeout=timeout)


def probe(code, prepare=None, user="root", timeout=None):
    """Inspect the system with Bash after (or by) running the script: `$S` is its path."""
    return dict(kind="probe", code=code, prepare=prepare, user=user, timeout=timeout)


def T(id, description, *cases, points=6):
    return dict(id=id, description=description, cases=list(cases), points=points)


def E(id, code, requirement, message, *cases, eg=True, partial=None):
    """A rejected input. Cases are argument lists, or dicts with args/msg/prepare/user/ref.

    `partial` documents the stdout of errors that keep processing the remaining arguments.
    """
    return dict(id=id, code=code, requirement=requirement, message=message, cases=list(cases), eg=eg, partial=partial)


def eg(command="", note=None, prepare=None, user=None):
    return dict(args=command, note=note, prepare=prepare, user=user)


class Practice:
    def __init__(self, number, title, intro, setup="", document=None):
        self.number, self.title, self.intro, self.document = number, title, intro, document
        self.slug = number.replace(".", "-")
        self.base = f"/home/learner/aso/p{number.replace('.', '')}"
        self.setup = f"set -e\ninstall -d -o learner -g learner {self.base}\n{setup}"
        self.exercises, self.solutions, self.example_specs = [], {}, {}

    def add(self, name, title, task, *, usage="", cmds, structs="", detail="", success, tests, errors, examples=(), tips=(), pages=(), solution, root=False):
        path = f"{self.base}/{name}.sh"
        fill = lambda text: text.replace("@S", path).replace("@D", self.base) if isinstance(text, str) else text
        default_user = "root" if root else None

        def run(case, requirement=None, message=None, default_stdout=None):
            check = dict(type="run", args=[fill(a) for a in case.get("args", [])])
            if requirement:
                check["requirement"] = requirement
            user = case.get("user") or default_user
            if user:
                check["user"] = user
            for field in ("stdin", "cwd", "timeout"):
                if case.get(field) is not None:
                    check[field] = fill(case[field])
            if case.get("prepare"):
                check["prepare"] = fill(case["prepare"])
            if case.get("stdout"):
                check["stdout"] = {k: fill(v) for k, v in case["stdout"].items()}
            elif default_stdout:
                check["stdout"] = default_stdout
            if message is not None:
                check["stderr"] = dict(match="exact", value=fill(message))
            elif case.get("err") == "empty":
                check["stderr"] = dict(match="empty")
            return check

        evaluations = []
        for test in tests:
            checks = []
            for case in test["cases"]:
                if case["kind"] == "probe":
                    check = dict(type="run", path="/usr/bin/bash", args=["-c", f"S={path}\nD={self.base}\n" + fill(case["code"])], user=case["user"], requirement="correcto")
                    if case.get("prepare"):
                        check["prepare"] = fill(case["prepare"])
                    if case.get("timeout"):
                        check["timeout"] = case["timeout"]
                    checks.append(check)
                else:
                    checks.append(run(case, "correcto"))
            evaluations.append(dict(id=test["id"], description=fill(test["description"]), points=test["points"], checks=checks))

        specs = [dict(eg_item, args=fill(eg_item["args"]), prepare=fill(eg_item["prepare"])) for eg_item in examples]
        for error in errors:
            checks = []
            for case in error["cases"]:
                case = case if isinstance(case, dict) else dict(args=case)
                default = dict(match="lines", from_command=fill(case["ref"])) if case.get("ref") else None
                checks.append(run(case, error["id"], case.get("msg", error["message"]), default))
            evaluations.append(dict(id=f"error-{error['id']}", description=fill(f"Rechaza la entrada: {error['requirement']}"), points=2, checks=checks))
            if error["eg"]:
                first = error["cases"][0]
                first = first if isinstance(first, dict) else dict(args=first)
                import shlex
                specs.append(dict(args=" ".join(shlex.quote(fill(a)) for a in first.get("args", [])), note=None, prepare=fill(first.get("prepare")), user=first.get("user") or default_user))

        body = [fill(task.strip())]
        body.append(f"**Comandos a practicar:** {cmds}")
        if structs:
            body.append(f"**Estructuras de Bash:** {structs}")
        if detail:
            body.append(f"**Detalle importante:** {fill(detail)}")
        captured = json.loads(EXAMPLES.read_text(encoding="utf-8")) if EXAMPLES.exists() else {}
        rendered = []
        for index, spec in enumerate(specs):
            seen = captured.get(self.slug, {}).get(name, {}).get(str(index), dict(stdout="", stderr="", exit_code=0))
            rendered.append(dict(command=f"{path} {spec['args']}".rstrip(), stdout=seen["stdout"], stderr=seen["stderr"], exit_code=seen["exit_code"], **({"description": fill(spec["note"])} if spec.get("note") else {})))
        self.example_specs[name] = specs

        exercise = dict(
            id=name, title=title, description="\n\n".join(body),
            script=dict(path=path, usage=f"{name}.sh {usage}".rstrip()),
            input_requirements=[dict(description=fill(error["requirement"]), error=error["id"]) for error in errors],
            output_requirements=[dict(id="correcto", description=fill(success), exit_code=0, stream="stdout")] + [
                dict(id=error["id"], description=fill(error["partial"] or "Mensaje en stderr; stdout vacío."), exit_code=error["code"], stream="stderr", message=fill(error["message"]))
                for error in errors],
            examples=rendered, evaluations=evaluations, tips=[fill(t) for t in tips],
            supplemental="Se ejecuta contra los ficheros reales del sistema Fedora del laboratorio; la salida esperada se calcula en vivo al evaluar.")
        if self.document and pages:
            exercise["sources"] = [dict(document_hash=self.document[0], title=self.document[1], pages=list(pages))]
        self.exercises.append(exercise)
        self.solutions[name] = (f"cat > {path} <<'ASO_EOF'\n{solution.strip()}\nASO_EOF\n"
                                f"chmod 755 {path}\nchown learner:learner {path}\n")

    def course(self):
        return dict(schema_version=1, id=f"aso-bash-p{self.slug}", version="1.0", title=f"ASO Bash {self.number} · {self.title}",
                    description=(f"{self.intro.strip()}\n\nCada ejercicio es un **script de Bash** en `{self.base}/`: empieza por `#!/bin/bash`, hazlo ejecutable "
                                 "con `chmod u+x`, envía los resultados a stdout y los errores a stderr, y usa un código de salida distinto para cada error. "
                                 "Los ejercicios trabajan con ficheros y procesos reales del sistema (`/etc/passwd`, `/etc/group`, `/proc`, `/usr/share/dict/words`...): "
                                 "la salida esperada se calcula al evaluar, así que no vale escribir el resultado a mano."),
                    setup=[dict(script=self.setup, timeout=60)], exercises=self.exercises)
