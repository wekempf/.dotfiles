# General aliases (tool-specific aliases are in tools/*.zsh)
alias shell="${EDITOR:-vi} $ZDOTDIR/.zshrc"
alias profile="${EDITOR:-vi} $HOME/.zprofile"
alias sc='source $HOME/.config/zsh/.zshrc'
alias cdx='codex'
alias cdxy='codex --dangerously-bypass-approvals-and-sandbox'
alias cdxh='codex --profile homeassistant'
alias cdxhy='codex --profile homeassistant --dangerously-bypass-approvals-and-sandbox'
alias aptu='sudo apt update && sudo apt upgrade -y'

# PowerShell-like aliases
alias md='mkdir'
alias cls='clear'
alias tree='eza --tree --level=2 --icons'
