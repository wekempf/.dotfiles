---
name: qenv
description: 'Use for qenv tasks in this dotfiles repo: add tools to qenv/registry.yaml, create or update package metadata in <package>/.qenv/package.yaml, adjust qenv.yaml or qenv/policies/policy.yaml, add provider backends under qenv/providers/, debug qenv apply behavior, and validate qenv package or host changes.'
argument-hint: '<task such as add tool, add package, update policy, debug apply>'
user-invocable: true
---

# qenv

Use this skill when working on qenv in this repository.

## When to Use

- Add a new tool to `qenv/registry.yaml`
- Update provider mappings for an existing tool
- Create a new managed package with `.qenv/package.yaml`
- Update package metadata such as required tools or stow target
- Adjust repository configuration in `qenv.yaml`
- Adjust install policy or provider order in `qenv/policies/policy.yaml`
- Add or update provider backends in `qenv/providers/`
- Debug `qenv apply`, `qenv host show`, or `qenv package list`
- Validate that qenv changes still resolve and apply correctly

## Repo Facts

- qenv is implemented as a repo-local Python CLI under `qenv/`
- Main entrypoint: `qenv/__main__.py`
- Repo config: `qenv.yaml`
- Policy file: `qenv/policies/policy.yaml`
- Tool registry: `qenv/registry.yaml`
- Package metadata: `<package>/.qenv/package.yaml`
- Provider backends are discovered dynamically from `qenv/providers/*.py`
- Package-local `.stow-local-ignore` files should exclude `.qenv` so metadata is never stowed

## Working Rules

1. Start from the specific qenv surface named by the user: tool, package, provider, policy, or failing command.
2. Prefer updating the owning qenv module or metadata file instead of patching around behavior in the CLI.
3. Keep provider behavior dynamic. Do not add hard-coded provider lists when extending qenv.
4. When adding a package, include both `.qenv/package.yaml` and the package-local `.stow-local-ignore` entries for `.qenv`.
5. After the first substantive edit, run the narrowest relevant validation command before widening scope.

## Procedure

### 1. Identify the task type

- Tool task: update `qenv/registry.yaml`
- Package task: update or create `<package>/.qenv/package.yaml`
- Config or policy task: update `qenv.yaml` or `qenv/policies/policy.yaml`
- Provider task: update `qenv/providers/` and any resolution logic that depends on it
- Apply failure: inspect the failing `qenv` command and the module that directly controls the failure

### 2. Gather only the local context you need

- Read the nearest controlling file first
- Read adjacent qenv metadata or a neighboring package only when needed to confirm schema or style
- Prefer existing qenv packages such as `zsh`, `bat`, or `ripgrep` as examples

### 3. Make the smallest correct change

Common changes:

- Add a tool entry with `commands` and `providers` in `qenv/registry.yaml`
- Add a package metadata file with `package`, `requires.tools.required`, and `stow`
- Add `.stow-local-ignore` entries:

```text
^\.qenv$
^\.qenv/.*$
```

- Update `qenv/policies/policy.yaml` provider order or install settings
- Add a provider backend module in `qenv/providers/` with a concrete provider subclass

### 4. Validate immediately

Choose the narrowest command that matches the change:

- Host or provider visibility:

```sh
python3 qenv/__main__.py --verbose host show
```

- Package discovery and metadata validation:

```sh
python3 qenv/__main__.py package list
python3 qenv/__main__.py --verbose package list
```

- Tool resolution and apply planning:

```sh
python3 qenv/__main__.py apply <package> --dry-run
python3 qenv/__main__.py --verbose apply <package> --dry-run
```

- Full apply only when the user wants real system changes:

```sh
python3 qenv/__main__.py apply <package>
```

### 5. Report the outcome clearly

- Name the user-visible behavior that changed
- Note the exact validation commands that passed
- Call out any remaining environment-limited gaps such as missing provider binaries or unavailable host platforms

## Task Playbooks

### Add a Tool

1. Update `qenv/registry.yaml`
2. Add the tool name, detection commands, and provider package mappings
3. If a new provider name is introduced, ensure a matching backend exists in `qenv/providers/`
4. Validate with `python3 qenv/__main__.py apply <package> --dry-run` for a package that requires the tool

### Add a Package

1. Create `<package>/.qenv/package.yaml`
2. Set `package.name` to match the directory name exactly
3. Add required tool names under `requires.tools.required`
4. Set `stow.enabled` and `stow.target`
5. Add or update `<package>/.stow-local-ignore` to exclude `.qenv`
6. Validate with `python3 qenv/__main__.py package list` and `python3 qenv/__main__.py apply <package> --dry-run`

### Update qenv Configuration or Policy

1. Edit `qenv.yaml` for repo-level stow settings
2. Edit `qenv/policies/policy.yaml` for install enablement, sudo behavior, or provider order
3. Validate with a narrow command such as `python3 qenv/__main__.py --verbose host show` or `python3 qenv/__main__.py apply <package> --dry-run`

### Add or Update a Provider Backend

1. Create or edit `qenv/providers/<provider>.py`
2. Implement the provider using the shared base class conventions already present in `qenv/providers/base.py`
3. Keep discovery dynamic so the provider is picked up from the filesystem
4. Add the provider to policy order only if the repo should consider it during selection
5. Validate with `python3 qenv/__main__.py --verbose host show` and a dry-run apply for a tool that can resolve through that provider

### Debug qenv Apply

1. Run the failing command again in the narrowest safe form, usually `--dry-run --verbose`
2. Identify whether the failure is configuration, registry, resolution, provider, or executor behavior
3. Step to the module that directly controls that behavior
4. Fix the root cause, then rerun the same command before broadening changes

## Output Expectations

- Default output should focus on changes, warnings, blockers, and failures
- Verbose output may include satisfied items and command output from installs or stow
- Recovery suggestions should stay concrete and point to the next validation command when possible

## Good End States

- A tool can be resolved from the registry and planned through a provider
- A package appears in `qenv package list`
- `qenv apply <package> --dry-run` shows the expected tool and stow actions
- Real apply is only used when the user intends to change the system