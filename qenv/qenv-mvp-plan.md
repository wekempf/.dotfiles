# qenv MVP Implementation Plan

## Bare Minimum for Package Installation

This plan outlines the absolute minimum functionality needed to make qenv useful for installing packages with their tool dependencies.

The current implementation reached that MVP by shelling out to GNU Stow. The next planned phase replaces that subprocess with a qenv-native POSIX link engine that applies stricter desired-state semantics.

---

## Goal

Enable users to run:

```sh
qenv apply <package>
```

And have qenv:
1. Read the package metadata
2. Detect which required tools are missing
3. Install missing tools using available package managers
4. Reconcile the package links into `$HOME`

---

## Out of Scope for MVP

- Optional dependencies
- Tool packages (packages associated with tools)
- Package scaffolding commands such as `qenv package init`
- Post-install actions
- Git repo sync operations
- Policy hierarchy (use single policy file)
- Plugin system
- State tracking
- Package sets
- What-if mode (nice to have, but not blocking)

---

## MVP Components

### 1. Bootstrap (Minimal)

**File**: `bootstrap.sh`

Root bootstrap that:
- Ensures Python 3 and stow are available
- Symlinks `qenv/qenv` into `${XDG_BIN_HOME:-$HOME/.local/bin}`
- Prints guidance when `${XDG_BIN_HOME:-$HOME/.local/bin}` is not in `PATH`
- Exits after bootstrapping the environment

**File**: `qenv/qenv`

Simple shell wrapper that:
- Locates dotfiles repo (`$DOTFILES` or the installed launcher path)
- Exports `DOTFILES` environment variable
- Prefers `qenv/.venv/bin/python`, then falls back to system Python 3
- Executes `qenv/__main__.py`

**File**: `qenv/pyproject.toml`

uv project metadata that:
- Defines qenv's Python dependencies
- Creates a repo-local virtual environment in `qenv/.venv` when synced
- Does not require packaging qenv as an installed distribution yet

Prerequisite bootstrapping lives in `bootstrap.sh`, not in the launcher.

### 2. Core Python Modules

**File**: `qenv/__main__.py`
- CLI entry point using `argparse`
- Implements `apply` command

**File**: `qenv/dotfiles.py`
- Find dotfiles root
- Load `qenv.yaml` (minimal config)

**File**: `qenv/host.py`
- Detect OS (Linux/macOS)
- Detect distro (Ubuntu/Fedora/Arch/macOS)
- Detect available package managers (apt/dnf/pacman/brew)
- Check sudo availability

**File**: `qenv/policy.py`
- Load single `qenv/policies/policy.yaml`
- Provide policy queries (no merging in MVP)

**File**: `qenv/registry.py`
- Load `qenv/registry.yaml`
- Look up tool definitions
- Map tools to providers

**File**: `qenv/packages.py`
- Find package directories
- Load `.qenv/package.yaml` from packages
- Parse required tools

**File**: `qenv/resolver.py`
- Check if tool command exists
- Determine which provider to use
- Create install plan

**File**: `qenv/executor.py`
- Execute install plans
- Reconcile package links into the target directory

**File**: `qenv/providers/base.py`
- Base provider interface

**File**: `qenv/providers/apt.py`
- Install via `apt-get install`
- Requires sudo

**File**: `qenv/providers/dnf.py`
- Install via `dnf install`
- Requires sudo

**File**: `qenv/providers/pacman.py`
- Install via `pacman -S`
- Requires sudo

**File**: `qenv/providers/brew.py`
- Install via `brew install`
- User-level, no sudo

**File**: `qenv/providers/mise.py`
- Install via `mise install`
- User-level, no sudo
- Check if mise is installed first

### 3. Configuration Files

**File**: `qenv.yaml` (root)

Minimal:
```yaml
version: 1

stow:
  target: "~"
  directory: "."
```

**File**: `qenv/policies/policy.yaml`

Minimal:
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

**File**: `qenv/registry.yaml`

