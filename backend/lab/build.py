import asyncio
import os
from pathlib import Path
import shutil
import subprocess
import docker


class ImageBuilder:
    def __init__(self, root):
        self.root = root
        self.state = "idle"
        self.log = ""
        self.task = None

    def status(self):
        return {"state": self.state, "log": self.log}

    def start(self):
        if self.state == "running":
            raise ValueError("A lab image build is already running")
        self.state, self.log = "running", "Preparing Linux environment image…\n"
        self.task = asyncio.create_task(self.run())

    async def run(self):
        process = None
        try:
            executable = shutil.which("docker")
            if not executable and os.name == "nt":
                candidates = [Path(os.getenv("ProgramFiles", "C:/Program Files")) / "Docker/Docker/resources/bin/docker.exe",
                              Path(os.getenv("LOCALAPPDATA", "")) / "Programs/DockerDesktop/resources/bin/docker.exe"]
                executable = next((str(p) for p in candidates if p.exists()), None)
            if not executable:
                # Docker Desktop's API can be available before its CLI is on PATH.
                await asyncio.to_thread(self.sdk_build)
                self.state = "done"
                self.log += "\nLab image ready. You can start an environment."
                return
            options = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
            process = await asyncio.create_subprocess_exec(executable, "build", "-t", os.getenv("LAB_IMAGE", "linux-lab-environment:local"), str(self.root / "docker" / "lab"), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT, **options)

            async def consume():
                while chunk := await process.stdout.read(4096):
                    self.log = (self.log + chunk.decode(errors="replace"))[-40000:]

            reader = asyncio.create_task(consume())
            try:
                await asyncio.wait_for(process.wait(), timeout=1800)
                await reader
            finally:
                reader.cancel()
            if process.returncode:
                raise ValueError(f"Docker build exited with code {process.returncode}. See the build log above.")
            self.state = "done"
            self.log += "\nLab image ready. You can start an environment."
        except asyncio.CancelledError:
            if process and process.returncode is None:
                process.kill()
                await process.wait()
            self.state = "error"
            self.log += "\nBuild interrupted. Retry after reopening the application."
        except Exception as exc:
            if process and process.returncode is None:
                process.kill()
                await process.wait()
            self.state = "error"
            self.log += "\n" + str(exc)

    def sdk_build(self):
        client = None
        try:
            client = docker.from_env(timeout=1800)
            for event in client.api.build(path=str(self.root / "docker" / "lab"), tag=os.getenv("LAB_IMAGE", "linux-lab-environment:local"), decode=True, rm=True):
                if "error" in event:
                    raise ValueError(event["error"])
                text = event.get("stream") or event.get("status", "")
                if text:
                    self.log = (self.log + text + ("" if text.endswith("\n") else "\n"))[-40000:]
        except Exception as exc:
            raise ValueError(f"Docker image build failed. Start Docker Desktop with Linux containers. {exc}") from exc
        finally:
            if client:
                client.close()
