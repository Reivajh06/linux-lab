# Writing Linux Lab exercise collections

Linux Lab imports UTF-8 `.yaml` or `.yml` files. The importer, evaluator, and local
AI generator share the same schema. View the machine-readable JSON schema at
`GET /api/courses/schema`. The import limit is 2 MB.

## A complete example

```yaml
schema_version: 1
id: team-files
version: "1.0"
title: A team's first files
description: Practice files, groups, and permissions in one shared Linux workspace.
setup:
  - script: |
      install -d -o learner -g learner /home/learner/team-practice
    user: root
    timeout: 15
exercises:
  - id: team-note
    title: Leave the team a note
    description: |
      Create `/home/learner/team-practice/note.txt` containing `Hello, team!`.
      Set its permissions so only the owner can read or write it.
    tasks:
      - id: greeting
        description: Save the greeting in the right file.
        points: 5
        checks:
          - type: content
            path: /home/learner/team-practice/note.txt
            value: Hello, team!
            match: contains
      - id: private
        description: Set the file permissions to 600.
        points: 5
        checks:
          - type: permissions
            path: /home/learner/team-practice/note.txt
            mode: "600"
    tips:
      - Try nano, vim, vi, or gedit to create the file.
      - Read `man chmod` for numeric permission modes.
    setup: []
    sources: []
    supplemental: Setup and evaluation rules use general Linux knowledge.
```

## Collection fields

| Field | Required | Meaning |
| --- | --- | --- |
| `schema_version` | Yes; defaults to 1 | Only `1` is supported. |
| `id` | Yes | Stable lowercase ID, starting with a letter; letters, numbers, and hyphens only; at most 64 characters. |
| `version` | Yes | **Quoted string**, up to 40 letters, digits, dots, underscores, or hyphens; starts with a letter or number. |
| `title` | Yes | Human-readable title, 1–200 characters. |
| `description` | Yes | Markdown introduction, up to 30,000 characters. |
| `setup` | No | Ordered list of scripts; at most 30. |
| `exercises` | Yes | Ordered list containing 1–200 exercises. |

An ID and version combination is immutable. Importing it twice is rejected. To
change an existing course, export it, change the version, and import the revision.
The revision gets a separate environment. Old work remains in its original course.
The Environments page can also create multiple named environments from the same
course version. Each has its own files, accounts, resources, and evaluation results.
Opening a course from the library uses its primary environment; opening a named
environment from Environments uses that specific instance.
Unknown fields, duplicate YAML mapping keys, aliases, and unsafe YAML tags are
rejected rather than silently interpreted.

## Exercise and task fields

Each exercise has `id`, `title`, `description`, and `tasks`. Exercise IDs are unique
within a collection and follow the same ID syntax as courses.

- `tasks`: 1–30 checklist entries, each with a unique `id`, Markdown `description`,
  positive integer `points` (1–1000), and 1–20 `checks`.
- `tips`: optional list of up to 20 Markdown strings.
- `setup`: optional list of up to 20 setup scripts.
- `sources`: optional list of up to 20 PDF references.
- `supplemental`: optional text explaining Linux details added beyond the sources.

All a task's checks must pass to earn its points. Exercises can earn partial credit
through separate tasks. A failed condition is `fail`; a timeout or execution error
is `error`. Errors award no points. Evaluation examines **current state**, not
terminal history or which editor a learner used. Results are timestamped snapshots;
evaluate again after changing the environment.

## Check reference

Fields not marked optional below are required. `type` must be exactly as shown.

| Type | Fields | Condition |
| --- | --- | --- |
| `path` | `path`; optional `kind` | `kind` is `file` (default), `directory`, `symlink`, or `absent`. File/directory checks follow links; absence checks include broken symlinks. |
| `content` | `path`, `value`; optional `match` | `match` is `contains` (default), `exact`, or Python `regex`. UTF-8 files only; limit 1 MB. |
| `permissions` | `path`, `mode` | Exact octal mode, **quoted**, 3 or 4 digits, e.g. `"640"`, `"2770"`. Follows links. |
| `ownership` | `path`; `owner` and/or `group` | Account/group names; at least one must be set. Follows links. |
| `user` | `name`; optional `exists`, `shell`, `home` | `exists` defaults to true. `shell` and `home` constrain existing accounts. |
| `group` | `name`; optional `exists` | `exists` defaults to true. |
| `membership` | `user`, `group` | Accepts primary or supplementary membership. |
| `package` | `name` | Debian package is installed according to `dpkg-query`. |
| `process` | `name`; optional `user` | Exact Linux process name, at most 15 characters; optionally owned by a given user. |
| `command` | `script`; optional `user`, `timeout`, `expected_exit`, `stdout_contains` | Bash script exits with expected status (default 0) and stdout contains optional text. |

