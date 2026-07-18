from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from host import HostInfo

from .base import CommandProvider


if TYPE_CHECKING:
    from registry import ToolDefinition


class AptProvider(CommandProvider):
    name = "apt"
    executable_names = ("apt-get", "apt")
    install_args = ("install", "-y")
    requires_sudo = True

    def install(
        self,
        tool: ToolDefinition,
        package_name: str,
        host: HostInfo,
    ) -> subprocess.CompletedProcess[str]:
        update_result = self._refresh_package_lists(host)
        install_result = super().install(tool, package_name, host)
        return subprocess.CompletedProcess(
            args=install_result.args,
            returncode=install_result.returncode,
            stdout=_join_output(update_result.stdout, install_result.stdout),
            stderr=_join_output(update_result.stderr, install_result.stderr),
        )

    def _refresh_package_lists(self, host: HostInfo) -> subprocess.CompletedProcess[str]:
        executable = self._find_executable()
        if executable is None:
            raise RuntimeError("apt provider is unavailable")

        if host.is_root:
            command = [executable, "update"]
        else:
            helper = Path(__file__).resolve().parents[2] / "__setup/apt-update"
            if helper.is_file():
                command = [str(helper)]
            else:
                command = ["sudo", executable, "update"]

        command_text = " ".join(command)
        try:
            return subprocess.run(
                command,
                check=True,
                text=True,
                capture_output=True,
            )
        except OSError as exc:
            raise RuntimeError(
                f"apt package list refresh could not start while running '{command_text}': {exc}"
            ) from exc
        except subprocess.CalledProcessError as exc:
            summary = (exc.stderr or exc.stdout or "").strip()
            if not summary:
                summary = f"exit code {exc.returncode}"

            raise RuntimeError(
                f"apt package list refresh failed while running '{command_text}' "
                f"(exit {exc.returncode}): {summary}"
            ) from exc


def _join_output(left: str, right: str) -> str:
    content = [part for part in (left.strip(), right.strip()) if part]
    if not content:
        return ""

    return "\n".join(content)