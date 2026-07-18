from __future__ import annotations

import os
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
CONTAINER_REPO_ROOT = "/work/dotfiles"
DEFAULT_IMAGE = "docker.io/library/debian:bookworm-slim"
ROOT_HOME = "/tmp/qenv-root-home"
NONROOT_HOME = "/tmp/qenv-user-home"
NONROOT_UID = "65534"
NONROOT_GID = "65534"
DEFAULT_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
PROXY_ENV_VARS = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "NO_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
    "no_proxy",
)


def _proxy_env_args() -> list[str]:
    return [
        argument
        for variable_name in PROXY_ENV_VARS
        if variable_name in os.environ
        for argument in ("--env", f"{variable_name}={os.environ[variable_name]}")
    ]


@dataclass(frozen=True)
class CommandResult:
    exit_code: int
    stdout: str
    stderr: str


class ContainerRuntime:
    def __init__(self, executable: str) -> None:
        self.executable = executable

    def create_session(self, image: str = DEFAULT_IMAGE) -> "ContainerSession":
        container_name = f"qenv-it-{uuid.uuid4().hex[:12]}"
        runtime_args = self._runtime_run_args()
        env_args = _proxy_env_args()
        subprocess.run(
            [self.executable, "pull", image],
            check=True,
            text=True,
            capture_output=True,
        )
        result = subprocess.run(
            [
                self.executable,
                "run",
                "--detach",
                "--rm",
                "--name",
                container_name,
                *runtime_args,
                *env_args,
                "--volume",
                f"{REPO_ROOT}:{CONTAINER_REPO_ROOT}:ro",
                image,
                "sh",
                "-lc",
                (
                    f"mkdir -p {ROOT_HOME} {NONROOT_HOME} && "
                    f"chown {NONROOT_UID}:{NONROOT_GID} {NONROOT_HOME} && "
                    "while :; do sleep 3600; done"
                ),
            ],
            check=True,
            text=True,
            capture_output=True,
        )
        container_id = result.stdout.strip()
        return ContainerSession(self.executable, container_id)

    def _runtime_run_args(self) -> list[str]:
        if self.executable == "podman":
            return ["--network=host", "--http-proxy=false"]

        return ["--network=host"]


class ContainerSession:
    def __init__(self, runtime: str, container_id: str) -> None:
        self.runtime = runtime
        self.container_id = container_id

    def run(
        self,
        command: str,
        *,
        user: str = "root",
        home: str = ROOT_HOME,
        cwd: str = CONTAINER_REPO_ROOT,
    ) -> CommandResult:
        env_path = f"{home}/.local/bin:{DEFAULT_PATH}"
        env_args = _proxy_env_args()
        result = subprocess.run(
            [
                self.runtime,
                "exec",
                "--user",
                user,
                "--workdir",
                cwd,
                "--env",
                f"HOME={home}",
                "--env",
                f"PATH={env_path}",
                *env_args,
                self.container_id,
                "sh",
                "-c",
                command,
            ],
            check=False,
            text=True,
            capture_output=True,
        )
        return CommandResult(
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )

    def cleanup(self) -> None:
        subprocess.run(
            [self.runtime, "rm", "--force", self.container_id],
            check=False,
            text=True,
            capture_output=True,
        )


@dataclass
class IntegrationWorld:
    session: ContainerSession | None = None
    result: CommandResult | None = None


def detect_runtime() -> str:
    override = os.environ.get("QENV_TEST_CONTAINER_RUNTIME")
    if override:
        return override

    for candidate in ("podman", "docker"):
        if subprocess.run(
            ["sh", "-lc", f"command -v {candidate}"],
            check=False,
            text=True,
            capture_output=True,
        ).returncode == 0:
            return candidate

    raise RuntimeError("no supported container runtime found; install podman or docker")