Start with a few essential tools:
```yaml
version: 1

tools:
  zsh:
    commands:
      - zsh
    providers:
      apt:
        package: zsh
      dnf:
        package: zsh
      pacman:
        package: zsh
      brew:
        package: zsh

  starship:
    commands:
      - starship
    providers:
      brew:
        package: starship
      mise:
        package: starship

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

  bat:
    commands:
      - bat
    providers:
      apt:
        package: bat
      dnf:
        package: bat
      pacman:
        package: bat
      brew:
        package: bat

  git:
    commands:
      - git
    providers:
      apt:
        package: git
      dnf:
        package: git
      pacman:
        package: git
      brew:
        package: git
```

### 4. Package Metadata

**File**: `<package>/.qenv/package.yaml`

Minimal schema:
```yaml
version: 1

package:
  name: <name>
  description: "<description>"

requires:
  tools:
    required:
      - tool: <tool-name>
      - tool: <tool-name>

stow:
  enabled: true
  target: "~"
```

---

## Implementation Order

### Step 1: Bootstrap & Repo Discovery
- Create `bootstrap.sh` and `qenv/qenv`
- Create `qenv/__main__.py` with basic CLI
- Create `qenv/dotfiles.py` to find repo

**Deliverable**: `qenv --version` works

### Step 2: Host Detection
- Create `qenv/host.py`
- Detect OS, distro, available package managers

**Deliverable**: `qenv host show` displays system info

### Step 3: Configuration Loading
- Create `qenv/policy.py`
- Create `qenv/registry.py`
- Load `qenv.yaml`, `policy.yaml`, `registry.yaml`

**Deliverable**: Config files load without errors

### Step 4: Package Metadata
- Create `qenv/packages.py`
- Find packages in repo
- Load `.qenv/package.yaml`

**Deliverable**: `qenv package list` shows packages

### Step 5: Tool Detection
- Create `qenv/resolver.py`
- Check if commands exist in PATH
- Map tools to providers based on host

**Deliverable**: Can determine which tools need installation

### Step 6: Provider Implementation
- Create `qenv/providers/` module
- Implement system package managers (apt/dnf/pacman/brew)
- Implement mise provider

**Deliverable**: Can install a tool using detected provider

### Step 7: Executor
- Create `qenv/executor.py`
- Execute install plans
- Build the desired link plan for the package
- Validate the full target state before mutating anything
- Remove stale owned links and create missing links

**Deliverable**: `qenv apply <package>` installs tools and reconciles package links

---

## MVP User Flow

```sh
# User runs apply command
$ qenv apply zsh

# qenv does:
# 1. Load zsh/.qenv/package.yaml
# 2. See that it requires tool: zsh
# 3. Check if 'zsh' command exists
# 4. If not found:
#    a. Look up 'zsh' in registry.yaml
#    b. Check host OS/distro
#    c. Find first available provider (e.g., apt)
#    d. Run: sudo apt-get install -y zsh
# 5. Build the desired link plan from the package tree
# 6. Validate all target paths and ownership rules
# 7. Remove owned links that are broken or no longer desired
# 8. Create missing file links and `.link` directory links

Output: zsh installed
  Package zsh reconciled to ~
```

Link rules for the planned native linker:

- Directories ending in `.link` are linked as directory symlinks and are terminal traversal nodes.
- All other non-ignored files are linked individually.
- Apply validates only the package being installed. qenv does not need repo-wide design-time conflict checks.
- Apply is strict: no merge, no overwrite, no partial best-effort link behavior.

---

## Error Handling (MVP)

Keep it simple:

- **Missing package**: Print error, exit 1
- **Missing tool in registry**: Print error, exit 1
- **No suitable provider**: Print error, exit 1
- **Install command fails**: Print stderr, exit 1
- **Link conflict or reconcile failure**: Print the conflicting path or command error, exit 1

No retries, no fallbacks, no merge, no overwrite, and no best-effort link mutation in MVP.

---

## Testing the MVP

Manual test cases:

1. **Fresh system** (no tools): `qenv apply zsh`
  - Should install zsh and reconcile package links

2. **Tool already exists**: `qenv apply git`
  - Should skip install, just reconcile links

3. **Unknown package**: `qenv apply nonexistent`
   - Should error clearly

4. **Tool not in registry**: Package requires unknown tool
   - Should error clearly

