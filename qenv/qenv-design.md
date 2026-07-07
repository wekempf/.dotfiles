# qenv Design Notes

## Overview

`qenv` is a repo-internal environment manager for a Git-backed dotfiles repository. It lives inside `~/.dotfiles` and acts as the orchestration layer for locating the repo, resolving policies, detecting host capabilities, resolving tool dependencies, installing missing tools, applying Stow packages, syncing Git state, and running idempotent post-install actions.

The design center is:

> `qenv` is a policy-aware, dependency-aware, Git-backed dotfiles environment manager built around Stow-compatible packages and semantic tool definitions.

---

## Goals

### Primary Goals

`qenv` should:

1. Live inside the dotfiles repository.
2. Locate the dotfiles repo using `$DOTFILES` or convention.
3. Use declarative metadata for Stow packages.
4. Use a semantic registry for tools.
5. Use hierarchical policies to decide what is allowed and preferred.
6. Detect the current host environment.
7. Resolve package and tool dependencies.
8. Install missing tools if allowed.
9. Stow packages after prerequisites are satisfied.
10. Support required and optional dependencies.
11. Support tool-specific Stow packages.
12. Support post-install/post-apply actions.
13. Be idempotent.
14. Support “what-if” planning that shows only changes.
15. Explain failures clearly.
16. Avoid complex Bash except for minimal bootstrapping.

### Non-Goals

At least initially, `qenv` should not try to become:

- a full Ansible replacement
- a full Nix replacement
- a general-purpose package manager
- a system service manager
- a cross-user enterprise provisioning platform
- a secrets manager
- a generic OS configuration framework

The initial scope should remain:

> dependency-aware dotfile provisioning and synchronization.

---

## Repository Model

`qenv` is part of the dotfiles repo.

Typical location:

```text
~/.dotfiles/
```

The repo is located by:

1. `$DOTFILES`, if set
2. `~/.dotfiles`, if present
3. current Git repo, if command is run from inside the dotfiles repo
4. otherwise, fail with guidance

Example repo structure:

```text
~/.dotfiles/
├── bootstrap.sh
├── bin/
│   ├── .local/
│   │   └── bin/
│   │       ├── dotstow
│   │       ├── dotpull
│   │       ├── dotpush
│   │       └── dotsync
│
├── qenv/
│   ├── qenv
│   ├── pyproject.toml
│   ├── .venv/
│   ├── .stow-local-ignore
│   ├── __main__.py
│   ├── bootstrap.py
│   ├── cli.py
│   ├── dotfiles.py
│   ├── host.py
│   ├── policy.py
│   ├── registry.py
│   ├── packages.py
│   ├── resolver.py
│   ├── planner.py
│   ├── executor.py
│   ├── git.py
│   ├── stow.py
│   ├── state.py
│   ├── plugins/
│   ├── providers/
│   │   ├── apt.py
│   │   ├── dnf.py
│   │   ├── pacman.py
│   │   ├── brew.py
│   │   ├── mise.py
│   │   ├── cargo.py
│   │   ├── uv.py
│   │   ├── git.py
│   │   └── direct.py
│   ├── registry.yaml
│   └── policies/
│       ├── policy.yaml
│       ├── os/
│       │   ├── linux.yaml
│       │   ├── ubuntu.yaml
│       │   ├── fedora.yaml
│       │   └── macos.yaml
│       ├── machines/
│       │   └── example-host.yaml
│       └── local.yaml
│
├── qenv.yaml
├── .stow-local-ignore
├── .gitignore
│
├── zsh/
│   ├── .zshrc
│   └── .qenv/
│       └── package.yaml
│
├── git/
│   ├── .gitconfig
│   └── .qenv/
│       └── package.yaml
│
├── starship/
│   ├── .config/starship.toml
│   └── .qenv/
│       └── package.yaml
│
└── nvim/
    ├── .config/nvim/init.lua
    └── .qenv/
        └── package.yaml
```

---

## Bootstrap Model

The installed launcher should be intentionally minimal.
A separate root-level `bootstrap.sh` handles first-run prerequisite provisioning and links `qenv` into `${XDG_BIN_HOME:-$HOME/.local/bin}`.
If that directory is not on `PATH`, bootstrap should print guidance, but persistent shell profile changes remain outside bootstrap.

Responsibilities:

