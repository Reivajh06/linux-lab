# Writing Linux Lab exercise collections

Linux Lab imports UTF-8 `.yaml` or `.yml` files. The importer, evaluator, and local
AI generator share the same schema. View the machine-readable JSON schema at
`GET /api/courses/schema`. The import limit is 2 MB.

Exercises follow **Description -> Input requirements -> Output requirements ->
Examples (optional) -> Evaluations**. State the learner's contract before describing
how it earns points. For scripting exercises, link each invalid input to an error
output with its own nonzero exit code and stderr message, then test success and
every error with `run` cases.

## A complete scripting example

This collection prepares a small dictionary fixture at `/usr/share/dict/words` so
it works without downloading a dictionary package. Setup creates input data, not
the learner's script. A course using an installed dictionary can omit that fixture;
`from_command` computes the expected count from the container's actual data.

```yaml
schema_version: 1
id: dictionary-count
version: "1.0"
title: Count words by initial letter
description: Practice Bash arguments, validation, output streams, and exit codes.
setup:
  - script: |
      install -d /usr/share/dict
      printf '%s\n' alpha apple banana berry cherry date > /usr/share/dict/words
      install -d -o learner -g learner /home/learner/lab/dictionary
exercises:
  - id: count-letter
    title: Count words starting with a letter
    description: |
      Write an executable Bash script at the path below. Given one ASCII letter,
      count the words in `/usr/share/dict/words` starting with that letter,
      ignoring case. Print only the decimal count and a newline on success.
      Validate argument count before validating the letter.
    script:
      path: /home/learner/lab/dictionary/count-letter.sh
      usage: count-letter.sh LETTER
    input_requirements:
      - description: Supply exactly one argument.
        error: argument-count
      - description: The argument must be one ASCII letter, A-Z or a-z.
        error: invalid-letter
    output_requirements:
      - id: success
        description: Print the count followed by a newline; leave stderr empty.
        exit_code: 0
        stream: stdout
      - id: argument-count
        description: Reject zero or multiple arguments; leave stdout empty.
        exit_code: 1
        stream: stderr
        message: Expected exactly one argument
      - id: invalid-letter
        description: Reject an empty argument, multiple characters, or a nonletter.
        exit_code: 2
        stream: stderr
        message: Expected one ASCII letter
    examples:
      - command: /home/learner/lab/dictionary/count-letter.sh a
        stdout: "2\n"
        stderr: ""
        exit_code: 0
        description: The fixture contains alpha and apple.
      - command: /home/learner/lab/dictionary/count-letter.sh
        stdout: ""
        stderr: "Expected exactly one argument\n"
        exit_code: 1
      - command: /home/learner/lab/dictionary/count-letter.sh ab
        stdout: ""
        stderr: "Expected one ASCII letter\n"
        exit_code: 2
    evaluations:
      - id: valid-letters
        description: Count existing initials case-insensitively and handle zero matches.
        points: 10
        checks:
          - type: run
            requirement: success
            args: [a]
            stdout:
              match: exact
              from_command: LC_ALL=C grep -ic '^a' /usr/share/dict/words
            stderr: {match: empty}
          - type: run
            requirement: success
            args: [B]
            stdout:
              match: lines
              from_command: LC_ALL=C grep -ic '^b' /usr/share/dict/words
            stderr: {match: empty}
          - type: run
            requirement: success
            args: [z]
            stdout: {match: exact, value: "0\n"}
            stderr: {match: empty}
      - id: wrong-argument-count
        description: Reject missing and extra arguments with exit 1 and the required message.
        points: 5
        checks:
          - type: run
            requirement: argument-count
            args: []
            stderr: {match: exact, value: Expected exactly one argument}
          - type: run
            requirement: argument-count
            args: [a, b]
            stderr: {match: exact, value: Expected exactly one argument}
      - id: wrong-letter
        description: Reject invalid letters with exit 2 and the required message.
        points: 5
        checks:
          - type: run
            requirement: invalid-letter
            args: [ab]
            stderr: {match: exact, value: Expected one ASCII letter}
          - type: run
            requirement: invalid-letter
            args: ["7"]
            stderr: {match: exact, value: Expected one ASCII letter}
          - type: run
            requirement: invalid-letter
            args: [""]
            stderr: {match: exact, value: Expected one ASCII letter}
    tips:
      - Read about positional parameters and redirecting messages to stderr.
      - Make the script executable before evaluating it.
    sources: []
    supplemental: The dictionary fixture and grading cases are authored for this lab.
```

## Collection fields

| Field | Required | Meaning |
| --- | --- | --- |
| `schema_version` | No; defaults to 1 | Only `1` is supported. |
| `id` | Yes | Lowercase letters, digits, and hyphens; starts with a letter; at most 64 characters. |
| `version` | Yes | Quoted string, up to 40 letters, digits, dots, underscores, or hyphens; starts with a letter or digit. |
| `title` | Yes | Human-readable title, 1-200 characters. |
| `description` | Yes | Markdown introduction, up to 30,000 characters. |
| `setup` | No | Ordered list of at most 30 setup scripts. |
| `exercises` | Yes | Ordered list of 1-200 exercises, with unique IDs. |