5. **No sudo available**: On system requiring sudo
   - Should error when trying to install

6. **Broken or stale owned links**: `qenv apply zsh`
  - Should remove owned links that are broken or no longer part of the desired tree

7. **Directory link conflict**: Package contains `.config/nvim.link`
  - Should fail clearly if the target subtree is already occupied by another package or real files

---

## File Structure After MVP

```
~/.dotfiles/
├── bootstrap.sh                      # First-run bootstrap
├── qenv/
│   ├── qenv                          # Installed launcher source
│   ├── pyproject.toml                # uv project metadata
│   ├── .venv/                        # uv-managed local virtual environment
│   ├── .stow-local-ignore            # Prevent qenv from being stowed as a package
│   ├── __main__.py                   # CLI entry point
│   ├── dotfiles.py                   # Repo discovery
│   ├── host.py                       # Host detection
│   ├── policy.py                     # Policy loading
│   ├── registry.py                   # Tool registry
│   ├── packages.py                   # Package discovery
│   ├── resolver.py                   # Dependency resolution
│   ├── executor.py                   # Plan execution
│   ├── providers/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── apt.py
│   │   ├── dnf.py
│   │   ├── pacman.py
│   │   ├── brew.py
│   │   └── mise.py
│   ├── policies/
│   │   └── policy.yaml               # Base policy
│   └── registry.yaml                 # Tool definitions
├── qenv.yaml                         # Repo config
├── zsh/
│   ├── .zshrc
│   └── .qenv/
│       └── package.yaml
└── git/
    ├── .gitconfig
    └── .qenv/
        └── package.yaml
```

---

## What Makes This "Bare Minimum"

This plan includes **only** what's needed to:
- Install missing tools required by a package
- Reconcile that package into the target home directory

It deliberately excludes:
- Optional dependencies (adds complexity)
- Package sets (adds indirection)
- Tool packages (adds recursion)
- Post-install actions (adds plugin system)
- What-if mode (adds planning complexity)
- Git sync (different concern)
- State tracking (adds persistence)
- Policy merging (adds complexity)
- Validation commands (nice to have)

These can all be added incrementally after the MVP proves useful.

---

## Success Criteria

The MVP is successful when:

1. On a fresh Ubuntu system, `qenv apply zsh` installs zsh and reconciles the config links
2. On a macOS system with Homebrew, the same command works
3. If a tool is already installed, it's not reinstalled
4. Re-running apply converges the target to desired state by removing stale owned links and creating missing links
5. Directory links via `.link` support exclusive subtree ownership with clear conflict errors
6. Error messages clearly indicate what went wrong
7. The code is simple enough to understand and extend

---

## Next Steps After MVP

Once the bare minimum works:

1. Replace the external Stow subprocess with a native POSIX qenv link engine
2. Add `qenv plan <package>` (what-if mode)
3. Add `qenv package init <package>` to scaffold `.qenv/package.yaml` and package-local `.stow-local-ignore` entries
4. Add optional dependencies with `detect_only` mode
5. Add basic validation commands (`qenv doctor`)
6. Add tool packages (tools that have associated configs)
7. Add simple post-install actions (e.g., set login shell)
8. Add package sets
9. Add policy hierarchy
10. Add state tracking outside the repo using `QENV_STATE_FILE`, platform state directories, and a home-directory fallback
11. Add Git sync operations
12. Add plugin system

Each addition should be incremental and prove its value independently.

---

## Implementation Checklist

Use this numbered checklist to implement the MVP step by step across multiple sessions.

### Phase 1: Bootstrap & Repo Discovery

- [x] 1. Create `bootstrap.sh` and `qenv/qenv`
  - [x] 1.1. Ensure Python 3 and stow are available during bootstrap
  - [x] 1.2. Symlink `qenv` into `${XDG_BIN_HOME:-$HOME/.local/bin}`
  - [x] 1.3. Locate dotfiles repo (`$DOTFILES` or launcher path)
  - [x] 1.4. Export `DOTFILES` environment variable
  - [x] 1.5. Find Python 3 executable
  - [x] 1.6. Execute `qenv/__main__.py` with arguments