1. `bootstrap.sh` ensures usable bootstrap prerequisites exist, including Python and stow, installs the launcher symlink, and warns when the launcher directory is not on `PATH`.
2. The installed launcher locates the dotfiles repo.
3. The installed launcher exports `DOTFILES`.
4. The installed launcher prefers `qenv/.venv/bin/python` when present, then falls back to a usable system Python.
5. The installed launcher hands off to the Python implementation.

The `qenv/` directory may also be managed as a local `uv` project. In that mode, `uv sync` creates `qenv/.venv`, and the launcher uses that interpreter automatically.

Conceptual installed launcher:

```sh
#!/usr/bin/env sh
set -eu

SCRIPT_PATH="$(readlink -f -- "$0")"
SCRIPT_DIR="$(cd -- "$(dirname -- "$SCRIPT_PATH")" && pwd -P)"

if [ -n "${DOTFILES:-}" ]; then
  DOTFILES_ROOT="$DOTFILES"
else
  DOTFILES_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd -P)"
fi

export DOTFILES="$DOTFILES_ROOT"

if [ -x "$SCRIPT_DIR/.venv/bin/python" ]; then
  exec "$SCRIPT_DIR/.venv/bin/python" "$SCRIPT_DIR/__main__.py" "$@"
fi

if command -v python3 >/dev/null 2>&1; then
  exec python3 "$SCRIPT_DIR/__main__.py" "$@"
fi

if command -v python >/dev/null 2>&1 \
  && python -c 'import sys; raise SystemExit(0 if sys.version_info.major == 3 else 1)' >/dev/null 2>&1; then
  exec python "$SCRIPT_DIR/__main__.py" "$@"
fi

echo "qenv: no usable Python found. Run $DOTFILES_ROOT/bootstrap.sh first or create $SCRIPT_DIR/.venv with uv sync." >&2
exit 1
```

Bootstrap prerequisite installation should use the same general installation heuristics as the rest of the system, but because Python is required to run `qenv`, the root `bootstrap.sh` path remains a special case for now.

Bootstrap Python discovery order might be:

1. `python3` already available
2. `python` already available and acceptable
3. `uv` available and can provide Python
4. `mise` available and can install Python
5. system package manager with sudo
6. portable/user-local Python fallback, if allowed by policy
7. fail with actionable instructions

---

## Core Architecture

The main inputs to `qenv` are:

```text
Repo config
Policy stack
Host facts
Tool registry
Package metadata
Runtime state
```

The resolver combines these into plans:

```text
Package metadata
  +
Tool registry
  +
Host facts
  +
Effective policy
  =
Install/stow/sync/action plans
```

Everything should be plan-first.

Important rule:

> Any operation that changes system state should first be representable as a plan.

This applies to:

- installing tools
- stowing packages
- unstowing packages
- changing login shell
- cloning plugin repos
- creating symlinks
- pulling repo changes
- applying post-install actions

---

## Repo-Level Configuration

A root-level `qenv.yaml` describes dotfiles repo behavior.

```yaml
version: 1

dotfiles:
  env_var: DOTFILES
  default_path: "~/.dotfiles"

repo:
  remote: origin
  branch: main

  sync:
    auto_pull: true
    pull_strategy: ff-only
    block_on_dirty_worktree: true
    block_on_symlink_risk: true
    auto_apply_tools: false
    auto_restow_changed: false

stow:
  target: "~"
  directory: "."
  ignore_file: ".stow-local-ignore"

packages:
  metadata_path: ".qenv/package.yaml"
  default_set: default
  auto_apply_tool_packages: true
  tool_package_mode: when_tool_satisfied

sets:
  default:
    - git
    - zsh
    - starship

  dev:
    - git
    - zsh
    - starship
    - nvim
    - tmux
```

---

## Hierarchical Policy Model

Policies should be hierarchical. The effective policy is built by loading an ordered set of policy files and merging them.

Recommended order:

```text
qenv/policies/policy.yaml
qenv/policies/os/<platform>.yaml
qenv/policies/os/<distro>.yaml
qenv/policies/machines/<machine-id>.yaml
qenv/policies/local.yaml
CLI overrides
```

Example:

```text
qenv/policies/policy.yaml
qenv/policies/os/linux.yaml
qenv/policies/os/ubuntu.yaml
qenv/policies/machines/work-devbox.yaml
qenv/policies/local.yaml
```

