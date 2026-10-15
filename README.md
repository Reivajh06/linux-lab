# Linux Lab

A Windows desktop app for learning Linux in real Docker containers. Includes a
browser-rendered Linux desktop inside the app, 30 guided exercises, YAML course
imports, PDF sources with local OCR, and natural-language exercise generation using
your existing Ollama models.

## Windows application

Install **Linux-Lab-Setup-1.1.0.exe** from `release/1.1.0/`, then launch **Linux Lab** from
the Start menu or desktop shortcut. The installer includes the UI and Python
backend; Node and Python are not required on the target computer.

1. Install [Docker Desktop for Windows](https://docs.docker.com/desktop/setup/install/windows-install/),
   enable its WSL 2 backend, and use Linux containers. Start Docker Desktop.
2. In Linux Lab, open **Environment setup**, click **Build lab image**, and wait for
   the initial Ubuntu image build. This needs Internet for the first download.
3. Open **Free Practice**, or choose **Linux Foundations**, then **Start environment**.
4. The terminal opens inside the app. Try `man ls`, `nano notes.txt`, or
   `gedit notes.txt &`. Use `sudo` to administer the container.

The application runs in its own window. It starts a private backend on a random
localhost port and connects directly to host Ollama at `http://127.0.0.1:11434`.
Closing the application stops its backend. Learner containers continue running
until explicitly stopped, preserving their files for your next session.

Use **File → Open data folder** to inspect or back up local data. The default is
`%LOCALAPPDATA%\LinuxLab`, including the SQLite database, PDFs, and backend log.
The application is a personal local tool; no account or hosted service is needed.

### What you can do

- **Environments:** create named free-practice or course environments, open them,
  rename them, set CPU/memory/process limits, stop/start them, and delete them.
  Stop an environment before changing its limits. Each course environment shares
  state across that course's exercises; additional environments are independent.
  Deleting an environment removes its files and scores, while its course remains.
- **Appearance:** use the palette button in the top bar to select Tux, Ubuntu,
  Terminal, Debian, Mint, Fedora, Arch, Kali, openSUSE, Pop!_OS, or Manjaro dark
  colors, or choose a custom accent. The palette
  and selected model are saved in the local database across app restarts.
- **Free Practice:** an independent Ubuntu sandbox with vi, vim, nano, gedit, manuals,
  user/group administration, files, networking tools, packages, and scripting.
- **Application tabs:** the terminal and normal GUI windows fill the Linux display
  without window-manager borders. Starting `gedit notes.txt &` or `firefox &` from
  the shell adds a tab automatically. Use the tab bar to switch, launch another
  terminal/editor/browser, or close an app. Save-confirmation dialogs stay with
  their parent app. Normal shell foreground/background behavior is preserved.
  The full-screen button expands the workspace while keeping its tabs available.
  Existing environments are upgraded in place when opened; files and course
  progress are preserved. The first upgrade downloads Firefox and desktop tools.
- **Exercise Library:** imported and generated collections, their exercise lists,
  scores, YAML exports, and retained environments. **Recreate** starts clean after
  a confirmation; **Stop** preserves filesystem state.
- **Evaluate exercise / Evaluate all:** checks Linux end state and awards task points.
  Feedback includes failures, script errors, and timeouts. Results show their last
  evaluation time; they are not continuous monitoring.
- **Sources:** upload PDF theory or practice notes, preview them, monitor indexing,
  and retry extraction failures. Text pages use local extraction. Scanned pages
  use local OCR. In the Windows app, OCR falls back to a disposable lab-image
  container if Poppler/Tesseract are not installed locally. It receives a copy of
  the PDF, has no network or host-directory mounts, and is removed afterward.
- **Exercise Chat:** select a local Ollama model, optional sources, an exercise
  count, and describe what you want in natural language. Revise, edit, validate,
  save, download, or import the YAML draft. Nothing runs during generation.

Read [EXERCISE_FORMAT.md](EXERCISE_FORMAT.md) for the complete authoring contract.
The bundled answer scripts in `courses/foundations-solutions.json` exist for
acceptance testing; learners can use any valid solution.

## Local Ollama

Install and run [Ollama](https://ollama.com/). The app discovers installed local
models; it never pulls models automatically. It initially selects
`gemma3:12b-it-qat` if installed, then remembers your selection. No quality or speed
guarantee is implied by that default. Smaller models may need more revisions.

Source retrieval uses local SQLite full-text search, so no embedding model or
vector service is required. Selected page excerpts, the schema, the lab tool list,
and authoring instructions form the model context. Citations must refer to supplied
pages. General Linux knowledge supplements source topics for setup and checks.
Review generated commands: schema validity does not prove teaching quality or that
every check accurately captures the intended task.

If Ollama is unavailable, refresh the model list and verify that
`http://127.0.0.1:11434/api/tags` responds. Set `OLLAMA_BASE_URL` before launching
the desktop app if you use another local address. The app does not change your
Ollama configuration or enable cloud inference.

## Optional Docker Compose web deployment

The same app can also run without Electron:

```powershell
docker compose up --build -d
```

Open [Linux Lab](http://localhost:8080). The app is bound to `127.0.0.1`; learner
desktops are proxied through its backend. The app container owns Docker control;
learner containers never receive the Docker socket. Compose builds the lab image
before starting the app. Rebuild it with `docker compose build lab-image`.

Copy `.env.example` to `.env` to override port, resources, Ollama, or OCR settings.
Compose's default Ollama URL is `http://host.docker.internal:11434`. Host Ollama
must listen on an interface reachable from Docker; its default loopback binding
may not be reachable from a container. Configure `OLLAMA_HOST` for your Docker
network and restrict access with the host firewall, or use the Windows desktop
app, which can use Ollama's existing loopback listener directly. See the
[Ollama FAQ](https://docs.ollama.com/faq) for environment configuration.

`docker compose down` stops the app, not dynamically created learner containers.
Stop those through the app before shutting down Compose. Do not remove the
`linux-lab-net` network while learner containers use it.

## Development and Windows packaging

Requirements: Node 24+, pnpm 11.25+, Python 3.12, and Docker Desktop for integration
tests. Run these commands in the repository root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt pyinstaller==6.16.0
pnpm install
pnpm build:frontend
pnpm desktop
```

For the installer and unpacked executable:

```powershell
pnpm build:windows
```

Outputs: `release/1.1.0/Linux-Lab-Setup-1.1.0.exe` and
`release/1.1.0/win-unpacked/Linux Lab.exe`. PyInstaller bundles the backend, while
Electron provides a sandboxed Chromium UI. The local backend needs neither a
terminal window nor a separately installed Python runtime. The default installer
is unsigned; release distributors can add their own signing configuration.
The packaged application registers a Start menu and desktop shortcut on launch,
using Linux Lab's icon and Windows application ID for taskbar grouping. Palette
names are visual themes; they do not change the Ubuntu base distribution.

To run only the backend during UI development:

```powershell
$env:LAB_HOST_RUNTIME = '1'
.\.venv\Scripts\python.exe backend\desktop_server.py --port 8080
```

The backend serves `frontend/dist` when built. For hot reload use `pnpm --dir
frontend dev` in another terminal; its `/api` proxy forwards to port 8080.

### Checks

```powershell
Push-Location backend
..\.venv\Scripts\python.exe -m pytest -q
Pop-Location
pnpm --dir frontend test
pnpm build:frontend
```

Docker acceptance tests cover all 30 starter solutions, editor/manual installation,
isolation, filesystem persistence, and recreation:

```powershell
docker compose build lab-image
$env:RUN_DOCKER_TESTS = '1'
Push-Location backend
..\.venv\Scripts\python.exe -m pytest tests\test_docker_integration.py -q
Pop-Location
```

Tests remove their own containers. Do not use this flag unless Docker is running
and the lab image is built. Unit tests mock external model calls and OCR; actual
Docker desktop rendering, real OCR binaries, and local-model generation also need
smoke testing on a machine with those prerequisites.

## Resources, backup, and limits

Defaults per learner environment: 2 CPUs, 2 GB memory, 256 processes, and 256 MB
shared memory. Set `LAB_CPUS`, `LAB_MEMORY`, or `LAB_PIDS` before launching the
Windows app, or use `.env` for Compose. Images and filesystem writes use Docker
Desktop's disk allocation; clean up unused course environments through Recreate
and manage Docker's storage as needed.

PDF limits: 25 MB and 500 pages per upload. OCR includes English and Spanish.
`OCR_LANGUAGES` can select installed language packs, e.g. `eng+spa`; add other
Tesseract language packages to the relevant image before choosing them.

Generation runs one local-model job at a time, in batches of at most 3 exercises,
with at most 2 repair attempts per batch. `OLLAMA_TIMEOUT` defaults to 300 seconds
per model response. Cancelling preserves the last successful draft. OCR jobs and
generation jobs interrupted by shutdown show retryable status at the next launch.

Back up `%LOCALAPPDATA%\LinuxLab` while the app is closed. For Compose, back up the
`lab-data` volume while its app is stopped. These backups preserve sources, drafts,
courses, and scores. Learner state also lives in retained Docker containers:
export a stopped learner container with `docker export CONTAINER -o lab.tar` if
you need a filesystem backup. An export does not include Docker metadata; restoring
it and attaching it to an environment is a manual administrative operation.

Containers share their host Linux kernel. Bootloaders, hardware drivers, real disk
partitioning, kernel modules, and full systemd/boot exercises require virtual
machines and are outside this lab. Learners have sudo inside their own container;
evaluation is a learning tool rather than a secure examination system. Imported
setup/grading scripts are trusted course code and execute only inside the lab.
