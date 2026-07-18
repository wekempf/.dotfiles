from __future__ import annotations

from .base import CommandProvider


class BrewProvider(CommandProvider):
    name = "brew"
    executable_names = ("brew",)
    install_args = ("install",)
    requires_sudo = False