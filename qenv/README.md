# qenv

qenv is a repo-local environment manager for this dotfiles repository. It resolves required tools for a package, installs missing tools through provider backends, and reconciles the package links into the target home directory.

## Overview

qenv is built for a dotfiles workflow where configuration packages may depend on system tools. Instead of manually remembering install steps for every package, qenv lets the repository describe those requirements and apply them consistently.

Current responsibilities include:

- locating the dotfiles repository
- loading qenv configuration, policy, package metadata, and the tool registry
- detecting host capabilities such as package managers and sudo availability
- resolving missing tools to install providers
- executing installs through provider backends
- reconciling package links into the configured target directory

## Getting Started

### Prerequisites

qenv expects:

- Python 3
- a clone of this dotfiles repository

The bootstrap script installs the minimum prerequisites when possible.

### Bootstrap

From the repository root, run:

```sh
./bootstrap.sh
```

Bootstrap special-cases Python 3 as the only stage-0 dependency, then uses qenv itself to ensure GNU Stow is installed, links the qenv launcher into `${XDG_BIN_HOME:-$HOME/.local/bin}`, and stops after the environment is ready.
Bootstrap special-cases Python 3 as the only stage-0 dependency, then uses qenv itself for any remaining bootstrap-managed tools, links the qenv launcher into `${XDG_BIN_HOME:-$HOME/.local/bin}`, and stops after the environment is ready.

If `${XDG_BIN_HOME:-$HOME/.local/bin}` is not already on `PATH`, add it in your shell profile before invoking `qenv` directly.

### First Commands

Inspect the current host:

```sh
qenv host show
```

List managed packages:

```sh
qenv package list
```

Preview a package apply without changing the system:

```sh
qenv apply bat --dry-run
```

Apply a package for real:

```sh
qenv apply zsh
```

Show extra detail during planning and execution:

```sh
qenv --verbose apply zsh --dry-run
```

Continue past tool installation failures when you still want later apply steps, such as link reconciliation, to run:

```sh
qenv apply zsh --force
```

`--force` only continues past tool installation failures during execution. It does not bypass configuration, resolution, or link-reconciliation failures.

## Detailed Documentation

### Command Reference

qenv currently exposes these user-facing commands:

```sh
qenv host show
qenv package list
qenv apply <package>
```

Useful flags:

- `--verbose` shows satisfied checks and command output for apply steps
- `--dry-run` previews changes without modifying the system
- `--force` continues past tool installation failures when later steps can still run

### Apply Flow

`qenv apply <package>` currently performs the following sequence:

1. Locate the dotfiles repository.
2. Load `qenv.yaml`.
3. Load `qenv/policies/policy.yaml`.
4. Load `qenv/registry.yaml`.
5. Load `<package>/.qenv/package.yaml`.
6. Detect host capabilities.
7. Resolve required tools that are missing.
8. Install missing tools through the selected provider backend.
9. Reconcile the package links into the configured target.

By default, output focuses on planned or executed changes. Use `--verbose` when you want command output, satisfied checks, and additional environment detail.

### Configuration

qenv reads repository-level configuration from `qenv.yaml`.

Minimal supported configuration:

```yaml
version: 1

stow:
  target: "~"
  directory: "."
```

`stow.target` controls the destination directory for package links. `stow.directory` controls the repository-relative directory qenv scans when building the desired link set.

### Policy

qenv reads install policy from `qenv/policies/policy.yaml`.

Minimal supported policy:

```yaml
version: 1

install:
  global:
    enabled: true
    allow_sudo: true

providers:
  order:
    - apt
    - dnf
    - pacman
    - brew
    - mise
```

The provider order controls how qenv chooses between multiple available providers for the same tool.

### Package Metadata

Each managed package lives at a top-level directory in the repo and must include `.qenv/package.yaml`.

Minimal supported schema:

```yaml
version: 1

package:
  name: zsh
  description: "Zsh shell configuration"

requires:
  tools:
    required:
      - tool: zsh

stow:
  enabled: true
  target: "~"
```

The package-local `.stow-local-ignore` file should ignore qenv metadata so qenv never links it into the target home directory:

```text
^\.qenv$
^\.qenv/.*$
```

### Tool Registry

The tool registry lives in `qenv/registry.yaml`. Packages reference semantic tool names from this file, not provider-specific package names.

Example entry:

```yaml
version: 1

tools:
  ripgrep:
    commands:
      - rg
    providers:
      apt:
        package: ripgrep
      dnf:
        package: ripgrep
      pacman:
        package: ripgrep
      brew:
        package: ripgrep
```

To add a new tool:

1. Add a new entry under `tools` in `qenv/registry.yaml`.
2. List the commands qenv should use to detect whether the tool is already installed.
3. Add provider mappings for every backend that can install it.
4. Reference the tool name from package metadata under `requires.tools.required`.

### Providers

Provider backends live in `qenv/providers/`. qenv discovers providers dynamically by scanning Python modules in that directory, so adding a new provider does not require editing a hard-coded provider list.

Provider modules should expose a concrete subclass of the shared provider base with:

- `name`
- `requires_sudo`
- `is_available(host)`
- `install(tool, package_name, host)`

Built-in provider modules currently include:

- `apt`
- `dnf`
- `pacman`
- `brew`
- `mise`

To add a custom provider:

1. Create `qenv/providers/<provider_name>.py`.
2. Implement a concrete provider subclass.
3. Add the provider name to `qenv/policies/policy.yaml` if it should participate in provider selection order.
4. Reference the provider under a tool entry in `qenv/registry.yaml`.

### Output and Recovery

Default apply output focuses on changes. Use `--verbose` to include satisfied items and command output from provider installs and link reconciliation.

Use `--dry-run` before a real apply when debugging provider selection, link targets, or policy behavior.

When qenv fails, it tries to return both the immediate error and a next-step hint. Use the hint first, then rerun with `--dry-run --verbose` if you need to inspect resolution or execution details.

## Contributing

Contributions should keep qenv focused on the repository workflow: resolve package requirements, install tools through providers, and apply package links predictably.

When making changes:

1. Start with the smallest affected module.
2. Prefer updating the owning abstraction instead of layering special-case behavior in the CLI.
3. Keep provider behavior dynamic so new provider modules can be added without changing a hard-coded list.
4. Validate changes with the narrowest relevant command, such as `qenv host show`, `qenv package list`, or `qenv apply <package> --dry-run`.
5. Update this README or package metadata examples when the user-facing workflow changes.

Useful development checks from the repository root:

```sh
python3 qenv/__main__.py host show
python3 qenv/__main__.py package list
python3 qenv/__main__.py apply bat --dry-run
python3 qenv/__main__.py --verbose apply zsh --dry-run
```

If you add a provider backend, validate both discovery and behavior by checking verbose host output and a dry-run apply for a package that can resolve through that provider.

## Project Status

qenv is currently an MVP-oriented tool inside this dotfiles repository. The current implementation covers package discovery, tool resolution, dynamic provider loading, install execution, native POSIX link reconciliation, verbose output, and recovery hints. Cross-platform validation outside the current Linux environment remains ongoing.