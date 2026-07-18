from __future__ import annotations

from .base import CommandProvider


class DnfProvider(CommandProvider):
    name = "dnf"
    executable_names = ("dnf",)
    install_args = ("install", "-y")
    requires_sudo = True