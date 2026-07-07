# qenv MVP Implementation Plan

## Bare Minimum for Package Installation

This plan outlines the absolute minimum functionality needed to make qenv useful for installing packages with their tool dependencies.

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
4. Stow the package into `$HOME`

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
- Run stow command

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
- Run `stow` command

**Deliverable**: `qenv apply <package>` installs tools and stows package

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
# 5. Run: stow -t ~ zsh

Output: zsh installed
        Package zsh stowed to ~
```

---

## Error Handling (MVP)

Keep it simple:

- **Missing package**: Print error, exit 1
- **Missing tool in registry**: Print error, exit 1
- **No suitable provider**: Print error, exit 1
- **Install command fails**: Print stderr, exit 1
- **Stow fails**: Print stderr, exit 1

No retries, no fallbacks, no best-effort in MVP.

---

## Testing the MVP

Manual test cases:

1. **Fresh system** (no tools): `qenv apply zsh`
   - Should install zsh and stow package

2. **Tool already exists**: `qenv apply git`
   - Should skip install, just stow

3. **Unknown package**: `qenv apply nonexistent`
   - Should error clearly

4. **Tool not in registry**: Package requires unknown tool
   - Should error clearly

5. **No sudo available**: On system requiring sudo
   - Should error when trying to install

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
- Stow that package

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

1. On a fresh Ubuntu system, `qenv apply zsh` installs zsh and stows the config
2. On a macOS system with Homebrew, the same command works
3. If a tool is already installed, it's not reinstalled
4. Error messages clearly indicate what went wrong
5. The code is simple enough to understand and extend

---

## Next Steps After MVP

Once the bare minimum works:

1. Add `qenv plan <package>` (what-if mode)
2. Add `qenv package init <package>` to scaffold `.qenv/package.yaml` and package-local `.stow-local-ignore` entries
3. Add optional dependencies with `detect_only` mode
4. Add basic validation commands (`qenv doctor`)
5. Add tool packages (tools that have associated configs)
6. Add simple post-install actions (e.g., set login shell)
7. Add package sets
8. Add policy hierarchy
9. Add state tracking
10. Add Git sync operations
11. Add plugin system

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

- [ ] 18. Create `qenv/resolver.py`
  - [ ] 18.1. Implement `is_command_available(command)` using `shutil.which()`
  - [ ] 18.2. Implement `is_tool_installed(tool)` checking all commands
  - [ ] 18.3. Implement `resolve_provider(tool, host, policy, registry)`
  - [ ] 18.4. Implement `create_install_plan(package_metadata, host, policy, registry)`
  - [ ] 18.5. Create `InstallPlan` dataclass with tools to install

- [ ] 19. Test Phase 5
  - [ ] 19.1. Verify command detection works
  - [ ] 19.2. Verify provider selection based on host
  - [ ] 19.3. Verify install plan generation
  - [ ] 19.4. Verify error when no provider available

### Phase 6: Provider Implementation

- [ ] 20. Create `qenv/providers/__init__.py`
  - [ ] 20.1. Set up provider package

- [ ] 21. Create `qenv/providers/base.py`
  - [ ] 21.1. Define `Provider` base class/interface
  - [ ] 21.2. Add `is_available(host)` method
  - [ ] 21.3. Add `install(tool, package_name, host)` method
  - [ ] 21.4. Add `requires_sudo` property

- [ ] 22. Create `qenv/providers/apt.py`
  - [ ] 22.1. Implement `is_available()` checking for apt-get
  - [ ] 22.2. Implement `install()` running `sudo apt-get install -y <package>`
  - [ ] 22.3. Set `requires_sudo = True`
  - [ ] 22.4. Add error handling for install failures

- [ ] 23. Create `qenv/providers/dnf.py`
  - [ ] 23.1. Implement `is_available()` checking for dnf
  - [ ] 23.2. Implement `install()` running `sudo dnf install -y <package>`
  - [ ] 23.3. Set `requires_sudo = True`
  - [ ] 23.4. Add error handling for install failures

- [ ] 24. Create `qenv/providers/pacman.py`
  - [ ] 24.1. Implement `is_available()` checking for pacman
  - [ ] 24.2. Implement `install()` running `sudo pacman -S --noconfirm <package>`
  - [ ] 24.3. Set `requires_sudo = True`
  - [ ] 24.4. Add error handling for install failures

- [ ] 25. Create `qenv/providers/brew.py`
  - [ ] 25.1. Implement `is_available()` checking for brew
  - [ ] 25.2. Implement `install()` running `brew install <package>`
  - [ ] 25.3. Set `requires_sudo = False`
  - [ ] 25.4. Add error handling for install failures

- [ ] 26. Create `qenv/providers/mise.py`
  - [ ] 26.1. Implement `is_available()` checking for mise
  - [ ] 26.2. Implement `install()` running `mise install <package>`
  - [ ] 26.3. Set `requires_sudo = False`
  - [ ] 26.4. Add error handling for install failures

- [ ] 27. Create provider factory in `qenv/providers/__init__.py`
  - [ ] 27.1. Implement `get_provider(provider_name)` factory function
  - [ ] 27.2. Register all provider classes
  - [ ] 27.3. Add error handling for unknown providers

- [ ] 28. Test Phase 6
  - [ ] 28.1. Test each provider's `is_available()` method
  - [ ] 28.2. Test installing a package with available provider
  - [ ] 28.3. Verify sudo is used when required
  - [ ] 28.4. Verify error handling on install failure

### Phase 7: Executor & Apply Command

- [ ] 29. Create `qenv/executor.py`
  - [ ] 29.1. Implement `execute_install_plan(plan, providers)`
  - [ ] 29.2. Add progress output for each tool installation
  - [ ] 29.3. Implement `stow_package(package_name, config)`
  - [ ] 29.4. Add error handling with clear messages
  - [ ] 29.5. Add dry-run support (optional but recommended)

- [ ] 30. Implement `apply` subcommand in `__main__.py`
  - [ ] 30.1. Parse package name argument
  - [ ] 30.2. Load package metadata
  - [ ] 30.3. Detect host capabilities
  - [ ] 30.4. Load policy and registry
  - [ ] 30.5. Create install plan
  - [ ] 30.6. Execute install plan
  - [ ] 30.7. Stow package
  - [ ] 30.8. Print success message

- [ ] 31. Test Phase 7
  - [ ] 31.1. Test `qenv apply <package>` with missing tools
  - [ ] 31.2. Test `qenv apply <package>` with existing tools
  - [ ] 31.3. Test error on unknown package
  - [ ] 31.4. Test error on missing tool in registry
  - [ ] 31.5. Test error on no available provider
  - [ ] 31.6. Verify stow works correctly

### Phase 8: Polish & Documentation

- [ ] 32. Add user-friendly output
  - [ ] 32.1. Add colored output (optional)
  - [ ] 32.2. Add progress indicators
  - [ ] 32.3. Improve error messages with suggestions
  - [ ] 32.4. Add verbose mode flag

- [ ] 33. Create README for qenv
  - [ ] 33.1. Document installation
  - [ ] 33.2. Document usage examples
  - [ ] 33.3. Document package.yaml format
  - [ ] 33.4. Document adding tools to registry

- [ ] 34. Add error recovery
  - [ ] 34.1. Handle partial failures gracefully
  - [ ] 34.2. Provide rollback suggestions
  - [ ] 34.3. Add `--force` flag for override scenarios

- [ ] 35. Final testing
  - [ ] 35.1. Test on Ubuntu system
  - [ ] 35.2. Test on Fedora system (if available)
  - [ ] 35.3. Test on macOS system (if available)
  - [ ] 35.4. Test all error conditions
  - [ ] 35.5. Test with various package configurations

### MVP Complete! 🎉

Once all items are checked, you have a working MVP that can:
- Detect your system
- Read package requirements
- Install missing tools
- Stow packages

Track your progress by checking off items as you complete them across sessions.
