from __future__ import annotations

from dataclasses import dataclass
from shutil import which

from host import HostInfo
from packages import PackageMetadata
from policy import Policy
from providers import ProviderError, get_provider
from registry import ProviderDefinition, Registry, ToolDefinition, get_providers_for_tool


class ResolverError(RuntimeError):
    """Raised when qenv cannot resolve required tool installs."""

    def __init__(self, message: str, suggestion: str | None = None):
        super().__init__(message)
        self.suggestion = suggestion


@dataclass(frozen=True)
class PlannedToolInstall:
    tool: ToolDefinition
    provider: ProviderDefinition


@dataclass(frozen=True)
class InstallPlan:
    package: PackageMetadata
    installed_tools: tuple[ToolDefinition, ...]
    tools_to_install: tuple[PlannedToolInstall, ...]


def is_command_available(command: str) -> bool:
    return which(command) is not None


def is_tool_installed(tool: ToolDefinition) -> bool:
    return all(is_command_available(command) for command in tool.commands)


def resolve_provider(
    tool: ToolDefinition,
    host: HostInfo,
    policy: Policy,
    registry: Registry,
) -> ProviderDefinition:
    resolved_tool = registry.get_tool(tool.name)
    try:
        available_providers = {
            provider.name: provider for provider in get_providers_for_tool(resolved_tool, host)
        }
    except ProviderError as exc:
        raise ResolverError(str(exc)) from exc

    if not available_providers:
        raise ResolverError(
            f"tool '{resolved_tool.name}' has no available providers on this host",
            suggestion=(
                "Install or add a provider backend for this host, then update the registry or "
                "provider order if needed."
            ),
        )

    candidate_providers = tuple(
        available_providers[provider_name]
        for provider_name in policy.get_provider_order()
        if provider_name in available_providers
    )

    if not candidate_providers:
        raise ResolverError(
            f"tool '{resolved_tool.name}' has no available providers allowed by policy",
            suggestion=(
                "Update qenv/policies/policy.yaml so an available provider is allowed for this tool."
            ),
        )

    blocked_by_policy: list[str] = []
    blocked_by_sudo: list[str] = []
    for provider in candidate_providers:
        try:
            provider_backend = get_provider(provider.name)
        except ProviderError as exc:
            raise ResolverError(str(exc)) from exc

        if provider_backend.requires_sudo and not policy.allows_sudo():
            blocked_by_policy.append(provider.name)
            continue

        if provider_backend.requires_sudo and not (host.sudo_available or host.is_root):
            blocked_by_sudo.append(provider.name)
            continue

        return provider

    if blocked_by_policy and len(blocked_by_policy) == len(candidate_providers):
        raise ResolverError(
            f"tool '{resolved_tool.name}' has only sudo-capable providers available, "
            "but policy disallows sudo installs",
            suggestion=(
                "Allow sudo installs in qenv/policies/policy.yaml or add a user-level provider "
                "for this tool."
            ),
        )

    if blocked_by_sudo and len(blocked_by_sudo) == len(candidate_providers):
        provider_names = ", ".join(blocked_by_sudo)
        raise ResolverError(
            f"tool '{resolved_tool.name}' requires sudo for available providers "
            f"({provider_names}), but sudo is not available",
            suggestion=(
                "Use an account with sudo access or add a user-level provider for this tool."
            ),
        )

    raise ResolverError(f"tool '{resolved_tool.name}' has no suitable provider")


def create_install_plan(
    package_metadata: PackageMetadata,
    host: HostInfo,
    policy: Policy,
    registry: Registry,
) -> InstallPlan:
    installed_tools: list[ToolDefinition] = []
    tools_to_install: list[PlannedToolInstall] = []

    for tool_name in package_metadata.required_tools:
        tool = registry.get_tool(tool_name)
        if is_tool_installed(tool):
            installed_tools.append(tool)
            continue

        if not policy.is_install_enabled():
            raise ResolverError(
                f"tool '{tool.name}' is required by package '{package_metadata.name}', "
                "but installs are disabled by policy",
                suggestion=(
                    "Enable installs in qenv/policies/policy.yaml or install the tool manually "
                    f"before rerunning qenv apply {package_metadata.name}."
                ),
            )

        provider = resolve_provider(tool, host, policy, registry)
        tools_to_install.append(PlannedToolInstall(tool=tool, provider=provider))

    return InstallPlan(
        package=package_metadata,
        installed_tools=tuple(installed_tools),
        tools_to_install=tuple(tools_to_install),
    )