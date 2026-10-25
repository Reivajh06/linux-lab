"""The single exercise contract used by imports, exports and Ollama."""
import re
from typing import Annotated, Literal

import bashlex
import yaml
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

Id = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9-]{0,63}$")]
Text = Annotated[str, StringConstraints(min_length=1, max_length=30000)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def valid_script(value: str) -> str:
    if len(value) > 30000 or "\x00" in value or not value.strip():
        raise ValueError("Script must contain 1–30000 characters and no NUL bytes")
    try:
        bashlex.parse(value)
    except (bashlex.errors.ParsingError, NotImplementedError) as exc:
        raise ValueError(f"Invalid or unsupported Bash syntax: {exc}") from exc
    return value


class Script(StrictModel):
    script: Text
    user: Literal["root", "learner"] = "root"
    timeout: int = Field(default=15, ge=1, le=60)
    _syntax = field_validator("script")(valid_script)


class PathCheck(StrictModel):
    type: Literal["path"]
    path: Text
    kind: Literal["file", "directory", "symlink", "absent"] = "file"


class ContentCheck(StrictModel):
    type: Literal["content"]
    path: Text
    value: Text
    match: Literal["contains", "exact", "regex"] = "contains"

    @model_validator(mode="after")
    def regex(self):
        if self.match == "regex":
            try:
                re.compile(self.value)
            except re.error as exc:
                raise ValueError(f"Invalid regular expression: {exc}") from exc
        return self


class PermissionsCheck(StrictModel):
    type: Literal["permissions"]
    path: Text
    mode: Annotated[str, StringConstraints(pattern=r"^[0-7]{3,4}$")]


class OwnershipCheck(StrictModel):
    type: Literal["ownership"]
    path: Text
    owner: str | None = None
    group: str | None = None

    @model_validator(mode="after")
    def target(self):
        if not self.owner and not self.group:
            raise ValueError("Set owner, group, or both")
        return self


class UserCheck(StrictModel):
    type: Literal["user"]
    name: Text
    exists: bool = True
    shell: str | None = None
    home: str | None = None


class GroupCheck(StrictModel):
    type: Literal["group"]
    name: Text
    exists: bool = True


class MembershipCheck(StrictModel):
    type: Literal["membership"]
    user: Text
    group: Text


class PackageCheck(StrictModel):
    type: Literal["package"]
    name: Annotated[str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9+.:_-]*$")]


class ProcessCheck(StrictModel):
    type: Literal["process"]
    name: Annotated[str, StringConstraints(pattern=r"^[a-zA-Z0-9_.-]{1,15}$")]
    user: str | None = None


class CommandCheck(Script):
    type: Literal["command"]
    expected_exit: int = Field(default=0, ge=0, le=255)
    stdout_contains: str | None = None


class StreamExpectation(StrictModel):
    """What a stream must look like. `from_command` computes the reference output in the lab at evaluation time."""
    match: Literal["exact", "lines", "contains", "regex", "empty", "nonempty"] = "exact"
    value: str | None = Field(default=None, max_length=30000)
    from_command: str | None = Field(default=None, max_length=30000)

    @model_validator(mode="after")
    def operand(self):
        if self.match in ("empty", "nonempty"):
            if self.value is not None or self.from_command is not None:
                raise ValueError(f"'{self.match}' takes no value or from_command")
        elif (self.value is None) == (self.from_command is None):
            raise ValueError(f"'{self.match}' needs exactly one of value or from_command")
        if self.match == "regex":
            if self.from_command is not None:
                raise ValueError("regex expectations need a literal value")
            try:
                re.compile(self.value)
            except re.error as exc:
                raise ValueError(f"Invalid regular expression: {exc}") from exc
        if self.from_command is not None:
            valid_script(self.from_command)
        return self


class RunCheck(StrictModel):
    """Run the learner's script (or any program) with arguments/stdin and compare exit status and streams."""
    type: Literal["run"]
    path: str | None = Field(default=None, max_length=4096)  # defaults to the exercise's script.path
    args: list[Annotated[str, StringConstraints(max_length=4096)]] = Field(default_factory=list, max_length=50)
    stdin: str | None = Field(default=None, max_length=100000)
    cwd: str = Field(default="/home/learner", max_length=4096)
    user: Literal["root", "learner"] = "learner"
    timeout: int = Field(default=10, ge=1, le=60)
    requirement: Id | None = None  # output requirement this case exercises; supplies the default exit code/streams
    exit_code: int | None = Field(default=None, ge=0, le=255)
    stdout: StreamExpectation | None = None
    stderr: StreamExpectation | None = None
    prepare: str | None = Field(default=None, max_length=30000)  # root script run before the case, e.g. to create input files

    _prepare = field_validator("prepare")(lambda v: v if v is None else valid_script(v))


Check = Annotated[PathCheck | ContentCheck | PermissionsCheck | OwnershipCheck | UserCheck | GroupCheck | MembershipCheck | PackageCheck | ProcessCheck | CommandCheck | RunCheck, Field(discriminator="type")]


class ScriptDeliverable(StrictModel):
    path: Annotated[str, StringConstraints(pattern=r"^/[^\x00]{1,4095}$")]
    usage: str | None = Field(default=None, max_length=500)  # e.g. "letra.sh LETRA"


class InputRequirement(StrictModel):
    description: Text
    error: Id | None = None  # id of the output requirement produced when this requirement is violated


class OutputRequirement(StrictModel):
    id: Id
    description: Text
    exit_code: int = Field(ge=0, le=255)
    stream: Literal["stdout", "stderr"] = "stdout"
    message: str | None = Field(default=None, max_length=2000)  # message shown to the user, informative only


class Example(StrictModel):
    command: Annotated[str, StringConstraints(min_length=1, max_length=2000)]
    stdout: str | None = Field(default=None, max_length=10000)
    stderr: str | None = Field(default=None, max_length=10000)
    exit_code: int | None = Field(default=None, ge=0, le=255)
    description: str | None = Field(default=None, max_length=2000)


class Reference(StrictModel):
    document_hash: Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{64}$")]
    title: Text
    pages: list[int] = Field(min_length=1, max_length=50)

    @field_validator("pages")
    @classmethod
    def positive_pages(cls, pages):
        if any(p < 1 for p in pages) or len(pages) != len(set(pages)):
            raise ValueError("Page numbers must be unique positive integers")
        return pages


class Task(StrictModel):
    id: Id
    description: Text
    points: int = Field(ge=1, le=1000, strict=True)
    checks: list[Check] = Field(min_length=1, max_length=20)


class Exercise(StrictModel):
    id: Id
    title: Annotated[str, StringConstraints(min_length=1, max_length=200)]
    description: Text
    script: ScriptDeliverable | None = None
    input_requirements: list[InputRequirement] = Field(default_factory=list, max_length=30)
    output_requirements: list[OutputRequirement] = Field(default_factory=list, max_length=30)
    examples: list[Example] = Field(default_factory=list, max_length=20)
    evaluations: list[Task] = Field(min_length=1, max_length=30)
    tips: list[Text] = Field(default_factory=list, max_length=20)
    setup: list[Script] = Field(default_factory=list, max_length=20)
    sources: list[Reference] = Field(default_factory=list, max_length=20)
    supplemental: str | None = None

    @model_validator(mode="before")
    @classmethod
    def legacy_tasks(cls, data):
        # Collections written before schema 1.1 call evaluations "tasks".
        if isinstance(data, dict) and "tasks" in data:
            if "evaluations" in data:
                raise ValueError("Use evaluations, not both evaluations and tasks")
            data = {("evaluations" if k == "tasks" else k): v for k, v in data.items()}
        return data

    @model_validator(mode="after")
    def consistent(self):
        ids = [t.id for t in self.evaluations]
        if len(ids) != len(set(ids)):
            raise ValueError("Evaluation IDs must be unique within an exercise")
        outputs = {o.id: o for o in self.output_requirements}
        if len(outputs) != len(self.output_requirements):
            raise ValueError("Output requirement IDs must be unique within an exercise")
        for requirement in self.input_requirements:
            if requirement.error is not None:
                if requirement.error not in outputs:
                    raise ValueError(f"Input requirement refers to unknown output requirement '{requirement.error}'")
                if outputs[requirement.error].exit_code == 0:
                    raise ValueError(f"Output requirement '{requirement.error}' describes an error, so its exit_code must not be 0")
        for task in self.evaluations:
            for check in task.checks:
                if check.type != "run":
                    continue
                if check.path is None and self.script is None:
                    raise ValueError(f"Evaluation '{task.id}' runs a script, so set its path or the exercise's script.path")
                if check.requirement is not None and check.requirement not in outputs:
                    raise ValueError(f"Evaluation '{task.id}' refers to unknown output requirement '{check.requirement}'")
        return self

    @property
    def tasks(self):
        return self.evaluations


class Course(StrictModel):
    schema_version: Literal[1] = 1
    id: Id
    version: Annotated[str, StringConstraints(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,39}$")]
    title: Annotated[str, StringConstraints(min_length=1, max_length=200)]
    description: Text
    setup: list[Script] = Field(default_factory=list, max_length=30)
    exercises: list[Exercise] = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def unique_exercises(self):
        ids = [e.id for e in self.exercises]
        if len(ids) != len(set(ids)):
            raise ValueError("Exercise IDs must be unique within a course")
        return self


class UniqueSafeLoader(yaml.SafeLoader):
    """Do not silently overwrite duplicate mapping keys or expand YAML aliases."""
    def compose_node(self, parent, index):
        if self.check_event(yaml.AliasEvent):
            raise ValueError("YAML aliases are not supported")
        return super().compose_node(parent, index)

    def construct_mapping(self, node, deep=False):
        result = {}
        for key, value in node.value:
            k = self.construct_object(key, deep=deep)
            if not isinstance(k, str):
                raise ValueError("YAML mapping keys must be strings")
            if k in result:
                raise ValueError(f"Duplicate YAML key: {k}")
            result[k] = self.construct_object(value, deep=deep)
        return result


_RESERVED_START = re.compile(r"^(\s*(?:- +)*(?:[A-Za-z_][\w-]*:\s+)?)([`@%].*?)\s*$")
# A key's plain value containing ": " or ending in ":" ("stdout: Total:") reads as a nested mapping.
_COLON_VALUE = re.compile(r"^(\s*(?:- +)*[A-Za-z_][\w-]*:\s+)([^\s'\"\[{|>&*!#][^#]*?(?::\s.*|:))\s*$")
_BLOCK_START = re.compile(r"(?::|^\s*-)\s*[|>][+-]?\d*\s*$")


def repair_yaml(text: str) -> str:
    """Quote plain values YAML cannot read as written: "- `grep` finds it", "stdout: Total:".

    Markdown-minded authors (and local models) write these constantly; quoting them changes
    nothing else, and literal block contents (after | or >) are left untouched.
    """
    lines, block_indent = [], None
    for line in text.splitlines():
        indent = len(line) - len(line.lstrip(" "))
        if block_indent is not None and (not line.strip() or indent > block_indent):
            lines.append(line)
            continue
        block_indent = None
        match = _RESERVED_START.match(line) or _COLON_VALUE.match(line)
        if match:
            line = match.group(1) + "'" + match.group(2).replace("'", "''") + "'"
        elif _BLOCK_START.search(line):
            block_indent = indent
        lines.append(line)
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def load_yaml(content: str):
    """Load untrusted YAML, repairing reserved-character values and reporting the error position."""
    try:
        try:
            return yaml.load(content, Loader=UniqueSafeLoader)
        except yaml.YAMLError:
            repaired = repair_yaml(content)
            if repaired == content:
                raise
            return yaml.load(repaired, Loader=UniqueSafeLoader)
    except yaml.MarkedYAMLError as exc:
        mark = exc.problem_mark
        where = f" at line {mark.line + 1}, column {mark.column + 1}" if mark else ""
        raise ValueError(f"YAML syntax error{where}: {exc.problem or exc.context}") from exc
    except RecursionError as exc:
        raise ValueError("YAML nesting is too deep") from exc


def parse_course(content: str) -> Course:
    if len(content.encode()) > 2_000_000:
        raise ValueError("Collection exceeds the 2 MB limit")
    return Course.model_validate(load_yaml(content))


def course_yaml(course: Course) -> str:
    return yaml.safe_dump(course.model_dump(exclude_none=True), sort_keys=False, allow_unicode=True)
