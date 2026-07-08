from __future__ import annotations

import argparse
import sys

from dotfiles import ConfigError, DotfilesNotFoundError, find_dotfiles_root, load_qenv_yaml
from executor import ExecutorError, execute_install_plan, stow_package
from host import detect_host_info
from packages import PackageError, find_packages, load_package_metadata
from policy import PolicyError, load_policy
from providers import ProviderError, list_providers
from registry import RegistryError, load_registry
from resolver import ResolverError, create_install_plan
from ui import UI


VERSION = "0.1.0"


def _help_handler(parser: argparse.ArgumentParser):
    def handler(_: argparse.Namespace) -> int:
        parser.print_help()
        return 0

    return handler


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="qenv",
        description="qenv manages this dotfiles repository.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {VERSION}",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show satisfied checks and command output for apply steps.",
    )

    subparsers = parser.add_subparsers(dest="command", metavar="command")

    apply_parser = subparsers.add_parser(
        "apply",
        help="Apply a dotfiles package.",
    )
    apply_parser.add_argument("package", help="Package name to apply.")
    apply_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without installing tools or changing stow links.",
    )
    apply_parser.add_argument(
        "--force",
        action="store_true",
        help="Continue to later apply steps after tool installation failures when possible.",
    )
    apply_parser.set_defaults(handler=handle_apply)

    host_parser = subparsers.add_parser(
        "host",
        help="Inspect host details.",
    )
    host_parser.set_defaults(handler=_help_handler(host_parser))

    host_subparsers = host_parser.add_subparsers(dest="host_command", metavar="host_command")

    host_show_parser = host_subparsers.add_parser(
        "show",
        help="Display host information.",
    )
    host_show_parser.set_defaults(handler=handle_host_show)

    package_parser = subparsers.add_parser(
        "package",
        help="Inspect qenv packages.",
    )
    package_parser.set_defaults(handler=_help_handler(package_parser))

    package_subparsers = package_parser.add_subparsers(
        dest="package_command",
        metavar="package_command",
    )

    package_list_parser = package_subparsers.add_parser(
        "list",
        help="List packages with qenv metadata.",
    )
    package_list_parser.set_defaults(handler=handle_package_list)

    return parser


def handle_apply(args: argparse.Namespace) -> int:
    ui = args.ui
    dotfiles_root = find_dotfiles_root()
    config = load_qenv_yaml(dotfiles_root)
    policy = load_policy(dotfiles_root)
    registry = load_registry(dotfiles_root)
    package_metadata = load_package_metadata(args.package, dotfiles_root)
    host_info = detect_host_info()
    plan = create_install_plan(package_metadata, host_info, policy, registry)
    total_steps = len(plan.tools_to_install) + (1 if package_metadata.stow_enabled else 0)

    ui.heading(
        f"{'Planning' if args.dry_run else 'Applying'} package '{plan.package.name}'"
    )
    if args.verbose:
        ui.detail(f"dotfiles root: {dotfiles_root}")
        ui.detail(f"stow target: {package_metadata.stow_target}")
        ui.detail(
            f"host: {host_info.operating_system}/{host_info.distro or 'n/a'} "
            f"[{host_info.architecture}]"
        )

    if plan.tools_to_install:
        ui.info("Tool changes:")
        for planned_tool in plan.tools_to_install:
            ui.list_item(
                f"install {planned_tool.tool.name} via {planned_tool.provider.name} "
                f"(package {planned_tool.provider.package})"
            )

    if args.verbose and plan.installed_tools:
        installed_tool_names = ", ".join(tool.name for tool in plan.installed_tools)
        ui.info(f"Already installed: {installed_tool_names}")

    if total_steps == 0:
        ui.success(f"No changes required for package '{package_metadata.name}'.")
        return 0

    if args.dry_run:
        ui.warn("Dry run mode: no changes will be applied.")

    if args.force:
        ui.warn("Force mode: qenv will continue after tool installation failures when possible.")

    execution = execute_install_plan(
        plan,
        host_info,
        ui,
        dry_run=args.dry_run,
        force=args.force,
        total_steps=total_steps,
    )

    if execution.failed_tools:
        ui.warn(
            f"{len(execution.failed_tools)} tool installation failure(s) were ignored because --force was set."
        )
        for failure in execution.failed_tools:
            ui.detail(
                f"{failure.tool_name} via {failure.provider_name}: {failure.error}"
            )

    stow_step_index = len(plan.tools_to_install) + 1
    stow_package(
        package_metadata,
        config,
        ui,
        dotfiles_root=dotfiles_root,
        dry_run=args.dry_run,
        step_index=stow_step_index if package_metadata.stow_enabled else None,
        total_steps=total_steps if package_metadata.stow_enabled else None,
    )

    if args.dry_run:
        ui.success(f"Dry run complete for package '{package_metadata.name}'.")
    elif execution.failed_tools:
        ui.warn(f"Applied package '{package_metadata.name}' with warnings.")
    else:
        ui.success(f"Applied package '{package_metadata.name}'.")

    return 0


