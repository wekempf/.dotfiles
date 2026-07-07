from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from shutil import which
from typing import Any

from dotfiles import find_dotfiles_root
from host import HostInfo
from yamlutil import load_yaml_mapping


REGISTRY_FILE = Path("qenv/registry.yaml")


class RegistryError(RuntimeError):
    """Raised when the tool registry is missing or invalid."""


@dataclass(frozen=True)
class ProviderDefinition:
    name: str
    package: str


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    commands: tuple[str, ...]
    providers: dict[str, ProviderDefinition]


@dataclass(frozen=True)
class Registry:
    version: int
    tools: dict[str, ToolDefinition]

    def get_tool(self, name: str) -> ToolDefinition:
        try:
            return self.tools[name]
        except KeyError as exc:
            raise RegistryError(f"unknown tool '{name}'") from exc


def load_registry(dotfiles_root: Path | None = None) -> Registry:
    root = find_dotfiles_root() if dotfiles_root is None else dotfiles_root.resolve()
    config_path = root / REGISTRY_FILE
    config = load_yaml_mapping(config_path, error_type=RegistryError)
    return _validate_registry(config, config_path)


def get_tool(name: str, dotfiles_root: Path | None = None) -> ToolDefinition:
    registry = load_registry(dotfiles_root)
    return registry.get_tool(name)


def get_providers_for_tool(tool: ToolDefinition, host: HostInfo) -> tuple[ProviderDefinition, ...]:
    available_providers = set(host.package_managers)
    if which("mise") is not None:
        available_providers.add("mise")

    return tuple(
        provider
        for provider_name, provider in tool.providers.items()
        if provider_name in available_providers
    )


def _validate_registry(config: dict[str, Any], config_path: Path) -> Registry:
    version = config.get("version")
    if not isinstance(version, int):
        raise RegistryError(f"{config_path} is missing an integer 'version'")

    raw_tools = config.get("tools")
    if not isinstance(raw_tools, dict) or not raw_tools:
        raise RegistryError(f"{config_path} is missing the 'tools' mapping")

    tools: dict[str, ToolDefinition] = {}
    for tool_name, raw_tool in raw_tools.items():
        if not isinstance(tool_name, str) or not tool_name:
            raise RegistryError(f"{config_path} contains an invalid tool name")

        if not isinstance(raw_tool, dict):
            raise RegistryError(f"{config_path} tool '{tool_name}' must be a mapping")

        commands = _expect_string_list(raw_tool, "commands", config_path, tool_name)
        raw_providers = raw_tool.get("providers")
        if not isinstance(raw_providers, dict) or not raw_providers:
            raise RegistryError(
                f"{config_path} tool '{tool_name}' is missing the 'providers' mapping"
            )

        providers: dict[str, ProviderDefinition] = {}
        for provider_name, raw_provider in raw_providers.items():
            if not isinstance(provider_name, str) or not provider_name:
                raise RegistryError(
                    f"{config_path} tool '{tool_name}' contains an invalid provider name"
                )

            if not isinstance(raw_provider, dict):
                raise RegistryError(
                    f"{config_path} tool '{tool_name}' provider '{provider_name}' must be a mapping"
                )

            package = raw_provider.get("package")
            if not isinstance(package, str) or not package:
                raise RegistryError(
                    f"{config_path} tool '{tool_name}' provider '{provider_name}' is missing 'package'"
                )

            providers[provider_name] = ProviderDefinition(
                name=provider_name,
                package=package,
            )

        tools[tool_name] = ToolDefinition(
            name=tool_name,
            commands=commands,
            providers=providers,
        )

    return Registry(version=version, tools=tools)


def _expect_string_list(
    config: dict[str, Any],
    key: str,
    config_path: Path,
    tool_name: str,
) -> tuple[str, ...]:
    value = config.get(key)
    if not isinstance(value, list) or not value:
        raise RegistryError(f"{config_path} tool '{tool_name}' is missing list '{key}'")

    items: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item:
            raise RegistryError(
                f"{config_path} tool '{tool_name}' contains an invalid entry in '{key}'"
            )
        items.append(item)

    return tuple(items)