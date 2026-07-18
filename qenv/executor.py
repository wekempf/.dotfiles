from __future__ import annotations

from dataclasses import dataclass
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from dotfiles import find_dotfiles_root
from host import HostInfo
from packages import PackageMetadata
from providers import ProviderError, get_provider
from resolver import InstallPlan
from ui import UI


IGNORE_FILE_NAME = ".stow-local-ignore"
DIRECTORY_LINK_SUFFIX = ".link"


class ExecutorError(RuntimeError):
    """Raised when qenv cannot execute an install plan or reconcile package links."""

    def __init__(self, message: str, suggestion: str | None = None):
        super().__init__(message)
        self.suggestion = suggestion


@dataclass(frozen=True)
class InstallFailure:
    tool_name: str
    provider_name: str
    package_name: str
    error: str


@dataclass(frozen=True)
class ExecutionSummary:
    processed_tools: tuple[str, ...]
    failed_tools: tuple[InstallFailure, ...]


@dataclass(frozen=True)
class LinkEntry:
    source: Path
    target: Path
    is_directory: bool


def execute_install_plan(
    plan: InstallPlan,
    host: HostInfo,
    ui: UI,
    dry_run: bool = False,
    force: bool = False,
    start_step: int = 1,
    total_steps: int | None = None,
) -> ExecutionSummary:
    processed_tools: list[str] = []
    failed_tools: list[InstallFailure] = []
    step_total = total_steps if total_steps is not None else len(plan.tools_to_install)

    for step_index, planned_tool in enumerate(plan.tools_to_install, start=start_step):
        tool_name = planned_tool.tool.name
        provider_name = planned_tool.provider.name
        package_name = planned_tool.provider.package
        ui.step(
            step_index,
            step_total,
            f"install {tool_name} via {provider_name} (package {package_name})",
            dry_run=dry_run,
        )

        if dry_run:
            processed_tools.append(tool_name)
            continue

        try:
            provider = get_provider(provider_name)
            result = provider.install(planned_tool.tool, package_name, host)
        except ProviderError as exc:
            failure = InstallFailure(
                tool_name=tool_name,
                provider_name=provider_name,
                package_name=package_name,
                error=str(exc),
            )
            if force:
                ui.warn(
                    f"Install for {tool_name} failed via {provider_name}; continuing because --force was set."
                )
                ui.detail(str(exc))
                failed_tools.append(failure)
                continue

            raise _install_failure_error(plan.package.name, failure, processed_tools) from exc
        except Exception as exc:
            failure = InstallFailure(
                tool_name=tool_name,
                provider_name=provider_name,
                package_name=package_name,
                error=f"provider '{provider_name}' failed while installing tool '{tool_name}': {exc}",
            )
            if force:
                ui.warn(
                    f"Install for {tool_name} failed via {provider_name}; continuing because --force was set."
                )
                ui.detail(str(exc))
                failed_tools.append(failure)
                continue

            raise _install_failure_error(plan.package.name, failure, processed_tools) from exc

        ui.command_output(result.stdout)
        ui.command_output(result.stderr, stderr=True)
        ui.success(f"Installed {tool_name}.")
        processed_tools.append(tool_name)

    return ExecutionSummary(
        processed_tools=tuple(processed_tools),
        failed_tools=tuple(failed_tools),
    )


def stow_package(
    package_metadata: PackageMetadata,
    config: dict[str, Any],
    ui: UI,
    dotfiles_root: Path | None = None,
    dry_run: bool = False,
    step_index: int | None = None,
    total_steps: int | None = None,
) -> Path | None:
    if not package_metadata.stow_enabled:
        ui.detail(f"Link reconciliation disabled for package '{package_metadata.name}'.")
        return None

    root = find_dotfiles_root() if dotfiles_root is None else dotfiles_root.resolve()
    stow_directory = _resolve_stow_directory(config, root)
    stow_target = _resolve_stow_target(package_metadata, config)
    package_root = (stow_directory / package_metadata.directory_name).resolve()
    if not package_root.is_dir():
        raise ExecutorError(f"package directory does not exist: {package_root}")

    desired_links = _collect_desired_links(package_metadata.name, package_root, stow_target)
    stale_links = _find_stale_links(package_root, stow_target, desired_links)
    _validate_link_plan(package_metadata.name, stow_target, desired_links, stale_links)

    if step_index is not None and total_steps is not None:
        ui.step(
            step_index,
            total_steps,
            f"reconcile package '{package_metadata.name}' to {stow_target}",
            dry_run=dry_run,
        )
    elif dry_run:
        ui.info(f"Would reconcile package '{package_metadata.name}' to {stow_target}.")
    else:
        ui.info(f"Reconciling package '{package_metadata.name}' to {stow_target}.")

    if desired_links:
        ui.detail(f"planned links: {len(desired_links)}")
    if stale_links:
        ui.detail(f"stale owned links to remove: {len(stale_links)}")

    if dry_run:
        for entry in sorted(desired_links.values(), key=lambda item: str(item.target)):
            ui.detail(
                f"link {entry.target} -> {entry.source}"
                f" ({'directory' if entry.is_directory else 'file'})"
            )
        for path in sorted(stale_links, key=str):
            ui.detail(f"remove stale link {path}")
    else:
        try:
            _apply_link_plan(stow_target, desired_links, stale_links)
        except OSError as exc:
            raise ExecutorError(
                f"reconcile package '{package_metadata.name}' failed while updating links: {exc}",
                suggestion=(
                    "Resolve the target path conflict or filesystem error, then rerun qenv apply "
                    f"{package_metadata.name} --dry-run --verbose. Installed tools are not rolled back automatically."
                ),
            ) from exc

    if dry_run:
        ui.success(f"Link reconciliation preview complete for package '{package_metadata.name}'.")
    else:
        ui.success(f"Package '{package_metadata.name}' reconciled to {stow_target}.")

    return stow_target