def handle_host_show(args: argparse.Namespace) -> int:
    host_info = detect_host_info()
    package_managers = ", ".join(host_info.package_managers) if host_info.package_managers else "none"
    distro = host_info.distro if host_info.distro is not None else "n/a"
    sudo_available = "yes" if host_info.sudo_available else "no"

    print(f"OS: {host_info.operating_system}")
    print(f"Distro: {distro}")
    print(f"Architecture: {host_info.architecture}")
    print(f"Package Managers: {package_managers}")
    print(f"Sudo Available: {sudo_available}")
    if args.verbose:
        dotfiles_root = find_dotfiles_root()
        providers = ", ".join(list_providers()) or "none"
        print(f"Dotfiles Root: {dotfiles_root}")
        print(f"Discovered Providers: {providers}")
    return 0


def handle_package_list(args: argparse.Namespace) -> int:
    packages = find_packages()
    if not packages:
        print("No packages found.")
        return 0

    for package in packages:
        required_tools = ", ".join(package.required_tools) if package.required_tools else "none"
        print(f"{package.name}: {package.description}")
        print(f"  required tools: {required_tools}")
        if args.verbose:
            print(f"  stow enabled: {'yes' if package.stow_enabled else 'no'}")
            print(f"  stow target: {package.stow_target}")

    return 0


def _format_error_suggestion(exc: Exception, args: argparse.Namespace) -> str | None:
    suggestion = getattr(exc, "suggestion", None)
    if isinstance(suggestion, str) and suggestion:
        return suggestion

    package_name = getattr(args, "package", "<package>")

    if isinstance(exc, ConfigError):
        return f"Fix qenv.yaml, then rerun qenv apply {package_name} --dry-run --verbose."

    if isinstance(exc, DotfilesNotFoundError):
        return "Set DOTFILES to this repo root or clone the repo to ~/.dotfiles before rerunning qenv."

    if isinstance(exc, PackageError):
        if "unknown package" in str(exc):
            return "Run qenv package list to see available package names."

        return (
            f"Create or fix {package_name}/.qenv/package.yaml and make sure .stow-local-ignore "
            "excludes .qenv metadata."
        )

    if isinstance(exc, PolicyError):
        return "Fix qenv/policies/policy.yaml, then rerun the command with --dry-run to preview the result."

    if isinstance(exc, RegistryError):
        return "Fix qenv/registry.yaml so each required tool has commands and provider mappings."

    if isinstance(exc, ProviderError):
        return "Fix the provider name in the registry or add a matching backend under qenv/providers/."

    if isinstance(exc, ResolverError):
        return (
            f"Review provider availability and policy settings, then rerun qenv apply {package_name} --dry-run --verbose."
        )

    if isinstance(exc, ExecutorError):
        return (
            f"Review the failing step, then rerun qenv apply {package_name} --dry-run --verbose before retrying."
        )

    return None


def _report_error(exc: Exception, args: argparse.Namespace) -> None:
    ui = getattr(args, "ui", UI())
    ui.error(f"qenv: {exc}")
    suggestion = _format_error_suggestion(exc, args)
    if suggestion:
        ui.hint(suggestion)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.ui = UI(verbose=getattr(args, "verbose", False))

    if not hasattr(args, "handler"):
        parser.print_help()
        return 0

    try:
        return args.handler(args)
    except (
        ConfigError,
        DotfilesNotFoundError,
        ExecutorError,
        PackageError,
        PolicyError,
        ProviderError,
        RegistryError,
        ResolverError,
    ) as exc:
        _report_error(exc, args)
        return 1
    except KeyboardInterrupt:
        _report_error(RuntimeError("interrupted"), args)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())