- [x] 2. Create `qenv/__main__.py`
  - [x] 2.1. Set up argparse CLI parser
  - [x] 2.2. Add `--version` flag
  - [x] 2.3. Add placeholder for `apply` subcommand
  - [x] 2.4. Add basic error handling

- [x] 3. Create `qenv/dotfiles.py`
  - [x] 3.1. Implement `find_dotfiles_root()`
  - [x] 3.2. Implement `load_qenv_yaml()`
  - [x] 3.3. Add error handling for missing repo

- [x] 4. Create minimal `qenv.yaml` in repo root
  - [x] 4.1. Add version field
  - [x] 4.2. Add stow configuration (target and directory)

- [x] 5. Test Phase 1
  - [x] 5.1. Verify `qenv --version` works
  - [x] 5.2. Verify error when repo not found
  - [x] 5.3. Verify `$DOTFILES` is set correctly

### Phase 2: Host Detection

- [x] 6. Create `qenv/host.py`
  - [x] 6.1. Detect OS (Linux/macOS using `platform.system()`)
  - [x] 6.2. Detect Linux distro (parse `/etc/os-release`)
  - [x] 6.3. Detect architecture (`platform.machine()`)
  - [x] 6.4. Check for available package managers (apt/dnf/pacman/brew)
  - [x] 6.5. Check sudo availability (`which sudo`)
  - [x] 6.6. Create `HostInfo` dataclass/dict

- [x] 7. Add `host show` subcommand to `__main__.py`
  - [x] 7.1. Display OS and distro
  - [x] 7.2. Display architecture
  - [x] 7.3. Display available package managers
  - [x] 7.4. Display sudo availability

- [ ] 8. Test Phase 2
  - [x] 8.1. Verify `qenv host show` displays correct info
  - [ ] 8.2. Test on different systems if available

### Phase 3: Configuration Loading

- [x] 9. Create `qenv/policies/policy.yaml`
  - [x] 9.1. Add version field
  - [x] 9.2. Add install.global.enabled setting
  - [x] 9.3. Add install.global.allow_sudo setting
  - [x] 9.4. Add providers.order list

- [x] 10. Create `qenv/policy.py`
  - [x] 10.1. Implement `load_policy()` to read YAML
  - [x] 10.2. Add policy query methods (get_provider_order, etc.)
  - [x] 10.3. Add validation for required fields
  - [x] 10.4. Add error handling for malformed YAML

- [x] 11. Create `qenv/registry.yaml`
  - [x] 11.1. Add version field
  - [x] 11.2. Add tool definition for `git`
  - [x] 11.3. Add tool definition for `zsh`
  - [x] 11.4. Add tool definition for `starship`
  - [x] 11.5. Add tool definition for `ripgrep`
  - [x] 11.6. Add tool definition for `bat`

- [x] 12. Create `qenv/registry.py`
  - [x] 12.1. Implement `load_registry()` to read YAML
  - [x] 12.2. Implement `get_tool(name)` lookup
  - [x] 12.3. Implement `get_providers_for_tool(tool, host)` filtering
  - [x] 12.4. Add validation for tool definitions
  - [x] 12.5. Add error handling for unknown tools

- [x] 13. Test Phase 3
  - [x] 13.1. Verify policy.yaml loads without errors
  - [x] 13.2. Verify registry.yaml loads without errors
  - [x] 13.3. Verify tool lookups work
  - [x] 13.4. Verify error on unknown tool

### Phase 4: Package Metadata

- [x] 14. Create `.qenv/package.yaml` for existing packages
  - [x] 14.1. Create `zsh/.qenv/package.yaml`
  - [x] 14.2. Create `bat/.qenv/package.yaml`
  - [x] 14.3. Create `ripgrep/.qenv/package.yaml`
  - [x] 14.4. Update `.stow-local-ignore` to ignore `.qenv` directories

- [x] 15. Create `qenv/packages.py`
  - [x] 15.1. Implement `find_packages()` to scan directories
  - [x] 15.2. Implement `load_package_metadata(package_name)`
  - [x] 15.3. Add validation for package.yaml schema
  - [x] 15.4. Add error handling for missing/invalid metadata
  - [x] 15.5. Create `PackageMetadata` dataclass/dict