def _resolve_stow_directory(config: dict[str, Any], dotfiles_root: Path) -> Path:
    stow_config = config.get("stow")
    if not isinstance(stow_config, dict):
        raise ExecutorError("qenv config is missing the 'stow' mapping")

    directory = stow_config.get("directory")
    if not isinstance(directory, str) or not directory:
        raise ExecutorError("qenv config is missing stow.directory")

    path = Path(directory).expanduser()
    if not path.is_absolute():
        path = (dotfiles_root / path).resolve()

    if not path.is_dir():
        raise ExecutorError(f"stow directory does not exist: {path}")

    return path


def _resolve_stow_target(package_metadata: PackageMetadata, config: dict[str, Any]) -> Path:
    target = package_metadata.stow_target
    if not target:
        stow_config = config.get("stow")
        if not isinstance(stow_config, dict):
            raise ExecutorError("qenv config is missing the 'stow' mapping")

        target = stow_config.get("target")

    if not isinstance(target, str) or not target:
        raise ExecutorError(f"package '{package_metadata.name}' is missing a stow target")

    return Path(target).expanduser()


def _collect_desired_links(
    package_name: str,
    package_root: Path,
    target_root: Path,
) -> dict[Path, LinkEntry]:
    patterns = _load_ignore_patterns(package_root)
    desired_links: dict[Path, LinkEntry] = {}

    def walk(directory: Path) -> None:
        for child in sorted(directory.iterdir(), key=lambda path: path.name):
            relative_path = child.relative_to(package_root)
            if _should_ignore(relative_path, patterns):
                continue

            if child.is_dir() and not child.is_symlink():
                if child.name.endswith(DIRECTORY_LINK_SUFFIX):
                    link_name = child.name[: -len(DIRECTORY_LINK_SUFFIX)]
                    if not link_name:
                        raise ExecutorError(
                            f"package '{package_name}' contains an invalid directory link name: {child}"
                        )

                    target_path = target_root / relative_path.parent / link_name
                    _add_desired_link(
                        package_name,
                        desired_links,
                        target_path,
                        child,
                        is_directory=True,
                    )
                    continue

                walk(child)
                continue

            if child.is_file() or child.is_symlink():
                _add_desired_link(
                    package_name,
                    desired_links,
                    target_root / relative_path,
                    child,
                    is_directory=False,
                )

    walk(package_root)
    return desired_links


def _load_ignore_patterns(package_root: Path) -> tuple[re.Pattern[str], ...]:
    ignore_file = package_root / IGNORE_FILE_NAME
    if not ignore_file.is_file():
        return ()

    patterns: list[re.Pattern[str]] = []
    for raw_line in ignore_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        try:
            patterns.append(re.compile(line))
        except re.error as exc:
            raise ExecutorError(f"invalid ignore pattern in {ignore_file}: {line} ({exc})") from exc

    return tuple(patterns)


def _should_ignore(relative_path: Path, patterns: tuple[re.Pattern[str], ...]) -> bool:
    if relative_path.name == IGNORE_FILE_NAME:
        return True

    candidate = "/" + relative_path.as_posix()
    return any(pattern.search(candidate) for pattern in patterns)


def _add_desired_link(
    package_name: str,
    desired_links: dict[Path, LinkEntry],
    target: Path,
    source: Path,
    *,
    is_directory: bool,
) -> None:
    existing = desired_links.get(target)
    if existing is not None:
        raise ExecutorError(
            f"package '{package_name}' maps multiple sources to the same target: {target}"
        )

    desired_links[target] = LinkEntry(
        source=source,
        target=target,
        is_directory=is_directory,
    )


def _find_stale_links(
    package_root: Path,
    target_root: Path,
    desired_links: dict[Path, LinkEntry],
) -> tuple[Path, ...]:
    if not _path_exists(target_root):
        return ()

    stale_links: list[Path] = []
    for path in _iter_symlinks(target_root):
        desired = desired_links.get(path)
        if desired is not None and _symlink_matches(path, desired.source):
            continue

        if _points_into_package(path, package_root):
            stale_links.append(path)

    return tuple(sorted(stale_links, key=lambda path: (-len(path.parts), str(path))))


