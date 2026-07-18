from __future__ import annotations

import subprocess
from abc import ABC, abstractmethod
from shutil import which
from typing import TYPE_CHECKING

from host import HostInfo


if TYPE_CHECKING:
    from registry import ToolDefinition


class ProviderError(RuntimeError):
    """Raised when provider discovery or execution fails."""


class UnknownProviderError(ProviderError):
    """Raised when a provider name has no matching backend implementation."""


class InstallError(ProviderError):
    """Raised when a provider install command fails."""


class Provider(ABC):
    name = ""
    requires_sudo = False

    @abstractmethod
    def is_available(self, host: HostInfo) -> bool:
        raise NotImplementedError

    @abstractmethod
    def install(
        self,
        tool: ToolDefinition,
        package_name: str,
        host: HostInfo,
    ) -> subprocess.CompletedProcess[str]:
        raise NotImplementedError


class CommandProvider(Provider):
    executable_names: tuple[str, ...] = ()
    install_args: tuple[str, ...] = ()

    def is_available(self, host: HostInfo) -> bool:
        return self._find_executable() is not None

    def install(
        self,
        tool: ToolDefinition,
        package_name: str,
        host: HostInfo,
    ) -> subprocess.CompletedProcess[str]:
        executable = self._find_executable()
        if executable is None:
            raise InstallError(f"provider '{self.name}' is not available on this host")

        command = self._build_install_command(executable, package_name, host)
        command_text = " ".join(command)

        try:
            return subprocess.run(
                command,
                check=True,
                text=True,
                capture_output=True,
            )
        except OSError as exc:
            raise InstallError(
                f"install tool '{tool.name}' via provider '{self.name}' could not start "
                f"while running '{command_text}': {exc}"
            ) from exc
        except subprocess.CalledProcessError as exc:
            summary = (exc.stderr or exc.stdout or "").strip()
            if not summary:
                summary = f"exit code {exc.returncode}"

            raise InstallError(
                f"install tool '{tool.name}' via provider '{self.name}' failed while running "
                f"'{command_text}' (exit {exc.returncode}): {summary}"
            ) from exc

    def _find_executable(self) -> str | None:
        for executable_name in self.executable_names:
            if which(executable_name) is not None:
                return executable_name

        return None

    def _build_install_command(
        self,
        executable: str,
        package_name: str,
        host: HostInfo,
    ) -> list[str]:
        command: list[str] = []
        if self.requires_sudo and not host.is_root:
            command.append("sudo")

        command.extend([executable, *self.install_args, package_name])
        return command