- [x] 16. Add `package list` subcommand to `__main__.py`
  - [x] 16.1. List all packages with `.qenv/package.yaml`
  - [x] 16.2. Show package name and description
  - [x] 16.3. Show required tools

- [x] 17. Test Phase 4
  - [x] 17.1. Verify `qenv package list` shows packages
  - [x] 17.2. Verify package metadata loads correctly
  - [x] 17.3. Verify error on malformed package.yaml

### Phase 5: Tool Detection & Resolution

- [x] 18. Create `qenv/resolver.py`
  - [x] 18.1. Implement `is_command_available(command)` using `shutil.which()`
  - [x] 18.2. Implement `is_tool_installed(tool)` checking all commands
  - [x] 18.3. Implement `resolve_provider(tool, host, policy, registry)`
  - [x] 18.4. Implement `create_install_plan(package_metadata, host, policy, registry)`
  - [x] 18.5. Create `InstallPlan` dataclass with tools to install

- [x] 19. Test Phase 5
  - [x] 19.1. Verify command detection works
  - [x] 19.2. Verify provider selection based on host
  - [x] 19.3. Verify install plan generation
  - [x] 19.4. Verify error when no provider available

### Phase 6: Provider Implementation

- [x] 20. Create `qenv/providers/__init__.py`
  - [x] 20.1. Set up provider package

- [x] 21. Create `qenv/providers/base.py`
  - [x] 21.1. Define `Provider` base class/interface
  - [x] 21.2. Add `is_available(host)` method
  - [x] 21.3. Add `install(tool, package_name, host)` method
  - [x] 21.4. Add `requires_sudo` property

- [x] 22. Create `qenv/providers/apt.py`
  - [x] 22.1. Implement `is_available()` checking for apt-get
  - [x] 22.2. Implement `install()` running `sudo apt-get install -y <package>`
  - [x] 22.3. Set `requires_sudo = True`
  - [x] 22.4. Add error handling for install failures

- [x] 23. Create `qenv/providers/dnf.py`
  - [x] 23.1. Implement `is_available()` checking for dnf
  - [x] 23.2. Implement `install()` running `sudo dnf install -y <package>`
  - [x] 23.3. Set `requires_sudo = True`
  - [x] 23.4. Add error handling for install failures

- [x] 24. Create `qenv/providers/pacman.py`
  - [x] 24.1. Implement `is_available()` checking for pacman
  - [x] 24.2. Implement `install()` running `sudo pacman -S --noconfirm <package>`
  - [x] 24.3. Set `requires_sudo = True`
  - [x] 24.4. Add error handling for install failures

- [x] 25. Create `qenv/providers/brew.py`
  - [x] 25.1. Implement `is_available()` checking for brew
  - [x] 25.2. Implement `install()` running `brew install <package>`
  - [x] 25.3. Set `requires_sudo = False`
  - [x] 25.4. Add error handling for install failures

- [x] 26. Create `qenv/providers/mise.py`
  - [x] 26.1. Implement `is_available()` checking for mise
  - [x] 26.2. Implement `install()` running `mise install <package>`
  - [x] 26.3. Set `requires_sudo = False`
  - [x] 26.4. Add error handling for install failures

- [x] 27. Create provider factory in `qenv/providers/__init__.py`
  - [x] 27.1. Implement `get_provider(provider_name)` factory function
  - [x] 27.2. Auto-discover provider classes from `qenv/providers/*.py`
  - [x] 27.3. Add error handling for unknown providers

- [x] 28. Test Phase 6
  - [x] 28.1. Test each provider's `is_available()` method
  - [x] 28.2. Test installing a package with available provider
  - [x] 28.3. Verify sudo is used when required
  - [x] 28.4. Verify error handling on install failure

### Phase 7: Executor & Apply Command

- [x] 29. Create `qenv/executor.py`
  - [x] 29.1. Implement `execute_install_plan(plan, providers)`
  - [x] 29.2. Add progress output for each tool installation
  - [x] 29.3. Implement `stow_package(package_name, config)`
  - [x] 29.4. Add error handling with clear messages
  - [x] 29.5. Add dry-run support (optional but recommended)

