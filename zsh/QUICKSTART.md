# Zsh Configuration - Quick Reference

## Fresh Machine Setup

### Option 1: Minimal (just zsh)
```bash
cd ~/.dotfiles/zsh
./setup
```

### Option 2: Interactive Selection
```bash
cd ~/.dotfiles/zsh
./setup-tools --interactive
```

### Option 3: Full Install
```bash
cd ~/.dotfiles/zsh
./setup-tools --all
```

### Option 4: Custom Selection
```bash
cd ~/.dotfiles/zsh
./setup-tools fzf eza neovim zoxide ripgrep
```

## Tool Recommendations by Use Case

### Minimal Developer Setup
```bash
./setup-tools fzf ripgrep
```
Essential for searching and fuzzy finding.

### Enhanced Terminal Experience
```bash
./setup-tools fzf eza bat zoxide
```
Better ls, cat, cd, and fuzzy finding.

### Full Power User Setup
```bash
./setup-tools --all
```
All productivity enhancements.

### Server/Remote Machine
```bash
./setup-tools ripgrep fzf
```
Lightweight, focused on searching and navigation.

## Tool Benefits

| Tool | Replaces | Key Benefit |
|------|----------|-------------|
| zoxide | cd | Learns your habits, jump to frequent dirs |
| fzf | ctrl+r | Fuzzy search history, files, commands |
| eza | ls | Colors, icons, tree view |
| neovim | vim | Modern, extensible editor |
| bat | cat | Syntax highlighting, line numbers |
| ripgrep | grep | Faster, smarter searching |
| fd | find | Simpler syntax, faster |
| delta | git diff | Better diff visualization |

## Checking Installation Status

```bash
cd ~/.dotfiles/zsh
./setup-tools --list
```

Or manually check:
```bash
command -v zoxide fzf eza nvim bat rg fd delta
```

## Adding Machine-Specific Config

Create `~/.config/zsh/local_env.zsh`:
```zsh
# This file is gitignored - add machine-specific settings here
export MY_CUSTOM_VAR="value"
alias my-alias="command"
```

## Troubleshooting

### Tools not working after install
Source your zshrc or restart shell:
```bash
source ~/.zshrc
# or
exec zsh
```

### Check what's loaded
```bash
# See which tool configs are active
ls ~/.config/zsh/tools/*.zsh | while read f; do
  tool=$(basename "$f" .zsh)
  if command -v "$tool" >/dev/null 2>&1; then
    echo "✓ $tool"
  else
    echo "✗ $tool (config present but tool not installed)"
  fi
done
```

## Uninstalling Tools

Tools can be removed with your package manager:
```bash
# Ubuntu/Debian
sudo apt remove <tool-name>
```

The configuration will automatically skip missing tools - no cleanup needed!
