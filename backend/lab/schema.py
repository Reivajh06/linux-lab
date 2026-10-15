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


Check = Annotated[PathCheck | ContentCheck | PermissionsCheck | OwnershipCheck | UserCheck | GroupCheck | MembershipCheck | PackageCheck | ProcessCheck | CommandCheck, Field(discriminator="type")]


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
    tasks: list[Task] = Field(min_length=1, max_length=30)
    tips: list[Text] = Field(default_factory=list, max_length=20)
    setup: list[Script] = Field(default_factory=list, max_length=20)
    sources: list[Reference] = Field(default_factory=list, max_length=20)
    supplemental: str | None = None

    @model_validator(mode="after")
    def unique_tasks(self):
        ids = [t.id for t in self.tasks]
        if len(ids) != len(set(ids)):
            raise ValueError("Task IDs must be unique within an exercise")
        return self


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


def parse_course(content: str) -> Course:
    if len(content.encode()) > 2_000_000:
        raise ValueError("Collection exceeds the 2 MB limit")
    try:
        return Course.model_validate(yaml.load(content, Loader=UniqueSafeLoader))
    except RecursionError as exc:
        raise ValueError("YAML nesting is too deep") from exc


def course_yaml(course: Course) -> str:
    return yaml.safe_dump(course.model_dump(exclude_none=True), sort_keys=False, allow_unicode=True)