`local.yaml` should be gitignored.

### Policy Precedence

Later files override earlier files.

```text
base policy < OS policy < machine policy < local policy < CLI flags
```

### Merge Semantics

Recommended merge rules:

```text
maps     deep merge
scalars  replace
lists    replace
null     delete or explicitly disable
```

Lists should replace by default, not concatenate. This avoids surprising behavior for ordered values like provider preference lists.

### Example Base Policy

```yaml
version: 1

install:
  prefer_existing: true

  scopes:
    order:
      - existing
      - global
      - user

  global:
    enabled: true
    allow_sudo: true
    allow_interactive_sudo: false

  user:
    enabled: true

providers:
  order:
    - apt
    - dnf
    - pacman
    - zypper
    - brew
    - mise
    - cargo
    - uv
    - git
    - direct

  blocked: []

dependencies:
  optional:
    mode: best_effort
    warn_if_unavailable: true
    fail_if_install_fails: false

packages:
  auto_apply_tool_packages: true
  tool_package_mode: when_tool_satisfied

actions:
  allow_post_install_actions: true
  allow_arbitrary_commands: false

security:
  allow_install_scripts: false
  allow_curl_pipe_shell: false
  allow_direct_downloads: true
  require_checksums: true
  require_signatures: false
  allow_git_fallbacks: true
  allowed_hosts:
    - github.com
    - gitlab.com
```

### Example Corporate/Machine Policy

```yaml
install:
  scopes:
    order:
      - existing
      - user

  global:
    enabled: false

providers:
  order:
    - mise
    - cargo
    - uv
    - git
    - direct

  blocked:
    - brew

dependencies:
  optional:
    mode: detect_only

actions:
  allow_post_install_actions: true
  allow_arbitrary_commands: false

security:
  allow_install_scripts: false
  allow_curl_pipe_shell: false
  allow_direct_downloads: false
```

---

## Host Facts

`qenv` should detect host capabilities and expose them.

Host facts include:

- OS family
- distro
- distro version
- architecture
- hostname
- machine ID
- WSL/container/CI detection
- available package managers
- sudo availability
- interactive sudo availability
- current shell
- `$PATH`
- whether `~/.local/bin` exists
- whether `~/.local/bin` is on `$PATH`
- installed commands
- versions for known tools when needed

Useful command:

```sh
qenv host show
```

---

## Tool Registry

The registry maps semantic tool names to commands, version probes, providers, fallback methods, and associated qenv packages.

Package requirements should refer to semantic tool names, not package-manager-specific names.

```yaml
version: 1

tools:
  ripgrep:
    description: "Fast recursive search"
    commands:
      - rg

    version:
      command: "rg --version"
      regex: "^ripgrep (?P<version>[0-9.]+)"

    providers:
      apt:
        package: ripgrep
        platforms:
          - debian
          - ubuntu

      dnf:
        package: ripgrep
        platforms:
          - fedora

      pacman:
        package: ripgrep
        platforms:
          - arch

      brew:
        package: ripgrep
        platforms:
          - linux
          - macos

      mise:
        package: ripgrep
        platforms:
          - linux
          - macos

      cargo:
        package: ripgrep
        provides:
          - rg
        platforms:
          - linux
          - macos
```

### Tool With Associated Stow Package

```yaml
tools:
  starship:
    description: "Cross-shell prompt"
    commands:
      - starship

    qenv_package: starship

    providers:
      apt:
        package: starship
        platforms:
          - ubuntu

      pacman:
        package: starship
        platforms:
          - arch

      brew:
        package: starship
        platforms:
          - linux
          - macos

      mise:
        package: starship
        platforms:
          - linux
          - macos
```

---

## Package Metadata

Each Stow package can include qenv metadata.

Location:

```text
<package>/.qenv/package.yaml
```

This metadata must be ignored by Stow.

`.stow-local-ignore` should include:

```text
^\.qenv$
^\.qenv/.*$
```

Because Stow ignore rules are package-local, qenv should eventually provide `qenv package init <package>` to scaffold both `.qenv/package.yaml` and the required `.stow-local-ignore` entries. This is convenience tooling and is not part of the MVP.

### Package Example: zsh

