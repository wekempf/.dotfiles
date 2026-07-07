from __future__ import annotations

import platform
from dataclasses import dataclass
from pathlib import Path
from shutil import which


OS_RELEASE_PATH = Path("/etc/os-release")
PACKAGE_MANAGER_COMMANDS: dict[str, tuple[str, ...]] = {
    "apt": ("apt-get", "apt"),
    "dnf": ("dnf",),
    "pacman": ("pacman",),
    "brew": ("brew",),
}


@dataclass(frozen=True)
class HostInfo:
    operating_system: str
    distro: str | None
    architecture: str
    package_managers: tuple[str, ...]
    sudo_available: bool


def detect_host_info() -> HostInfo:
    operating_system = _detect_operating_system()
    distro = _detect_distro(operating_system)
    architecture = platform.machine().lower() or "unknown"
    package_managers = tuple(
        manager_name
        for manager_name, commands in PACKAGE_MANAGER_COMMANDS.items()
        if any(which(command) for command in commands)
    )
    sudo_available = which("sudo") is not None

    return HostInfo(
        operating_system=operating_system,
        distro=distro,
        architecture=architecture,
        package_managers=package_managers,
        sudo_available=sudo_available,
    )


def _detect_operating_system() -> str:
    system = platform.system()
    if system == "Darwin":
        return "macos"

    if system == "Linux":
        return "linux"

    return system.lower() or "unknown"


def _detect_distro(
    operating_system: str,
    os_release_path: Path = OS_RELEASE_PATH,
) -> str | None:
    if operating_system != "linux":
        return None

    os_release = _load_os_release(os_release_path)
    distro = os_release.get("ID") or os_release.get("NAME")
    if not distro:
        return "unknown"

    return distro.lower()


def _load_os_release(os_release_path: Path) -> dict[str, str]:
    try:
        text = os_release_path.read_text(encoding="utf-8")
    except OSError:
        return {}

    result: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        result[key] = _strip_quotes(value.strip())

    return result


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]

    return value