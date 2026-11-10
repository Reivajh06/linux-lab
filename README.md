# Linux Lab

A local app for learning Linux in **real Fedora containers**, right from your
browser (or as a Windows desktop app). Each learner environment is a Docker
container with a full Linux desktop rendered in the page: terminal, editors,
Firefox, manuals and `sudo`. Exercises are checked automatically against the
container's real end state.

It ships with guided courses (Linux Foundations and the ASO practice sheets), a
Notebook of study notes, and can **generate new exercises** from your own PDFs or
notes using a local [Ollama](https://ollama.com/) model. Everything runs on your
machine: no account, no hosted service, no cloud inference.

NOTE: this is an entirely vibecoded application for EDUCATION PURPOSES ONLY.

- [Quick start](#quick-start)
- [First steps in the app](#first-steps-in-the-app)
- [Features](#features)
- [Bundled content](#bundled-content)
- [Configuration](#configuration)
- [Local AI with Ollama](#local-ai-with-ollama)
- [Windows desktop app](#windows-desktop-app)
- [Running with Docker Compose manually](#running-with-docker-compose-manually)
- [How it works](#how-it-works)
- [Development](#development)
- [Resources, backup and limits](#resources-backup-and-limits)

---

## Quick start

**Prerequisites:** [Docker](https://docs.docker.com/get-docker/), meaning Docker Desktop on
Windows/macOS (using Linux containers and the WSL 2 backend on Windows), or Docker
Engine with the Compose plugin on Linux. Docker must be **running**. Ollama is
optional and only needed for the AI features.

From the repository folder:

| OS | Start | Stop |
|---|---|---|
| Windows | double-click `start-lab.cmd`, or `.\start-lab.ps1` | `.\start-lab.ps1 -Stop` |
| Linux / macOS | `bash start-lab.sh` (needs `curl`) | `bash start-lab.sh --stop` |

Then open **<http://localhost:8080>** (the launcher opens it for you).

What the launcher does:

1. Checks that Docker and Docker Compose are available and running.
2. Creates `.env` from `.env.example` if it doesn't exist.
3. Builds the Fedora lab image `linux-lab-environment:local` if it's missing.
   **The first run downloads several GB**, so expect it to take a while.
4. Builds the app image (cached when the code hasn't changed), starts it, and
   restarts it so that course and notebook edits are picked up.
5. Waits until `http://localhost:<port>/api/courses` answers, then opens the browser.

Options: `-NoBrowser` (PowerShell) / `--no-browser` (Bash) just prints the URL.
To use another port, set `LAB_PORT` in `.env` (e.g. `LAB_PORT=8090`). The
launcher refuses to start if the port is already taken by something else.

> **Re-run the launcher whenever you edit `courses/` or `notebook/`.** That's all
> it takes to load the changes. No manual rebuild is needed.

Stopping the app does **not** stop learner containers: they keep running and keep
their files until you stop them from the app's **Environments** page.

## First steps in the app

1. **Environments → Build lab image** if the app reports the image is missing
   (the launcher normally does this already).
2. Open **Free Practice** for a blank sandbox, or pick a course such as
   **Linux Foundations** in the **Library**, then click **Start environment**.
3. The terminal opens inside the page. Try `man ls`, `nano notes.txt`,
   `gedit notes.txt &` or `firefox &`. Use `sudo` to administer the container.
4. Solve an exercise, then click **Evaluate exercise** (or **Evaluate all**) to
   score it.

## Features

The app's sections, as they appear in the sidebar:

- **Environments.** Create named free-practice or course environments. You can open,
  rename, stop/start and delete them, and set CPU/memory/process limits (stop the
  environment before changing its limits). A course environment shares state
  across that course's exercises. Deleting an environment removes its files and
  scores but keeps the course.
- **In-browser Linux desktop.** The terminal and GUI apps fill the display
  without window borders, with a tab bar to switch, launch another
  terminal/editor/browser, or close apps. Running `gedit file &` or `firefox &`
  from the shell adds a tab automatically. There's a full-screen mode too. Windows
  dead keys (accents such as `´` + `a` = `á`) are composed correctly. Older
  environments are upgraded in place when opened, and files and progress are kept.
- **Environment Assistant.** A chat beside the desktop that answers questions
  about the current exercise using your local Ollama model.
- **Library.** Imported, bundled and generated collections grouped into folders,
  with exercise lists, scores, YAML export and retained environments. **Recreate**
  starts clean (after a confirmation). **Stop** keeps the filesystem.
- **Evaluation.** Checks the container's real end state and awards points.
  Feedback shows failures, script errors and timeouts. Results are snapshots taken
  when you click Evaluate, not continuous monitoring.
- **Notebook.** Markdown study notes (ASO practice notes and a Bash syntax
  reference) from `notebook/`. Pages can be edited inside the app; edits persist
  until you restore the original.
- **Sources.** Upload PDF, `.txt`, `.md`, `.htm` or `.html` theory/practice sheets,
  then preview them, monitor indexing and retry failures. Text PDFs are extracted locally.
  Scanned pages use local OCR (English + Spanish). Text/HTML is split into
  searchable pages of about 3000 characters, with scripts and styles stripped.
  UTF-8, cp1252 and Latin-1 are supported.
- **Exercise Chat.** Describe the exercises you want in natural language, then
  revise, edit, validate, save, download or import the YAML draft. Nothing runs
  during generation. Ask a question instead ("How do I approach csv-03?") and it
  answers from the draft and your library without touching the draft. Prefix a
  message with `/ask` or `/generate` to force a mode.
- **Appearance and sound.** The palette button switches between distro-inspired
  dark themes (Tux, Ubuntu, Fedora, Arch, Kali…) or a custom accent. The themes are
  only visual; the base is always Fedora. There are optional sound effects for
  evaluations and lab events. Preferences are saved in the local database.

## Bundled content

| Path | Contents |
|---|---|
| `courses/foundations.yaml` | **Linux Foundations**: 30 guided starter exercises |
| `courses/aso-p*.yaml` | **ASO Práctica** 1.2 – 3.2 (filters, users and permissions, Bash scripts, processes, vi) |
| `courses/aso-bash-p*.yaml` | **ASO Bash** 1.1 – 3.2: every practice sheet as Bash scripts run against the container's real files and processes; expected output is computed live at evaluation |
| `courses/aso-fund-*.yaml` | **ASO Fundamentos** 1.2 – 3.3 (shell, users, scripts, processes, systemd, monitoring) |
| `courses/*-solutions.json` | Reference solutions used by the acceptance tests. Learners may solve exercises any valid way |
| `notebook/*.md` | Notebook pages (front matter: `title`, `folder`, `order`, `icon`) |
| `exercises/` | Source YAML for the ASO practice sheets |
| `EXERCISE_FORMAT.md` | The complete exercise authoring contract |

Exercises follow *Description → Input requirements → Output requirements →
Examples (optional) → Evaluations*. Scripting exercises declare a script path, map
invalid inputs to stderr messages with distinct nonzero exit codes, and use `run`
cases to check output and errors. Older YAML using `tasks` still imports. Exports
and generated drafts use `evaluations`. See [EXERCISE_FORMAT.md](EXERCISE_FORMAT.md).

The ASO Bash courses are generated: edit them in `scripts/aso_bash/`, verify with
`scripts/aso_bash/verify.py` (needs Docker: it checks that stubs score nothing,
solutions score everything, and captures examples), then rebuild with
`scripts/build_aso_bash.py`.

> The systemd and Apache parts of ASO Práctica 3.2 need a real VM with systemd.
> The practice container cannot boot systemd.

## Configuration

Set these in `.env` (web/Compose) or as environment variables before launching the
Windows app:

| Variable | Default | Purpose |
|---|---|---|
| `LAB_PORT` | `8080` | Web port (bound to `127.0.0.1` only) |
| `LAB_CPUS` | `2` | CPUs per learner container |
| `LAB_MEMORY` | `2g` | Memory per learner container |
| `LAB_PIDS` | `1024` | Process/thread limit (Firefox alone uses several hundred) |
| `OLLAMA_BASE_URL` | `http://host.docker.internal:11434` (Compose), `http://127.0.0.1:11434` (Windows app) | Ollama address |
| `OLLAMA_TIMEOUT` | `300` | Seconds per model response |
| `OLLAMA_NUM_CTX` | `8192` | Model context ceiling (higher means more memory) |
| `OCR_LANGUAGES` | `eng+spa` | Tesseract languages; others must be installed in the image first |

## Local AI with Ollama

Install and run [Ollama](https://ollama.com/) and pull a model yourself. The app
only lists installed models and never downloads one. It restores your saved model,
otherwise picks `gemma3:12b-it-qat` if installed, otherwise the first model it
finds. Smaller models may need more revisions.

- **Grounding:** generation searches **all indexed sources by default** with
  SQLite full-text search. No embeddings or vector DB are used. You can restrict it to
  specific documents or turn grounding off. Only short, relevant page excerpts
  enter the prompt, and citations must point to supplied pages.
- **Budget:** one exercise at a time, an 8192-token context and up to 2048 output
  tokens, with at most 2 repair attempts. Oversized revisions keep the existing draft
  and ask you to split the course. For thinking models, thinking is disabled or set
  to low when Ollama supports it.
- **Review what it generates.** A valid schema doesn't guarantee good teaching or
  that every check matches the intended task.

**Docker networking caveat:** inside Compose the app reaches Ollama at
`host.docker.internal:11434`. Ollama's default loopback-only binding may not be
reachable from a container, so set `OLLAMA_HOST` (on the Ollama side) to an
interface Docker can reach and restrict it with your firewall. See the
[Ollama FAQ](https://docs.ollama.com/faq). The Windows desktop app avoids this by
talking to `127.0.0.1:11434` directly.

Troubleshooting: refresh the model list and check that
`http://127.0.0.1:11434/api/tags` responds.

## Windows desktop app

Install **`Linux-Lab-Setup-1.3.6.exe`** from `release/1.3.6/` and launch
**Linux Lab** from the Start menu or desktop shortcut. Node and Python are *not*
required; the installer bundles the UI and backend. You still need Docker Desktop
running with Linux containers.

- On first use, open **Environment setup → Build lab image** (needs Internet).
- The app starts a private backend on a random localhost port and stops it when
  you close the window. Learner containers keep running.
- Data lives in `%LOCALAPPDATA%\LinuxLab`: the SQLite database, uploaded PDFs and
  the backend log. Open it with **File → Open data folder**.
- If Poppler/Tesseract aren't installed locally, OCR runs in a disposable lab-image
  container with no network or host mounts, which is removed afterwards.

## Running with Docker Compose manually

This is what the launchers do. Copy `.env.example` to `.env` first, then:

```bash
docker compose build lab-image   # only if linux-lab-environment:local is missing
docker compose build app
docker compose up -d --no-build app
docker compose restart app
```

| You changed… | Run |
|---|---|
| `courses/` or `notebook/` | `docker compose restart app` (they are mounted read-only) |
| backend or frontend code | `docker compose build app && docker compose up -d --no-build app` |
| `docker/lab/` (the Fedora image) | `docker compose build lab-image` |

`docker compose stop app` stops the app and keeps its data. Stop learner
containers through the app **before** shutting Compose down, and don't remove the
`linux-lab-net` network while learner containers use it.

## How it works

```
Browser ──► app container (FastAPI + built React UI, :8080 on 127.0.0.1)
               │  Docker socket (only the app has it)
               ├──► learner container (Fedora 44: TigerVNC + Openbox + GNOME Terminal,
               │      noVNC over websockets, proxied through the backend)
               ├──► SQLite + uploaded sources  (lab-data volume / %LOCALAPPDATA%)
               └──► Ollama on the host (optional)
```

- The **app container** owns Docker control. Learner containers never get the
  Docker socket. The desktop is streamed with noVNC and proxied by the backend.
- Evaluation runs each exercise's check scripts inside the learner container and
  inspects the resulting state.

Repository layout:

| Path | What lives there |
|---|---|
| `backend/lab/` | FastAPI app: `main.py` (API), `runtime.py` (containers), `evaluation.py`, `generation.py` (Ollama), `sources.py` (PDF/OCR/FTS), `schema.py` (course YAML), `notebook.py`, `workspace.py`, `db.py` |
| `backend/desktop_server.py` | Backend entry point used by the Windows app and local dev |
| `backend/tests/` | Pytest suite (unit + opt-in Docker integration) |
| `frontend/src/` | React 19 + Vite + TypeScript UI (`Desktop.tsx`, `Library.tsx`, `Notebook.tsx`, …) |
| `desktop/` | Electron shell for the Windows app |
| `docker/app/` | App image |
| `docker/lab/` | Fedora learner image, desktop/VNC startup and supervisord config |
| `scripts/` | Course builders (`build_starter.py`, `build_aso_bash.py`, `aso_bash/`) and the backend packaging script |
| `start-lab.*` | One-command launchers |

## Development

Requirements: Node 24+, pnpm 11.25+, Python 3.12, and Docker Desktop for
integration tests.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt pyinstaller==6.16.0
pnpm install
pnpm build:frontend
pnpm desktop          # run the Electron app
```

Backend only, with hot-reloading UI:

```powershell
$env:LAB_HOST_RUNTIME = '1'
.\.venv\Scripts\python.exe backend\desktop_server.py --port 8080
pnpm --dir frontend dev   # in another terminal; /api is proxied to :8080
```

The backend also serves `frontend/dist` when it has been built.

### Tests

```powershell
Push-Location backend; ..\.venv\Scripts\python.exe -m pytest -q; Pop-Location
pnpm --dir frontend test
pnpm build:frontend
```

The Docker acceptance tests cover all 30 starter solutions, editors/manuals,
isolation, persistence and recreation. They need Docker running and the lab image built:

```powershell
docker compose build lab-image
$env:RUN_DOCKER_TESTS = '1'
Push-Location backend; ..\.venv\Scripts\python.exe -m pytest tests\test_docker_integration.py -q; Pop-Location
```

Tests clean up their own containers. Unit tests mock Ollama and OCR, so real
desktop rendering, OCR binaries and model generation still need a manual smoke test.

### Building the Windows installer

```powershell
pnpm build:windows
```

This produces `release/1.3.6/Linux-Lab-Setup-1.3.6.exe` and
`release/1.3.6/win-unpacked/Linux Lab.exe`. PyInstaller bundles the backend and
Electron provides a sandboxed Chromium UI. The installer is unsigned by default.

## Resources, backup and limits

- **Per environment:** 2 CPUs, 2 GB RAM, 1024 PIDs and 256 MB shared memory by
  default. Disk usage comes out of Docker's storage allocation, so use **Recreate**
  and Docker's own cleanup tools to reclaim space.
- **Uploads:** 25 MB per file; PDFs up to 500 pages.
- **Jobs:** one model job at a time. Cancelling keeps the last good draft. OCR and
  generation jobs interrupted by a shutdown show as retryable on the next launch.
- **Backup:** with the app stopped, back up the `lab-data` volume (Compose) or
  `%LOCALAPPDATA%\LinuxLab` (Windows). That covers sources, drafts, courses and
  scores. Learner files live in the containers. Export one with
  `docker export CONTAINER -o lab.tar` (without metadata; re-attaching it is manual).
- **What it can't do:** containers share the host kernel, so bootloaders, drivers,
  disk partitioning, kernel modules and full systemd/boot exercises need a VM.
- **Security model:** learners have `sudo` in their own container, and evaluation is
  a learning aid rather than a secure exam system. Imported setup and grading scripts are
  trusted course code and only execute inside the lab.