Built-in checks run as root in the learner container. Missing paths produce a
failed condition; invalid output, unreadable inputs, or probe failures produce an
error. Regex checks and probes have a 10-second outer limit.

### User, group, and custom command example

```yaml
schema_version: 1
id: group-practice
version: "1.0"
title: Group practice
description: Create a user and assign a supplementary group.
exercises:
  - id: join-developers
    title: Join the developers
    description: Create labdev, create labdevelopers, and add labdev to that group.
    tasks:
      - id: account
        description: Create a Bash account with a home directory.
        points: 5
        checks:
          - type: user
            name: labdev
            shell: /bin/bash
            home: /home/labdev
      - id: membership
        description: Add the developer group membership.
        points: 5
        checks:
          - type: group
            name: labdevelopers
          - type: membership
            user: labdev
            group: labdevelopers
      - id: executable-script
        description: Create /home/learner/hello.sh that prints Hello.
        points: 5
        checks:
          - type: command
            script: /home/learner/hello.sh
            user: learner
            timeout: 5
            expected_exit: 0
            stdout_contains: Hello
    tips:
      - Read the useradd, groupadd, and usermod manual pages.
```

## Script contract and shared state

Setup entries contain `script`, optional `user` (`root` or `learner`, default
`root`), and optional `timeout` (1–60 seconds, default 15). Command checks have
the same fields plus `type: command`, `expected_exit` (0–255), and optional
`stdout_contains`.

Scripts are parsed as Bash on import; unsupported syntax is rejected with its
location. Execution uses `bash -lc` with working directory `/home/learner` and
`DISPLAY=:1`. Use absolute paths. Scripts must be noninteractive. Only use custom
grading commands to inspect state; the app cannot prove arbitrary shell code is
read-only. The stdout/stderr feedback limit is 32 KB each, and individual output
files are limited to 1 MB. Timeout exits are reported as errors.

Course setup runs first, followed by **all exercise setup in order**, exactly once
on a fresh environment. Opening an exercise does not rerun its setup. Setup should
create input data and prerequisites, never the learner's completed answers.
Use distinct paths and account names across exercises. Prefer
`install -d -o learner -g learner /home/learner/lab/my-exercise` when preparing
learner-owned directories. Do not rely on previous exercise answers unless your
description states that dependency explicitly.

Stopping preserves the entire container filesystem, including users, groups, and
installed packages. Recreating destroys that state, clears current scores, and
reruns setup. Setup failure leaves an error environment; fix the collection in a
new version or recreate after resolving the failure.

Imports and AI generation do not execute scripts. Starting the environment runs
setup. Import only collections you trust. Learners have sudo, so this grading is a
practice aid, not a tamper-resistant exam system. No host paths or Docker socket
are mounted into learner containers.

## PDF references and portability

Optional exercise references use the PDF's SHA-256, title, and **one-based PDF page
numbers** (not the printed page labels):

```yaml
sources:
  - document_hash: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
    title: Linux administration notes
    pages: [12, 13]
supplemental: Setup paths and grading checks were added using general Linux knowledge.
```

The Sources library exposes the document hash through its API. References remain
portable across installations when the same PDF is imported. YAML exports do not
embed PDF files. Missing or removed documents remain named in the exercise but
are marked unavailable. Local model output is checked against the actual source
pages provided to it; generated citations cannot invent other page numbers.

## Using Exercise Chat

Select a local model and optional ready PDFs, choose the requested exercise count,
and describe your goals in natural language. Follow-up requests revise the saved
draft. The model receives this format through the canonical JSON schema and
authoring rules, then returns structured data converted into YAML.

Generation uses batches of up to three exercises, with at most two repair attempts
per invalid batch. Review the editable YAML, validate and save it, then import it.
Each import uses a course ID/version; importing never modifies an already running
course. All model computation uses the configured local Ollama endpoint.