def _iter_symlinks(root: Path):
    if root.is_symlink():
        yield root
        return

    if not root.exists():
        return

    for current_root, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current_root)
        for name in sorted(dirnames):
            child = current_path / name
            if child.is_symlink():
                yield child

        for name in sorted(filenames):
            child = current_path / name
            if child.is_symlink():
                yield child


def _validate_link_plan(
    package_name: str,
    target_root: Path,
    desired_links: dict[Path, LinkEntry],
    stale_links: tuple[Path, ...],
) -> None:
    removal_targets = set(stale_links)

    for entry in sorted(desired_links.values(), key=lambda item: (len(item.target.parts), str(item.target))):
        _validate_target_ancestors(package_name, target_root, entry.target, removal_targets)

        if entry.target in removal_targets:
            continue

        if entry.target.is_symlink():
            if _symlink_matches(entry.target, entry.source):
                continue

            raise ExecutorError(
                f"package '{package_name}' cannot link {entry.target}: existing symlink points elsewhere"
            )

        if not entry.target.exists():
            continue

        if entry.is_directory and entry.target.is_dir() and _directory_will_be_empty(entry.target, removal_targets):
            continue

        raise ExecutorError(
            f"package '{package_name}' cannot link {entry.target}: target already exists"
        )


def _validate_target_ancestors(
    package_name: str,
    target_root: Path,
    target: Path,
    removal_targets: set[Path],
) -> None:
    current = target.parent
    ancestors: list[Path] = []
    while current != target_root and current != current.parent:
        ancestors.append(current)
        current = current.parent

    for ancestor in reversed(ancestors):
        if ancestor in removal_targets:
            continue

        if ancestor.is_symlink():
            raise ExecutorError(
                f"package '{package_name}' cannot link {target}: ancestor is a symlink ({ancestor})"
            )

        if _path_exists(ancestor) and not ancestor.is_dir():
            raise ExecutorError(
                f"package '{package_name}' cannot link {target}: ancestor is not a directory ({ancestor})"
            )


def _directory_will_be_empty(path: Path, removal_targets: set[Path]) -> bool:
    if path.is_symlink() or not path.is_dir():
        return False

    for child in path.iterdir():
        if child in removal_targets:
            continue

        if child.is_dir() and not child.is_symlink() and _directory_will_be_empty(child, removal_targets):
            continue

        return False

    return True


def _apply_link_plan(
    target_root: Path,
    desired_links: dict[Path, LinkEntry],
    stale_links: tuple[Path, ...],
) -> None:
    for path in stale_links:
        path.unlink()
        _remove_empty_ancestors(path.parent, target_root)

    for entry in sorted(desired_links.values(), key=lambda item: (len(item.target.parts), str(item.target))):
        if entry.target.is_symlink() and _symlink_matches(entry.target, entry.source):
            continue

        if entry.target.exists() and entry.is_directory and entry.target.is_dir():
            _remove_empty_ancestors(entry.target, target_root, include_start=True)

        entry.target.parent.mkdir(parents=True, exist_ok=True)
        link_target = os.path.relpath(entry.source, start=entry.target.parent)
        entry.target.symlink_to(link_target, target_is_directory=entry.is_directory)


def _remove_empty_ancestors(
    start: Path,
    target_root: Path,
    *,
    include_start: bool = False,
) -> None:
    current = start if include_start else start
    while current != target_root and current != current.parent:
        if not current.exists() or current.is_symlink() or not current.is_dir():
            break

        try:
            current.rmdir()
        except OSError:
            break

        current = current.parent


def _path_exists(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def _points_into_package(link_path: Path, package_root: Path) -> bool:
    try:
        target_path = _symlink_target_path(link_path)
    except OSError:
        return False

    return target_path.is_relative_to(_normalize_path(package_root))


def _symlink_matches(link_path: Path, expected_source: Path) -> bool:
    try:
        return _symlink_target_path(link_path) == _normalize_path(expected_source)
    except OSError:
        return False


def _symlink_target_path(link_path: Path) -> Path:
    target_text = os.readlink(link_path)
    target_path = Path(target_text)
    if not target_path.is_absolute():
        target_path = link_path.parent / target_path

    return _normalize_path(target_path)


def _normalize_path(path: Path) -> Path:
    return Path(os.path.normpath(str(path)))


def _install_failure_error(
    apply_package_name: str,
    failure: InstallFailure,
    processed_tools: list[str],
) -> ExecutorError:
    completed = ", ".join(processed_tools) if processed_tools else "none"
    return ExecutorError(
        f"install tool '{failure.tool_name}' via provider '{failure.provider_name}' failed: "
        f"{failure.error}. Completed installs before failure: {completed}.",
        suggestion=(
            f"Review the provider failure, then rerun qenv apply {apply_package_name} --dry-run --verbose. "
            "Installed tools are not rolled back automatically. Use --force to continue with later apply steps."
        ),
    )