```yaml
version: 1

package:
  name: zsh
  description: "Zsh shell configuration"

requires:
  tools:
    required:
      - tool: zsh

    optional:
      - tool: starship
        purpose: "Prompt"
      - tool: fzf
        purpose: "Fuzzy finder integration"
      - tool: zoxide
        purpose: "Directory jumping"

stow:
  enabled: true
  target: "~"

actions:
  after_apply:
    - type: set_login_shell
      shell: zsh
      required: false
```

### Package Example: starship

```yaml
version: 1

package:
  name: starship
  description: "Starship prompt configuration"

requires:
  tools:
    required:
      - tool: starship

stow:
  enabled: true
```

---

## Required and Optional Dependencies

Package dependencies should support both required and optional requirements.

### Required Dependencies

Required dependencies are blocking. If a required tool or required package cannot be satisfied under the current policies, the package cannot be applied.

### Optional Dependencies

Optional dependencies are best-effort by default. If an optional dependency is available, qenv may use it. If missing but installable, qenv may install it depending on policy. If missing and not installable, qenv should warn but continue.

This supports conditional shell configuration such as:

```sh
if command -v fzf >/dev/null 2>&1; then
  # enable fzf integration
fi
```

### Optional Dependency Modes

Policy should control optional dependency behavior.

```yaml
dependencies:
  optional:
    mode: best_effort
```

Possible modes:

```text
ignore
  Do not evaluate optional dependencies.

detect_only
  Use optional dependencies only if already installed. Do not install them.

best_effort
  Install optional dependencies if possible. Do not fail if unavailable.

strict
  Treat optional dependencies as required.
```

---

## Tool Packages

Some tools have their own Stow packages.

Examples:

```text
starship/
fzf/
zoxide/
delta/
tmux/
nvim/
```

If a tool has an associated qenv package, that package may be applied automatically.

Registry example:

```yaml
tools:
  fzf:
    commands:
      - fzf
    qenv_package: fzf

  zoxide:
    commands:
      - zoxide
    qenv_package: zoxide

  starship:
    commands:
      - starship
    qenv_package: starship
```

### Tool Package Auto-Application

Policy controls this behavior:

```yaml
packages:
  auto_apply_tool_packages: true
  tool_package_mode: when_tool_satisfied
```

Possible modes:

```text
never
  Never auto-apply associated tool packages.

when_tool_satisfied
  If the tool is already present or successfully installed, apply its package.

when_tool_installed_by_qenv
  Apply the associated package only if qenv installed the tool in this run.

always_try
  Try to install the tool and apply its package whenever referenced.
```

### Optionality Propagation

If an optional tool introduces a tool package, that package should also be considered optional. If a required tool introduces a tool package, that package should be considered required.

---

## Dependency Graph Model

Internally, qenv should treat resolution as a graph.

Node types:

```text
PackageNode
ToolNode
ProviderActionNode
ActionNode
```

Edge types:

```text
requires
associated_package
install_action
post_action
```

Edges should carry dependency strength:

```text
required: true
required: false
```

Cycle detection is required.

---

## Provider Model

Providers are installation backends.

Examples:

```text
apt
dnf
pacman
zypper
brew
mise
cargo
uv
nix
git
direct
install_script
```

Each provider should expose a common interface:

```text
is_available(host)
can_install(tool, host, policy)
plan(tool, host, policy)
apply(action)
```

Provider decisions should consider:

- host OS
- distro
- architecture
- package manager availability
- sudo availability
- policy scope order
- provider order
- provider blocklist
- security settings
- registry support

---

## Post-Install and Post-Apply Actions

Some operations need to happen after tool installation or package application.

Examples:

- set the user’s login shell with `chsh`
- create a symlink
- clone a plugin
- initialize a plugin manager
- create a directory
- ensure a Git config value
- generate a cache
- run a known tool-specific setup command

These actions must be:

1. declarative when possible
2. idempotent
3. explainable
4. policy-controlled
5. safe in what-if mode

### Known Declarative Actions

Where possible, qenv should provide built-in action types instead of arbitrary shell commands.

Examples:

```text
set_login_shell
ensure_directory
ensure_symlink
ensure_git_config
ensure_line
clone_git_repo
run_command
```

`run_command` should be treated as the least safe and most restricted action type.

### Example: Set Login Shell

