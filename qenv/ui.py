from __future__ import annotations

import os
import sys
from typing import TextIO


_RESET = "\033[0m"
_BOLD = "\033[1m"
_COLORS = {
    "blue": "\033[34m",
    "cyan": "\033[36m",
    "green": "\033[32m",
    "magenta": "\033[35m",
    "red": "\033[31m",
    "yellow": "\033[33m",
}


class UI:
    def __init__(
        self,
        *,
        verbose: bool = False,
        color: bool | None = None,
        stdout: TextIO = sys.stdout,
        stderr: TextIO = sys.stderr,
    ) -> None:
        self.verbose = verbose
        self.stdout = stdout
        self.stderr = stderr
        self.color = _supports_color(stdout) if color is None else color

    def heading(self, text: str) -> None:
        print(self._style(text, color="blue", bold=True), file=self.stdout)

    def info(self, text: str) -> None:
        self._emit("info", text, color="cyan", stream=self.stdout)

    def success(self, text: str) -> None:
        self._emit("ok", text, color="green", stream=self.stdout)

    def warn(self, text: str) -> None:
        self._emit("warn", text, color="yellow", stream=self.stdout)

    def error(self, text: str) -> None:
        self._emit("error", text, color="red", stream=self.stderr)

    def hint(self, text: str) -> None:
        self._emit("hint", text, color="yellow", stream=self.stderr)

    def detail(self, text: str) -> None:
        if self.verbose:
            print(f"  {text}", file=self.stdout)

    def list_item(self, text: str) -> None:
        print(f"  - {text}", file=self.stdout)

    def step(self, current: int, total: int, text: str, *, dry_run: bool = False) -> None:
        prefix = self._style(f"[{current}/{total}]", color="magenta", bold=True)
        verb = "Would" if dry_run else "Run"
        print(f"{prefix} {verb} {text}", file=self.stdout)

    def command_output(self, text: str, *, stderr: bool = False) -> None:
        if not self.verbose:
            return

        content = text.strip()
        if not content:
            return

        stream = self.stderr if stderr else self.stdout
        for line in content.splitlines():
            print(f"    {line}", file=stream)

    def _emit(self, label: str, text: str, *, color: str, stream: TextIO) -> None:
        rendered_label = self._style(label, color=color, bold=True)
        print(f"{rendered_label}: {text}", file=stream)

    def _style(self, text: str, *, color: str, bold: bool = False) -> str:
        if not self.color:
            return text

        parts = []
        if bold:
            parts.append(_BOLD)

        parts.append(_COLORS[color])
        parts.append(text)
        parts.append(_RESET)
        return "".join(parts)


def _supports_color(stream: TextIO) -> bool:
    if os.environ.get("NO_COLOR") is not None:
        return False

    if os.environ.get("TERM", "dumb") == "dumb":
        return False

    return hasattr(stream, "isatty") and stream.isatty()