- [x] 30. Implement `apply` subcommand in `__main__.py`
  - [x] 30.1. Parse package name argument
  - [x] 30.2. Load package metadata
  - [x] 30.3. Detect host capabilities
  - [x] 30.4. Load policy and registry
  - [x] 30.5. Create install plan
  - [x] 30.6. Execute install plan
  - [x] 30.7. Stow package
  - [x] 30.8. Print success message

- [x] 31. Test Phase 7
  - [x] 31.1. Test `qenv apply <package>` with missing tools
  - [x] 31.2. Test `qenv apply <package>` with existing tools
  - [x] 31.3. Test error on unknown package
  - [x] 31.4. Test error on missing tool in registry
  - [x] 31.5. Test error on no available provider
  - [x] 31.6. Verify stow works correctly

### Phase 8: Polish & Documentation

- [x] 32. Add user-friendly output
  - [x] 32.1. Add colored output (optional)
  - [x] 32.2. Add progress indicators
  - [x] 32.3. Improve error messages with suggestions
  - [x] 32.4. Add verbose mode flag

- [x] 33. Create README for qenv
  - [x] 33.1. Document installation
  - [x] 33.2. Document usage examples
  - [x] 33.3. Document package.yaml format
  - [x] 33.4. Document adding tools to registry

- [x] 34. Add error recovery
  - [x] 34.1. Handle partial failures gracefully
  - [x] 34.2. Provide rollback suggestions
  - [x] 34.3. Add `--force` flag for override scenarios

- [ ] 35. Final testing
  - [x] 35.1. Test on Ubuntu system
  - [ ] 35.2. Test on Fedora system (if available)
  - [ ] 35.3. Test on macOS system (if available)
  - [x] 35.4. Test all error conditions
  - [x] 35.5. Test with various package configurations

### MVP Complete! 🎉

Once all items are checked, you have a working MVP that can:
- Detect your system
- Read package requirements
- Install missing tools
- Reconcile packages into the target directory (currently via Stow)

Track your progress by checking off items as you complete them across sessions.

### Phase 9: Native Link Engine

- [ ] 36. Design qenv-native link planning
  - [ ] 36.1. Treat directories ending in `.link` as directory symlink roots
  - [ ] 36.2. Treat `.link` directories as terminal traversal nodes
  - [ ] 36.3. Continue honoring package-local ignore rules during the transition from Stow
  - [ ] 36.4. Plan individual file links for all other non-ignored files

- [ ] 37. Validate desired state at apply time
  - [ ] 37.1. Validate only the package being applied; no repo-wide design-time verification required
  - [ ] 37.2. Reject any conflicting existing file, directory, or symlink that is not already the expected target
  - [ ] 37.3. Reject overlaps between file-link targets and directory-link subtrees
  - [ ] 37.4. Complete full validation before mutating the target tree

- [ ] 38. Reconcile owned links
  - [ ] 38.1. Treat every apply as a reinstall of the package's desired state
  - [ ] 38.2. Discover links owned by the package by proving they point into that package's source tree
  - [ ] 38.3. Remove owned links that are broken or no longer desired
  - [ ] 38.4. Create missing links and parent directories
  - [ ] 38.5. Apply removals before creates so source-tree deletions and renames converge cleanly

- [ ] 39. Replace the external Stow dependency
  - [ ] 39.1. Replace the subprocess Stow call in `qenv/executor.py`
  - [ ] 39.2. Remove the Stow bootstrap prerequisite once the native linker is in place
  - [ ] 39.3. Update bootstrap and README messaging to describe native link reconciliation
  - [ ] 39.4. Decide later whether `stow` metadata names should be renamed to a qenv-native term

- [ ] 40. Test strict desired-state linking
  - [ ] 40.1. Verify idempotent reapply with no changes
  - [ ] 40.2. Verify broken owned links are removed on reapply
  - [ ] 40.3. Verify valid-but-stale owned links are removed when the desired tree changes
  - [ ] 40.4. Verify `.link` directory conflicts fail cleanly with no mutation
  - [ ] 40.5. Verify package apply never merges or overwrites foreign content