```yaml
actions:
  after_apply:
    - type: set_login_shell
      shell: zsh
      required: false
```

The action plugin should know how to inspect current state.

What-if example:

```text
Action: set login shell
Current: /bin/bash
Desired: /usr/bin/zsh
Would run: chsh -s /usr/bin/zsh bill
Required: false
```

If already current:

```text
Action: set login shell
Current: /usr/bin/zsh
Desired: /usr/bin/zsh
Status: already satisfied
```

No change should be shown unless verbose mode is enabled.

### Example: Clone Plugin Repo

```yaml
actions:
  after_apply:
    - type: clone_git_repo
      repo: "https://github.com/mattmc3/antidote.git"
      dest: "~/.local/share/antidote"
      update: false
      required: false
```

Idempotent behavior:

- if destination does not exist, clone
- if destination exists and is correct repo, no change
- if destination exists and is wrong repo, report conflict
- if `update: true`, plan a pull/fetch according to policy
- if optional and unavailable, warn only

---

## Plugin / Extensibility Model

`qenv` should support plugins or extension modules for custom actions and possibly custom providers.

Plugin use cases:

- custom post-install action
- custom provider
- custom host detection
- custom validation
- custom package metadata behavior

Potential plugin categories:

```text
providers
actions
validators
detectors
formatters
```

### Action Plugin Interface

Conceptual interface:

```text
name
schema
detect_current_state(context, config)
plan(context, config)
apply(context, config)
```

Every action plugin must support what-if planning.

It must be able to answer:

```text
Is the desired state already satisfied?
If not, what would change?
How would the change be applied?
Is the change allowed by policy?
```

### Provider Plugin Interface

Conceptual interface:

```text
name
scope
is_available(host)
can_install(tool, host, policy, registry_entry)
plan_install(tool, host, policy, registry_entry)
apply_install(action, context)
```

### Plugin Loading

Since qenv is repo-internal, plugin discovery can be simple initially:

```text
$DOTFILES/qenv/plugins/
```

Because plugins can execute code, they should be considered trusted code from the dotfiles repo.

---

## Idempotency

Everything qenv does should be idempotent.

That means each operation should be modeled as desired state, not just as a command to run.

Every operation must be able to answer:

```text
What is the current state?
What is the desired state?
Is a change required?
What change would be made?
```

Examples:

- Tool installation checks command presence and version before installing.
- Stow checks whether target paths are already correct symlinks.
- Repo sync fetches and analyzes incoming changes before merging.
- Post actions check current state before applying.

---

## What-If / Plan Mode

“What-if” is central.

The planner should show only what would change. If something is already correct, it should not appear in normal what-if output. Verbose mode may show satisfied items.

Commands:

```sh
qenv plan zsh
qenv plan --all
qenv sync --plan
qenv stow zsh --whatif
qenv apply zsh --whatif
```

Possible aliases:

```sh
qenv whatif zsh
qenv dry-run zsh
```

### What-If Output Principles

Default output should include:

- changes that would be made
- warnings
- blockers
- skipped optional items
- required failures
- security/policy rejections

Default output should exclude:

- already-installed tools
- already-stowed packages
- already-satisfied post actions

unless `--verbose` is used.

Example:

```text
Plan for package: zsh

Tool changes:
  install starship via mise
  install zoxide via mise

Package changes:
  stow package starship
  stow package zoxide
  restow package zsh

Post-apply actions:
  set login shell to /usr/bin/zsh

Optional skipped:
  fzf
    reason: provider unavailable under current policy

Warnings:
  set_login_shell may require interactive password

Result:
  ready_with_warnings
```

No-change output:

```text
No changes required.

Package zsh is already stowed.
Required tools are satisfied.
Post-apply actions are satisfied.
```

---

## Error and Warning Model

qenv should distinguish between configuration errors, resolution errors, and execution errors.

### Configuration Errors

The repo metadata is invalid.

Examples:

- Package references unknown tool.
- Registry provider is malformed.
- Policy contains invalid keys.
- Action metadata fails schema validation.

These should generally fail fast.

### Resolution Errors

The repo metadata is valid, but current policy/host cannot satisfy it.

Examples:

- Required tool has no allowed provider.
- Global installs are disabled and no user provider exists.
- Direct downloads are disabled.
- Required version cannot be satisfied.

