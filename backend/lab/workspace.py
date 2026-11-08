"""Install and control the tabbed Linux workspace without recreating containers."""
import asyncio
import hashlib
import io
import json
from pathlib import Path
import tarfile

from .runtime import LabError

FILES = ("workspace.py", "lab-terminal", "install-browser.sh", "desktop.sh")
DESTINATION = "/opt/linux-lab-workspace"


class WorkspaceService:
    def __init__(self, runtime, assets):
        self.runtime, self.assets = runtime, Path(assets)
        self.prepared = set()

    def _files(self):
        return {name: (self.assets / name).read_bytes().replace(b"\r\n", b"\n") for name in FILES}

    def _prepare(self, environment_id):
        container = self.runtime.container(environment_id)
        if container.status != "running":
            raise LabError("Start the environment before opening its workspace")
        payloads = self._files()
        version = hashlib.sha256(b"".join(payloads.values())).hexdigest()
        cache_key = (container.id, version)
        if cache_key in self.prepared:
            return self.command(environment_id, "list")
        marker = container.exec_run(["cat", DESTINATION + "/version"])
        if marker.exit_code != 0 or marker.output.decode().strip() != version:
            container.exec_run(["mkdir", "-p", DESTINATION])
            archive = io.BytesIO()
            with tarfile.open(fileobj=archive, mode="w") as handle:
                for name, content in payloads.items():
                    entry = tarfile.TarInfo(name)
                    entry.size, entry.mode = len(content), 0o755
                    handle.addfile(entry, io.BytesIO(content))
            if not container.put_archive(DESTINATION, archive.getvalue()):
                raise LabError("Could not copy workspace tools into the environment")
            # Apt may take longer than a normal Docker request; consume output while
            # the command runs, with an outer timeout inside the container.
            script = (
                "set -e; bash /opt/linux-lab-workspace/install-browser.sh; "
                "install -m 755 /opt/linux-lab-workspace/lab-terminal /usr/local/bin/lab-terminal; "
                "install -m 755 /opt/linux-lab-workspace/desktop.sh /usr/local/bin/lab-desktop; "
                "install -d -o learner -g learner /home/learner/.config /home/learner/.config/openbox "
                "/home/learner/.config/gtk-3.0; "
                "runuser -u learner -- env DISPLAY=:1 python3 /opt/linux-lab-workspace/workspace.py configure; "
                f"printf %s {version} > /opt/linux-lab-workspace/version"
            )
            client = self.runtime.client.api
            execution = client.exec_create(container.id, ["timeout", "--kill-after=5s", "300s", "bash", "-lc", script], user="root")
            output = ""
            for chunk in client.exec_start(execution["Id"], stream=True):
                output = (output + chunk.decode(errors="replace"))[-6000:]
            status = client.exec_inspect(execution["Id"])
            if status["ExitCode"] != 0:
                raise LabError("Could not prepare application tabs. Your files are preserved. " + output)
        self.command(environment_id, "layout")
        self.prepared.add(cache_key)
        return self.command(environment_id, "list")

    async def prepare(self, environment_id):
        async with self.runtime.lock(environment_id):
            try:
                return await asyncio.to_thread(self._prepare, environment_id)
            except LabError:
                raise
            except Exception as exc:
                raise LabError(f"Cannot prepare Linux workspace: {exc}") from exc

    def command(self, environment_id, action, window=None):
        container = self.runtime.container(environment_id)
        if container.status != "running":
            raise LabError("The Linux environment is stopped")
        command = ["python3", DESTINATION + "/workspace.py", action]
        if window:
            command.append(window)
        result = container.exec_run(command, user="learner", demux=True,
                                    environment={"DISPLAY": ":1", "HOME": "/home/learner", "GTK_THEME": "Adwaita:dark"})
        stdout, stderr = result.output or (b"", b"")
        if result.exit_code:
            raise LabError((stderr or stdout or b"Cannot control application tab").decode(errors="replace")[:2000])
        try:
            return json.loads((stdout or b"{}").decode())
        except ValueError as exc:
            raise LabError("Linux workspace returned an invalid application list") from exc