An ID and version combination is immutable. Importing it twice is rejected. To
change a course, export it, change its version, and import the revision. Existing
work stays in its original environment. The Environments page can create multiple
named environments from one course version, each with independent state and scores.
Unknown fields, duplicate YAML mapping keys, aliases, and unsafe tags are rejected.

## Exercise fields

| Field | Required | Meaning |
| --- | --- | --- |
| `id`, `title`, `description` | Yes | ID/title follow collection rules; description is the Markdown assignment. |
| `script` | No | Deliverable `{path, usage?}`. `path` is an absolute path; `usage` is a short usage hint. This declares where the learner writes a script; it does not create it. |
| `input_requirements` | No | Up to 30 `{description, error?}` entries. `error` links to an output requirement ID for invalid input. |
| `output_requirements` | No | Up to 30 `{id, description, exit_code, stream?, message?}` entries, with unique IDs. Exit codes are 0-255; `stream` defaults to `stdout`. |
| `examples` | No | Up to 20 `{command, stdout?, stderr?, exit_code?, description?}` examples. Examples are explanatory, not executable grading cases. |
| `evaluations` | Yes | 1-30 entries, each with a unique `id`, Markdown `description`, integer `points` (1-1000), and 1-20 `checks`. |
| `tips` | No | Up to 20 Markdown hints. |
| `setup` | No | Up to 20 setup scripts. |
| `sources` | No | Up to 20 document references. |
| `supplemental` | No | Explain Linux setup/grading details added beyond the sources. |

An input requirement's `error` must name an existing output requirement whose exit
code is nonzero. Author errors with distinct exit codes and `stream: stderr`.
`message` documents the expected message; enforce its contents with a stream
expectation in the check. An output requirement alone does not create a test.
For nonscripting exercises, express inputs and outputs as relevant to the Linux
state being requested; `script` and empty optional sections can be omitted.

All checks in an evaluation must pass to earn its points. Separate evaluations
allow partial credit. Checks examine current state, not command history or editor
choice. Results are timestamped snapshots; evaluate again after changing the lab.

### Legacy collections

On import, `tasks` is accepted as a legacy alias for `evaluations`. Supplying both
keys is an error, even if they contain identical entries. Exports and generated
collections always use `evaluations`. Python callers can still read `Exercise.tasks`
as a read-only compatibility property; the serialized field is `evaluations`.

## Check reference

Fields not marked optional are required. `type` must be exactly as shown.

| Type | Fields | Condition |
| --- | --- | --- |
| `path` | `path`; optional `kind` | `file` (default), `directory`, `symlink`, or `absent`. Files/directories follow links; absence includes broken symlinks. |
| `content` | `path`, `value`; optional `match` | `contains` (default), `exact`, or Python `regex`. UTF-8 files, limit 1 MB. |
| `permissions` | `path`, `mode` | Exact quoted octal mode, 3 or 4 digits, e.g. `"640"`, `"2770"`. Follows links. |
| `ownership` | `path`; `owner` and/or `group` | At least one account/group name; follows links. |
| `user` | `name`; optional `exists`, `shell`, `home` | `exists` defaults to true; shell/home constrain existing accounts. |
| `group` | `name`; optional `exists` | `exists` defaults to true. |
| `membership` | `user`, `group` | Accepts primary or supplementary membership. |
| `package` | `name` | Installed according to `dpkg-query`. |
| `process` | `name`; optional `user` | Exact process name, at most 15 characters; optionally owned by a user. |
| `command` | `script`; optional `user`, `timeout`, `expected_exit`, `stdout_contains` | Bash script exits with expected status (default 0), and stdout contains optional text. |
| `run` | See below | Execute a program with arguments/stdin and compare status and streams. |

State probes run as root. Missing paths fail; invalid probe output and execution
errors are errors. Probes have a 10-second outer limit. Command checks default to
root and a 15-second timeout; command timeouts are errors.

### `run` check

| Field | Default | Meaning |
| --- | --- | --- |
| `type` | Required | `run`. |
| `path` | Exercise's `script.path` | Program to execute directly; either this or exercise `script` is required. Script files must exist and be executable. |
| `args` | `[]` | Up to 50 strings, each at most 4096 characters; passed as quoted arguments, not shell code. Quote numeric YAML arguments. |
| `stdin` | None | UTF-8 input (up to 100,000 characters), piped to the program. Without it stdin is `/dev/null`. |
| `cwd` | `/home/learner` | Working directory. |
| `user` | `learner` | `learner` or `root`. |
| `timeout` | `10` | Execution/reference timeout in seconds, 1-60. |
| `requirement` | None | Existing output requirement ID; supplies the expected exit code when `exit_code` is omitted. |
| `exit_code` | Requirement's code, otherwise `0` | Expected status, 0-255; explicit value overrides the requirement. |
| `stdout`, `stderr` | Unchecked | Optional `StreamExpectation` objects. For a stderr requirement, omitted stdout defaults to `empty`, omitted stderr to `nonempty`. Explicit stream expectations override those defaults. |
| `prepare` | None | Bash script run as root before the program, with a 15-second timeout; e.g. prepare case input files. It must not solve the exercise. |