Required resolution errors block the package. Optional resolution errors warn.

### Execution Errors

A planned action failed when applied.

Examples:

- `apt install` failed.
- `mise install` failed.
- `stow` failed.
- `chsh` failed.
- `git clone` failed.
- checksum mismatch.

Execution errors should include:

- action name
- command, if applicable
- exit code
- stderr summary
- whether dependency was required or optional
- recovery suggestion

---

## Repo Synchronization

Since qenv replaces existing dotfile scripts, it should manage repo operations.

Commands:

```sh
qenv status
qenv sync
qenv pull
qenv push
qenv save
qenv repo status
qenv repo diff
```

### `qenv status`

High-level dashboard.

Should show:

- dotfiles root
- branch
- upstream
- Git status
- ahead/behind count
- effective policy summary
- stowed package status
- missing required tools
- optional warnings
- sync risks

### `qenv sync`

Safe synchronization command.

Suggested flow:

1. verify repo exists
2. verify branch/upstream
3. check working tree status
4. fetch upstream
5. analyze incoming changes
6. map changed files to packages
7. detect currently stowed affected packages
8. detect broken symlink risks
9. detect tool dependency changes
10. produce sync plan
11. apply only if safe and allowed

Prefer:

```text
git fetch
git merge --ff-only
```

over raw `git pull`.

### Broken Symlink Protection

If an incoming change deletes or renames a file currently stowed into `$HOME`, qenv should detect the risk.

Example:

```text
Incoming deletion:
  zsh/.zshrc

Existing link:
  ~/.zshrc -> ~/.dotfiles/zsh/.zshrc

Risk:
  pull would create broken symlink
```

The sync plan should propose one of:

- unstow before pull
- pull then restow
- manual resolution
- allow broken links explicitly

---

## State Tracking

Although desired state comes from the repo, qenv should track local runtime state outside the repo.

Suggested location:

```text
~/.local/state/qenv/state.yaml
```

State may include:

```yaml
dotfiles_root: "~/.dotfiles"

stowed:
  zsh:
    target: "~"
    stowed_at: "2026-07-07T12:41:00-04:00"

installed:
  starship:
    provider: mise
    installed_at: "2026-07-07T12:42:00-04:00"
    reason:
      package: zsh
      dependency: optional

actions:
  set_login_shell:zsh:
    last_checked: "2026-07-07T12:43:00-04:00"
    last_result: satisfied
```

The state file should not be treated as truth by itself.

Instead:

```text
state file = remembered intent/history
filesystem/host scan = current truth
repo metadata = desired state
```

`qenv doctor` should detect drift.

---

## Command Surface

### Environment and Diagnostics

```sh
qenv host show
qenv policy show
qenv policy explain <path>
qenv doctor
qenv status
```

### Tools

```sh
qenv tool list
qenv tool explain <tool>
qenv tool status <tool>
qenv why <tool>
```

### Packages

```sh
qenv package init <package>
qenv package list
qenv package status [package]
qenv package explain <package>
qenv package validate [package]
```

### Planning and Applying

```sh
qenv plan <package|@set...>
qenv apply <package|@set...>
qenv stow <package|@set...>
qenv unstow <package|@set...>
qenv restow <package|@set...>
qenv restow --changed
```

### Repo Operations

```sh
qenv repo status
qenv repo diff
qenv repo pull
qenv repo push
qenv sync
qenv save
qenv save -m "Update zsh config"
qenv save zsh -m "Update zsh aliases"
qenv save --push
```

### Validation

```sh
qenv registry validate
qenv package validate
qenv policy validate
qenv doctor
```

### Actions

```sh
qenv actions list
qenv actions explain zsh
qenv actions plan zsh
```

---

## Explanation Commands

qenv should be highly explainable.

### Effective Policy

```sh
qenv policy show
qenv policy explain install.global.enabled
```

### Tool Explanation

```sh
qenv tool explain fzf
```

Should show:

- registry entry
- command detection
- installed status
- version status
- provider options
- rejected providers and reasons
- selected provider
- associated qenv package
- post actions, if any

### Package Explanation

```sh
qenv package explain zsh
```

Should show:

- package metadata file
- required dependencies
- optional dependencies
- tool package expansion
- post actions
- stow status
- blockers
- warnings
- what would change

### Why

```sh
qenv why fzf
```

