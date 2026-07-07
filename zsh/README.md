# Zsh Configuration

A portable, modular zsh configuration that works across different machines with varying tool installations.

## Features

- **Conditional Loading**: Configurations only load if the required tools are installed
- **Modular Design**: Tool-specific configurations in separate files
- **Flexible Installation**: Install only the tools you need
- **Cross-Machine Compatible**: Works seamlessly across different setups

## Installation

### Basic Setup (zsh only)

```bash
./setup
```

### Install Specific Tools

```bash
./setup-tools fzf eza neovim
```

### Install All Available Tools

```bash
./setup-tools --all
```

### Interactive Selection

```bash
./setup-tools --interactive
```

### List Available Tools

```bash
./setup-tools --list
```

## Available Optional Tools

The configuration supports the following optional tools. Each tool's configuration only loads if the tool is installed:

- **zoxide** - Smarter cd command that learns your habits
- **fzf** - Fuzzy finder for command-line
- **eza** - Modern replacement for ls with icons and colors
- **neovim** - Hyperextensible Vim-based text editor
- **bat** - Cat clone with syntax highlighting
- **ripgrep** - Fast grep alternative
- **fd** - Fast find alternative
- **delta** - Syntax-highlighting pager for git

## Structure

```
.config/zsh/
├── .zshrc              # Main zsh configuration
├── aliases.zsh         # General aliases
├── prompt.zsh          # Custom prompt (loaded if starship not available)
├── functions.zsh       # Custom functions (optional)
├── local_env.zsh       # Machine-specific config (optional, not in git)
├── tools.yaml          # Tool definitions and metadata
└── tools/              # Tool-specific configurations
    ├── zoxide.zsh
    ├── fzf.zsh
    ├── eza.zsh
    ├── neovim.zsh
    ├── bat.zsh
    ├── ripgrep.zsh
    ├── fd.zsh
    └── delta.zsh
```

## How It Works

1. **Conditional Loading**: Each tool configuration in `tools/*.zsh` checks if the tool is installed before applying settings
2. **Automatic Discovery**: The main `.zshrc` automatically sources all tool configurations
3. **No Errors**: Missing tools don't cause errors or warnings
4. **Override Support**: Create `local_env.zsh` for machine-specific overrides

## Adding New Tools

1. Add tool info to `tools.yaml`
2. Create `tools/<toolname>.zsh` with conditional checks:
   ```zsh
   if command -v <toolname> >/dev/null 2>&1; then
     # Tool configuration here
   fi
   ```
3. Update `setup-tools` script to include the new tool

## Machine-Specific Configuration

Create `.config/zsh/local_env.zsh` (gitignored) for machine-specific settings:

```zsh
# Example local_env.zsh
export CUSTOM_VAR="value"
alias custom-alias="command"
```

## Examples

### Minimal Setup (Development Server)
```bash
./setup
./setup-tools fzf ripgrep
```

### Full Featured (Personal Workstation)
```bash
./setup
./setup-tools --all
```

### Custom Selection
```bash
./setup
./setup-tools fzf eza bat neovim zoxide
```