Missing/nonexecutable scripts, wrong exit codes, mismatched output, and program
timeouts fail the case. Preparation failures and reference-command timeouts are
errors. Stderr requirement defaults do not compare the informational `message`;
add an explicit `stderr` expectation when exact wording matters. For stdout
requirements, add a `stdout` expectation and an empty `stderr` expectation.

### `StreamExpectation`

| `match` | Operand | Comparison |
| --- | --- | --- |
| `exact` (default) | Exactly one of `value`, `from_command` | Equal text after removing trailing newline characters. |
| `lines` | Exactly one of `value`, `from_command` | Same ordered lines, ignoring trailing spaces per line and final newlines. Whitespace-only output is treated as no lines. |
| `contains` | Exactly one of `value`, `from_command` | Expected text is a substring of actual output. |
| `regex` | Literal `value` only | Python regular expression search with multiline mode. Invalid regexes are rejected on import. |
| `empty` | Neither operand | No characters, including whitespace. |
| `nonempty` | Neither operand | At least one nonwhitespace character. |

`value` may be an empty string. `from_command` is a validated Bash command whose
stdout becomes the reference, even when checking stderr. It runs in the case's
working directory as the case's user, after the learner program. It should inspect
independent input data rather than call the learner's script. It does not assert
the reference command's exit status. Literal and command operands are limited to
30,000 characters each. Omitting a stream expectation leaves that stream unchecked,
except for the stderr requirement defaults described above.

## Script contract and shared state

Setup entries contain `script`, optional `user` (`root` or `learner`, default
`root`), and optional `timeout` (1-60 seconds, default 15). Command checks have the
same fields plus `type: command`, `expected_exit`, and optional `stdout_contains`.
Setup, command, preparation, and reference scripts are parsed as Bash on import;
unsupported syntax is rejected. A deliverable `script.path` identifies the
learner's file and is not parsed or executed on import.

Execution uses Bash in the container, normally in `/home/learner`, with `DISPLAY=:1`.
Use absolute paths and bounded, noninteractive commands. Custom grading commands
should inspect state. Stdout/stderr feedback is limited to 32 KB each, and
individual output files are limited to 1 MB.

Course setup runs first, followed by all exercise setup in order, once on a fresh
environment. Opening an exercise does not rerun it. Setup prepares inputs and
prerequisites, never completed answers. Use distinct paths and accounts across
exercises; `install -d -o learner -g learner /home/learner/lab/my-exercise` prepares
a learner-owned directory. State any dependency on earlier exercise answers.

Stopping preserves files, accounts, and installed packages. Recreating destroys
that state, clears scores, and reruns setup. Imports and generation do not execute
scripts; starting the environment runs setup. Import only collections you trust.
Learners have sudo, so grading is a practice aid rather than a secure exam. No
host paths or Docker socket are mounted into learner containers.

## Source references and portability

The Sources library accepts `.pdf`, `.txt`, `.md`, `.htm`, and `.html` documents.
PDFs retain their physical pages and local OCR behavior. Text uses UTF-8 with
cp1252/Latin-1 fallback. HTML becomes plain text, dropping scripts/styles and
retaining headings, lists, and code. Plain-text `.htm` sheets also work. Text is
split on paragraph boundaries into pages of about 3000 characters; long paragraphs
are split further. These pages use the same search and citation system without OCR.

References use the original document's SHA-256, title, and one-based indexed page
numbers (PDF physical pages, not printed labels; synthetic pages for text):

```yaml
sources:
  - document_hash: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
    title: Linux administration notes
    pages: [12, 13]
supplemental: Setup paths and grading checks were added using general Linux knowledge.
```

The API exposes the hash. References remain portable when the same original file
is uploaded elsewhere. YAML exports do not embed source files. Removed documents
remain named but are marked unavailable. Generated citations are checked against
the pages actually supplied to the model.

## Using Exercise Chat

Select a local model and optional ready sources, choose an exercise count, and
describe your goals. Follow-up requests revise the saved draft. The model receives
the canonical JSON schema through structured output plus concise authoring rules.
Generation uses one exercise per batch and at most two repair attempts per invalid
batch. Review the YAML, validate and save it, then import it. Each import uses a
course ID/version and never modifies an already running course. All model
computation uses the configured local Ollama endpoint.
