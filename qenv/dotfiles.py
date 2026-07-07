from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping

from yamlutil import load_yaml_mapping


DOTFILES_ENV_VAR = "DOTFILES"
DEFAULT_DOTFILES_PATH = Path("~/.dotfiles").expanduser()
QENV_CONFIG_FILE = "qenv.yaml"


class DotfilesError(RuntimeError):
    """Base error for qenv dotfiles discovery failures."""


class DotfilesNotFoundError(DotfilesError):
    """Raised when the dotfiles repository cannot be located."""


class ConfigError(DotfilesError):
    """Raised when qenv.yaml is missing or invalid."""


def find_dotfiles_root(environ: Mapping[str, str] | None = None) -> Path:
    environment = os.environ if environ is None else environ

    env_root = environment.get(DOTFILES_ENV_VAR)
    if env_root:
        return _validate_dotfiles_root(
            Path(env_root).expanduser(),
            source=f"${DOTFILES_ENV_VAR}",
        )

    module_root = Path(__file__).resolve().parent.parent
    if _looks_like_dotfiles_root(module_root):
        return module_root

    if _looks_like_dotfiles_root(DEFAULT_DOTFILES_PATH):
        return DEFAULT_DOTFILES_PATH.resolve()

    raise DotfilesNotFoundError(
        "unable to locate dotfiles repo. Set DOTFILES or clone to ~/.dotfiles."
    )


def load_qenv_yaml(dotfiles_root: Path | None = None) -> dict[str, Any]:
    root = (
        find_dotfiles_root()
        if dotfiles_root is None
        else _validate_dotfiles_root(dotfiles_root, source="argument")
    )
    config_path = root / QENV_CONFIG_FILE

    config = load_yaml_mapping(config_path, error_type=ConfigError)
    _validate_qenv_config(config, config_path)
    return config


def _looks_like_dotfiles_root(path: Path) -> bool:
    return path.is_dir() and (path / QENV_CONFIG_FILE).is_file() and (path / "qenv").is_dir()


def _validate_dotfiles_root(path: Path, source: str) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.is_dir():
        raise DotfilesNotFoundError(f"{source} does not point to a directory: {path}")

    if not _looks_like_dotfiles_root(resolved):
        raise DotfilesNotFoundError(
            f"{source} does not point to a qenv repo: missing {resolved / QENV_CONFIG_FILE}"
        )

    return resolved
def _validate_qenv_config(config: dict[str, Any], config_path: Path) -> None:
    if "version" not in config:
        raise ConfigError(f"{config_path} is missing 'version'")

    stow = config.get("stow")
    if not isinstance(stow, dict):
        raise ConfigError(f"{config_path} is missing the 'stow' mapping")

    for key in ("target", "directory"):
        value = stow.get(key)
        if not isinstance(value, str) or not value:
            raise ConfigError(f"{config_path} is missing stow.{key}")