from __future__ import annotations

from .base import CommandProvider


class PacmanProvider(CommandProvider):
    name = "pacman"
    executable_names = ("pacman",)
    install_args = ("-S", "--noconfirm")
    requires_sudo = True