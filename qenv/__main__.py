from __future__ import annotations

import argparse
import sys

from dotfiles import ConfigError, DotfilesNotFoundError, find_dotfiles_root, load_qenv_yaml
from host import detect_host_info
from packages import PackageError, find_packages, load_package_metadata
from policy import PolicyError, load_policy
from registry import RegistryError, load_registry


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

    subparsers = parser.add_subparsers(dest="command", metavar="command")

    apply_parser = subparsers.add_parser(
        "apply",
        help="Apply a dotfiles package.",
    )
    apply_parser.add_argument("package", help="Package name to apply.")
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
    dotfiles_root = find_dotfiles_root()
    load_qenv_yaml(dotfiles_root)
    load_policy(dotfiles_root)
    load_registry(dotfiles_root)
    load_package_metadata(args.package, dotfiles_root)
    print(
        f"qenv apply is not implemented yet for package '{args.package}'.",
        file=sys.stderr,
    )
    return 1


def handle_host_show(_: argparse.Namespace) -> int:
    host_info = detect_host_info()
    package_managers = ", ".join(host_info.package_managers) if host_info.package_managers else "none"
    distro = host_info.distro if host_info.distro is not None else "n/a"
    sudo_available = "yes" if host_info.sudo_available else "no"

    print(f"OS: {host_info.operating_system}")
    print(f"Distro: {distro}")
    print(f"Architecture: {host_info.architecture}")
    print(f"Package Managers: {package_managers}")
    print(f"Sudo Available: {sudo_available}")
    return 0


def handle_package_list(_: argparse.Namespace) -> int:
    packages = find_packages()
    if not packages:
        print("No packages found.")
        return 0

    for package in packages:
        required_tools = ", ".join(package.required_tools) if package.required_tools else "none"
        print(f"{package.name}: {package.description}")
        print(f"  required tools: {required_tools}")

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not hasattr(args, "handler"):
        parser.print_help()
        return 0

    try:
        return args.handler(args)
    except (ConfigError, DotfilesNotFoundError, PackageError, PolicyError, RegistryError) as exc:
        print(f"qenv: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("qenv: interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())