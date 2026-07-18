from __future__ import annotations

import importlib
import inspect
from functools import lru_cache
from pathlib import Path

from .base import Provider, ProviderError, UnknownProviderError


_IGNORED_MODULES = frozenset({"__init__", "base"})


@lru_cache(maxsize=1)
def _load_provider_types() -> dict[str, type[Provider]]:
    package_dir = Path(__file__).resolve().parent
    provider_types: dict[str, type[Provider]] = {}

    for module_path in sorted(package_dir.glob("*.py"), key=lambda path: path.name):
        module_name = module_path.stem
        if module_name in _IGNORED_MODULES:
            continue

        try:
            module = importlib.import_module(f"{__name__}.{module_name}")
        except Exception as exc:  # pragma: no cover - defensive import boundary
            raise ProviderError(
                f"failed to load provider module '{module_name}': {exc}"
            ) from exc

        for _, provider_type in inspect.getmembers(module, inspect.isclass):
            if provider_type.__module__ != module.__name__:
                continue

            if not issubclass(provider_type, Provider) or inspect.isabstract(provider_type):
                continue

            provider_name = provider_type.name
            if not provider_name:
                raise ProviderError(
                    f"provider module '{module_name}' defines a provider without a name"
                )

            if provider_name in provider_types:
                raise ProviderError(f"duplicate provider '{provider_name}'")

            provider_types[provider_name] = provider_type

    return provider_types


def list_providers() -> tuple[str, ...]:
    return tuple(sorted(_load_provider_types()))


def get_provider(provider_name: str) -> Provider:
    try:
        provider_type = _load_provider_types()[provider_name]
    except KeyError as exc:
        raise UnknownProviderError(f"unknown provider '{provider_name}'") from exc

    return provider_type()