from __future__ import annotations

from .base import CommandProvider


class MiseProvider(CommandProvider):
    name = "mise"
    executable_names = ("mise",)
    install_args = ("install",)
    requires_sudo = False