Shows which packages require or optionally use a tool.

---

## Validation

### Registry Validation

```sh
qenv registry validate
```

Checks:

- duplicate tool names
- unknown providers
- malformed provider entries
- invalid platform names
- missing commands
- invalid version regex
- direct downloads without checksums when required
- associated package names that do not exist
- invalid post-install metadata

### Package Validation

```sh
qenv package validate
```

Checks:

- valid schema
- referenced tools exist
- referenced packages exist
- required/optional sections are valid
- action metadata is valid
- Stow metadata is ignored
- package cycles are safe

### Doctor

```sh
qenv doctor
```

Runs broader diagnostics:

- host detection
- policy load
- registry validation
- package validation
- provider availability
- Python/runtime status
- Git repo status
- Stow availability
- Stow link drift
- broken symlinks
- PATH issues
- action plugin availability

---

## Plan Result States

A package plan should have one of these high-level results:

```text
no_change
ready
ready_with_warnings
blocked
invalid
```

- `no_change`: everything is already satisfied.
- `ready`: required dependencies are satisfied or installable. No warnings.
- `ready_with_warnings`: required dependencies are satisfied or installable, but optional dependencies or optional actions have warnings.
- `blocked`: one or more required dependencies or required actions cannot be satisfied.
- `invalid`: configuration is invalid.

---

## Security Model

Because qenv may install tools, clone repos, run commands, and apply plugins, security policy matters.

Suggested policy:

```yaml
security:
  allow_install_scripts: false
  allow_curl_pipe_shell: false
  allow_direct_downloads: true
  require_checksums: true
  require_signatures: false
  allow_git_fallbacks: true
  allowed_hosts:
    - github.com
    - gitlab.com

plugins:
  enabled: true
  allow_repo_plugins: true
  allow_user_plugins: false

actions:
  allow_post_install_actions: true
  allow_arbitrary_commands: false
```

Arbitrary command execution should be opt-in and visible in plans.

---

## Design Principles

1. **Repo-internal first** — qenv lives in `.dotfiles`.
2. **Declarative where possible** — prefer structured metadata over scripts.
3. **Idempotent always** — detect current state before planning changes.
4. **Plan before apply** — every state-changing operation must be previewable.
5. **Required blocks, optional warns** — required dependencies block; optional ones warn.
6. **Explain rejections** — rejected providers/actions must include reasons.
7. **Keep Bash minimal** — complex logic belongs in Python.
8. **Avoid becoming Ansible** — stay focused on dotfiles, tools, Stow packages, and environment setup.

---

## Suggested MVP

### Phase 1: Discovery and Validation

Implement:

```sh
qenv host show
qenv policy show
qenv package list
qenv package explain
qenv registry validate
qenv package validate
qenv doctor
```

No installs yet.

### Phase 2: Tool Resolution

Implement:

```sh
qenv tool explain <tool>
qenv plan <package>
```

Support:

- required tools
- optional tools
- provider selection
- installability errors
- warnings

### Phase 3: Apply Tools

Implement provider execution for:

```text
apt
dnf
pacman
brew
mise
cargo
```

Add:

```sh
qenv apply <package>
```

### Phase 4: Stow Integration

Implement:

```sh
qenv stow <package>
qenv unstow <package>
qenv restow <package>
qenv package status
```

### Phase 5: Tool Packages

Implement:

```text
tool -> associated qenv package
optionality propagation
cycle-safe expansion
```

### Phase 6: Post Actions

Implement built-in idempotent actions:

```text
set_login_shell
ensure_directory
ensure_symlink
clone_git_repo
ensure_git_config
run_command
```

Restrict `run_command` by policy.

### Phase 7: Repo Sync

Implement:

```sh
qenv status
qenv sync
qenv save
qenv push
qenv pull
```

Add safe pull planning and symlink risk detection.

---

## Summary

`qenv` should be a repo-internal orchestration tool for `.dotfiles`.

It should combine:

```text
Stow package metadata
semantic tool registry
hierarchical policies
host detection
provider-based installation
tool package expansion
idempotent post actions
Git repo management
what-if planning
```

The most important architectural rule is:

> qenv should model desired state, compute a plan, show only meaningful changes, and apply that plan idempotently.

This keeps the system scalable while avoiding the duplicate-shell-script problem that motivated the design.
