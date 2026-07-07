from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotfiles import find_dotfiles_root
from yamlutil import load_yaml_mapping


PACKAGE_METADATA_FILE = Path(".qenv/package.yaml")


class PackageError(RuntimeError):
    """Raised when package metadata is missing or invalid."""


@dataclass(frozen=True)
class PackageMetadata:
    directory_name: str
    name: str
    description: str
    required_tools: tuple[str, ...]
    stow_enabled: bool
    stow_target: str


def find_packages(dotfiles_root: Path | None = None) -> tuple[PackageMetadata, ...]:
    root = find_dotfiles_root() if dotfiles_root is None else dotfiles_root.resolve()
    packages: list[PackageMetadata] = []

    for child in sorted(root.iterdir(), key=lambda path: path.name):
        if not child.is_dir():
            continue

        if not (child / PACKAGE_METADATA_FILE).is_file():
            continue

        packages.append(load_package_metadata(child.name, dotfiles_root=root))

    return tuple(packages)


def load_package_metadata(
    package_name: str,
    dotfiles_root: Path | None = None,
) -> PackageMetadata:
    root = find_dotfiles_root() if dotfiles_root is None else dotfiles_root.resolve()
    package_dir = root / package_name
    metadata_path = package_dir / PACKAGE_METADATA_FILE

    if not package_dir.is_dir():
        raise PackageError(f"unknown package '{package_name}'")

    if not metadata_path.is_file():
        raise PackageError(f"package '{package_name}' is missing {metadata_path}")

    config = load_yaml_mapping(metadata_path, error_type=PackageError)
    return _validate_package_metadata(package_name, config, metadata_path)


def _validate_package_metadata(
    package_name: str,
    config: dict[str, Any],
    metadata_path: Path,
) -> PackageMetadata:
    version = config.get("version")
    if not isinstance(version, int):
        raise PackageError(f"{metadata_path} is missing an integer 'version'")

    package = _expect_mapping(config, "package", metadata_path)
    requires = _expect_mapping(config, "requires", metadata_path)
    tools = _expect_mapping(requires, "tools", metadata_path)
    stow = _expect_mapping(config, "stow", metadata_path)

    name = _expect_string(package, "name", metadata_path)
    description = _expect_string(package, "description", metadata_path)
    required_tools = _expect_required_tools(tools, metadata_path)
    stow_enabled = _expect_bool(stow, "enabled", metadata_path)
    stow_target = _expect_string(stow, "target", metadata_path)

    if name != package_name:
        raise PackageError(
            f"{metadata_path} package.name '{name}' does not match directory '{package_name}'"
        )

    return PackageMetadata(
        directory_name=package_name,
        name=name,
        description=description,
        required_tools=required_tools,
        stow_enabled=stow_enabled,
        stow_target=stow_target,
    )


def _expect_mapping(config: dict[str, Any], key: str, metadata_path: Path) -> dict[str, Any]:
    value = config.get(key)
    if not isinstance(value, dict):
        raise PackageError(f"{metadata_path} is missing the '{key}' mapping")

    return value


def _expect_string(config: dict[str, Any], key: str, metadata_path: Path) -> str:
    value = config.get(key)
    if not isinstance(value, str) or not value:
        raise PackageError(f"{metadata_path} is missing string '{key}'")

    return value


def _expect_bool(config: dict[str, Any], key: str, metadata_path: Path) -> bool:
    value = config.get(key)
    if not isinstance(value, bool):
        raise PackageError(f"{metadata_path} is missing boolean '{key}'")

    return value


def _expect_required_tools(tools: dict[str, Any], metadata_path: Path) -> tuple[str, ...]:
    value = tools.get("required")
    if not isinstance(value, list):
        raise PackageError(f"{metadata_path} is missing list 'requires.tools.required'")

    required_tools: list[str] = []
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            raise PackageError(
                f"{metadata_path} requires.tools.required item {index} must be a mapping"
            )

        tool_name = item.get("tool")
        if not isinstance(tool_name, str) or not tool_name:
            raise PackageError(
                f"{metadata_path} requires.tools.required item {index} is missing 'tool'"
            )

        required_tools.append(tool_name)

    return tuple(required_tools)