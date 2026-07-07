from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotfiles import find_dotfiles_root
from yamlutil import load_yaml_mapping


POLICY_FILE = Path("qenv/policies/policy.yaml")


class PolicyError(RuntimeError):
    """Raised when policy configuration is missing or invalid."""


@dataclass(frozen=True)
class Policy:
    version: int
    install_enabled: bool
    allow_sudo: bool
    provider_order: tuple[str, ...]

    def get_provider_order(self) -> tuple[str, ...]:
        return self.provider_order

    def is_install_enabled(self) -> bool:
        return self.install_enabled

    def allows_sudo(self) -> bool:
        return self.allow_sudo


def load_policy(dotfiles_root: Path | None = None) -> Policy:
    root = find_dotfiles_root() if dotfiles_root is None else dotfiles_root.resolve()
    config_path = root / POLICY_FILE
    config = load_yaml_mapping(config_path, error_type=PolicyError)
    return _validate_policy(config, config_path)


def _validate_policy(config: dict[str, Any], config_path: Path) -> Policy:
    version = config.get("version")
    if not isinstance(version, int):
        raise PolicyError(f"{config_path} is missing an integer 'version'")

    install = _expect_mapping(config, "install", config_path)
    install_global = _expect_mapping(install, "global", config_path)
    providers = _expect_mapping(config, "providers", config_path)

    install_enabled = _expect_bool(install_global, "enabled", config_path)
    allow_sudo = _expect_bool(install_global, "allow_sudo", config_path)
    provider_order = _expect_string_list(providers, "order", config_path)

    return Policy(
        version=version,
        install_enabled=install_enabled,
        allow_sudo=allow_sudo,
        provider_order=provider_order,
    )


def _expect_mapping(config: dict[str, Any], key: str, config_path: Path) -> dict[str, Any]:
    value = config.get(key)
    if not isinstance(value, dict):
        raise PolicyError(f"{config_path} is missing the '{key}' mapping")

    return value


def _expect_bool(config: dict[str, Any], key: str, config_path: Path) -> bool:
    value = config.get(key)
    if not isinstance(value, bool):
        raise PolicyError(f"{config_path} is missing boolean '{key}'")

    return value


def _expect_string_list(config: dict[str, Any], key: str, config_path: Path) -> tuple[str, ...]:
    value = config.get(key)
    if not isinstance(value, list) or not value:
        raise PolicyError(f"{config_path} is missing list '{key}'")

    items: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item:
            raise PolicyError(f"{config_path} contains an invalid entry in '{key}'")
        items.append(item)

    return tuple(items)