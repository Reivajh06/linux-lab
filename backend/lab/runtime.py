"""Only this module talks to Docker. Learner containers receive no host mounts."""
import asyncio
import os
import shlex
import threading
import time
from dataclasses import dataclass

import docker
from docker.errors import DockerException, NotFound

from .db import now, uid


class LabError(Exception):
    pass


@dataclass
class Execution:
    code: int
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False


class Runtime:
    def __init__(self, db):
        self.db = db
        self._client = None
        self._locks: dict[str, asyncio.Lock] = {}
        self._docker_lock = threading.Lock()

    @property
    def client(self):
        with self._docker_lock:
            if self._client is None:
                try:
                    self._client = docker.from_env(timeout=90)
                except DockerException as exc:
                    raise LabError("Docker is unavailable. Start Docker Desktop with Linux containers, then retry.") from exc
            return self._client

    def lock(self, environment_id):
        return self._locks.setdefault(environment_id, asyncio.Lock())

    def health(self):
        try:
            self.client.ping()
            try:
                image = self.client.images.get(os.getenv("LAB_IMAGE", "linux-lab-environment:local"))
            except NotFound:
                return {"available": True, "image_ready": False, "message": "Build the lab image: docker compose build lab-image"}
            # Images built before the move to Fedora (Ubuntu based) lack this label.
            if ((image.attrs.get("Config") or {}).get("Labels") or {}).get("linux-lab.base") != "fedora":
                return {"available": True, "image_ready": False, "message": "The lab image is out of date (it predates the Fedora lab). Click Build lab image to update it, then recreate environments to move them to Fedora."}
            return {"available": True, "image_ready": True, "message": "Docker is ready"}
        except (DockerException, LabError) as exc:
            return {"available": False, "image_ready": False, "message": str(exc)}

    def environment(self, course_key=None):
        # This method is called in the event loop: insert/get is atomic there.
        row = self.db.one("SELECT * FROM environments WHERE course_key IS ? AND is_default=1", (course_key,))
        if row:
            return row
        name = self.db.course(course_key).title if course_key else "Free Practice"
        return self.create(name, course_key, is_default=True)

    def create(self, name, course_key=None, cpus=None, memory_mb=None, pids=None, is_default=False):
        if course_key:
            self.db.course(course_key)
        environment_id = uid()
        default_memory = max(512, int(docker.utils.parse_bytes(os.getenv("LAB_MEMORY", "2g")) / 1024 / 1024))
        self.db.execute("INSERT INTO environments(id,course_key,name,cpus,memory_mb,pids,is_default,created_at) VALUES(?,?,?,?,?,?,?,?)",
                        (environment_id, course_key, name.strip(), cpus or float(os.getenv("LAB_CPUS", "2")), memory_mb or default_memory,
                         pids or int(os.getenv("LAB_PIDS", "1024")), int(is_default), now()))
        return self.get(environment_id)

    async def update(self, environment_id, name, cpus, memory_mb, pids):
        async with self.lock(environment_id):
            row = await asyncio.to_thread(self.refresh, environment_id)
            limits_changed = (row["cpus"], row["memory_mb"], row["pids"]) != (cpus, memory_mb, pids)
            if limits_changed and row["state"] == "running":
                raise ValueError("Stop the environment before changing resource limits")
            if limits_changed and row["container_id"] and row["state"] != "missing":
                container = await asyncio.to_thread(self.container, environment_id)
                payload = {"NanoCpus": int(cpus * 1_000_000_000), "Memory": memory_mb * 1024 * 1024,
                           "MemorySwap": memory_mb * 2 * 1024 * 1024, "PidsLimit": pids}
                # Docker SDK 7 omits newer update fields; use its versioned engine transport.
                def update_limits():
                    response = self.client.api._post_json(self.client.api._url("/containers/{0}/update", container.id), data=payload)
                    self.client.api._raise_for_status(response)
                await asyncio.to_thread(update_limits)
            self.db.execute("UPDATE environments SET name=?,cpus=?,memory_mb=?,pids=? WHERE id=?", (name.strip(), cpus, memory_mb, pids, environment_id))
            return self.get(environment_id)

    def _remove_container(self, container):
        """Remove a lab container, its anonymous volumes and, if now unused, the outdated lab image it ran."""
        image_id = container.attrs.get("Image")
        container.remove(force=True, v=True)
        self._remove_unused_lab_image(image_id)

    def _remove_unused_lab_image(self, image_id):
        # Only images a linux-lab container ran: never the current lab tag, never an
        # image tagged by anything else, never one another container still uses.
        if not image_id:
            return
        lab_image = os.getenv("LAB_IMAGE", "linux-lab-environment:local")
        try:
            image = self.client.images.get(image_id)
            current = self.client.images.get(lab_image).id
        except (NotFound, DockerException):
            return
        repository = lab_image.rsplit(":", 1)[0]
        if image.id == current or any(tag.rsplit(":", 1)[0] != repository for tag in image.tags):
            return
        if self.client.containers.list(all=True, filters={"ancestor": image.id}):
            return
        try:
            self.client.images.remove(image.id, noprune=False)
        except DockerException:
            pass  # Still referenced (e.g. as a parent layer); leave it alone.

    async def delete(self, environment_id):
        async with self.lock(environment_id):
            row = self.get(environment_id)
            if row["container_id"]:
                try:
                    container = await asyncio.to_thread(self.container, environment_id)
                    await asyncio.to_thread(self._remove_container, container)
                except LabError:
                    if self.get(environment_id)["state"] != "missing":
                        raise
            with self.db.connect() as con:
                con.execute("DELETE FROM results WHERE environment_id=?", (environment_id,))
                con.execute("DELETE FROM environments WHERE id=?", (environment_id,))

    def get(self, environment_id):
        row = self.db.one("SELECT * FROM environments WHERE id=?", (environment_id,))
        if not row:
            raise KeyError("Environment not found")
        return row

    def container(self, environment_id):
        row = self.get(environment_id)
        if not row["container_id"]:
            raise LabError("Start this environment first")
        try:
            container = self.client.containers.get(row["container_id"])
        except NotFound as exc:
            self.db.execute("UPDATE environments SET state='missing',setup_done=0 WHERE id=?", (environment_id,))
            raise LabError("Container was removed outside the app. Recreate this environment.") from exc
        if container.labels.get("linux-lab.environment") != environment_id:
            raise LabError("Container ownership label does not match this environment")
        return container

    def refresh(self, environment_id):
        row = self.get(environment_id)
        if row["container_id"]:
            try:
                container = self.container(environment_id)
                state = "running" if container.status == "running" else "stopped"
                if row["state"] == "error":
                    state = "error"
                self.db.execute("UPDATE environments SET state=? WHERE id=?", (state, environment_id))
            except (LabError, DockerException):
                pass
        return self.get(environment_id)

    def _repair_desktop_launchers(self, container):
        # Older Windows builds copied the extensionless launcher with CRLF,
        # making its shebang refer to a nonexistent /bin/bash\r interpreter.
        repair = container.exec_run(["python3", "-c", (
            "from pathlib import Path\n"
            "for name in ('lab-terminal', 'lab-desktop'):\n"
            "    path = Path('/usr/local/bin') / name\n"
            "    data = path.read_bytes()\n"
            "    if b'\\r\\n' in data:\n"
            "        path.write_bytes(data.replace(b'\\r\\n', b'\\n'))\n"
            "        print(name)\n"
        )], user="root")
        if repair.exit_code:
            raise LabError("Could not repair the Linux desktop launchers: " + repair.output.decode(errors="replace"))
        repaired = repair.output.decode().splitlines()
        if "lab-desktop" in repaired:
            result = container.exec_run(["supervisorctl", "restart", "desktop"], user="root")
            if result.exit_code:
                raise LabError("Could not restart the repaired desktop: " + result.output.decode(errors="replace"))
        elif "lab-terminal" in repaired and container.exec_run(["pgrep", "-f", "gnome-terminal-server"]).exit_code:
            container.exec_run(["bash", "-c", "exec /usr/local/bin/lab-terminal >/tmp/linux-lab-terminal.log 2>&1"],
                               user="learner", detach=True, environment={"HOME": "/home/learner"})

    def _start(self, environment_id):
        row = self.get(environment_id)
        if (row["state"] == "error" and row["container_id"] and row["course_key"] and not row["setup_done"]
                and (row["error"] or "").startswith(("Setup step ", "Setup failed previously."))):
            message = row["error"]
            if "Recreate" not in message:
                message += " Recreate the environment to run setup from a clean state."
            raise LabError(message)
        if row["container_id"]:
            container = self.container(environment_id)
            if container.status != "running":
                container.start()
        else:
            kwargs = dict(
                image=os.getenv("LAB_IMAGE", "linux-lab-environment:local"),
                name=f"linux-lab-{environment_id[:16]}",
                labels={"linux-lab.managed": "true", "linux-lab.environment": environment_id},
                detach=True, init=True, hostname="fedora",
                mem_limit=row["memory_mb"] * 1024 * 1024,
                nano_cpus=int(row["cpus"] * 1_000_000_000),
                pids_limit=row["pids"],
                shm_size="256m", cap_drop=["NET_RAW"],
                restart_policy={"Name": "no"},
            )
            if os.getenv("LAB_HOST_RUNTIME") == "1":
                kwargs["ports"] = {"6080/tcp": ("127.0.0.1", None)}
            network = os.getenv("LAB_NETWORK")
            if network:
                kwargs["network"] = network
            try:
                container = self.client.containers.run(**kwargs)
            except DockerException as exc:
                raise LabError(f"Cannot create lab container: {exc}") from exc
            self.db.execute("UPDATE environments SET container_id=?,state='starting' WHERE id=?", (container.id, environment_id))
        self._repair_desktop_launchers(container)
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            container.reload()
            if container.status != "running":
                raise LabError("Linux desktop exited. Inspect its Docker logs and recreate it.")
            if container.exec_run(["bash", "-c", "test -f /tmp/lab-ready && pgrep -x 'Xvnc|Xtigervnc' >/dev/null && pgrep -x openbox >/dev/null && (pgrep -f gnome-terminal-server || pgrep -x xfce4-terminal) >/dev/null"]).exit_code == 0:
                break
            time.sleep(0.5)
        else:
            raise LabError("Linux desktop did not become ready within 45 seconds")
        if row["course_key"] and not row["setup_done"]:
            course = self.db.course(row["course_key"])
            steps = list(course.setup)
            for exercise in course.exercises:
                steps.extend(exercise.setup)
            for index, step in enumerate(steps):
                result = self.exec(environment_id, step.script, step.user, step.timeout)
                if result.code != 0 or result.timed_out:
                    raise LabError(f"Setup step {index + 1} failed: {result.stderr or result.stdout or 'timeout'}")
        self.db.execute("UPDATE environments SET state='running',setup_done=1,error=NULL WHERE id=?", (environment_id,))
        return self.get(environment_id)

    async def start(self, environment_id):
        async with self.lock(environment_id):
            try:
                return await asyncio.to_thread(self._start, environment_id)
            except Exception as exc:
                self.db.execute("UPDATE environments SET state='error',error=? WHERE id=?", (str(exc)[:2000], environment_id))
                if isinstance(exc, (LabError, KeyError)):
                    raise
                raise LabError(str(exc)) from exc

    async def stop(self, environment_id):
        async with self.lock(environment_id):
            await asyncio.to_thread(self.container(environment_id).stop, timeout=5)
            self.db.execute("UPDATE environments SET state='stopped' WHERE id=?", (environment_id,))
            return self.get(environment_id)

    async def recreate(self, environment_id):
        async with self.lock(environment_id):
            row = self.get(environment_id)
            if row["container_id"]:
                try:
                    await asyncio.to_thread(self._remove_container, self.container(environment_id))
                except LabError:
                    if self.get(environment_id)["state"] != "missing":
                        raise
            with self.db.connect() as con:
                con.execute("DELETE FROM results WHERE environment_id=?", (environment_id,))
                con.execute("UPDATE environments SET container_id=NULL,state='new',setup_done=0,error=NULL WHERE id=?", (environment_id,))
            try:
                return await asyncio.to_thread(self._start, environment_id)
            except Exception as exc:
                self.db.execute("UPDATE environments SET state='error',error=? WHERE id=?", (str(exc)[:2000], environment_id))
                raise LabError(str(exc)) from exc

    def exec(self, environment_id, script, user="root", timeout=15):
        container = self.container(environment_id)
        # Bound duration AND output size. Preserve stdout/stderr and original status.
        wrapper = (
            'work=$(mktemp -d); trap \'rm -rf -- "$work"\' EXIT; '
            f'(ulimit -f 1024; timeout --kill-after=2s {int(timeout)}s bash -lc {shlex.quote(script)}) '
            '>"$work/out" 2>"$work/err"; status=$?; '
            'head -c 32768 "$work/out"; head -c 32768 "$work/err" >&2; exit "$status"'
        )
        result = container.exec_run(["bash", "-c", wrapper], user=user, demux=True,
                                    environment={"DISPLAY": ":1", "HOME": "/home/learner" if user == "learner" else "/root"},
                                    workdir="/home/learner")
        stdout, stderr = result.output or (b"", b"")
        return Execution(result.exit_code, (stdout or b"").decode(errors="replace"),
                         (stderr or b"").decode(errors="replace"), result.exit_code in (124, 137))

    def desktop_url(self, environment_id):
        row = self.get(environment_id)
        if row["state"] != "running":
            raise LabError("Start the environment before connecting")
        container = self.container(environment_id)
        if os.getenv("LAB_HOST_RUNTIME") == "1":
            bindings = container.attrs["NetworkSettings"]["Ports"].get("6080/tcp")
            if not bindings:
                raise LabError("This environment has no desktop port. Recreate it for Windows desktop access.")
            return f"ws://127.0.0.1:{bindings[0]['HostPort']}"
        networks = container.attrs["NetworkSettings"]["Networks"]
        ip = next((v["IPAddress"] for v in networks.values() if v.get("IPAddress")), None)
        if not ip:
            raise LabError("Container has no reachable network address")
        return f"ws://{ip}:6080"
