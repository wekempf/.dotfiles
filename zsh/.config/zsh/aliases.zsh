# General aliases (tool-specific aliases are in tools/*.zsh)
alias shell="${EDITOR:-vi} $ZDOTDIR/.zshrc"
alias profile="${EDITOR:-vi} $HOME/.zprofile"
alias sc='source $HOME/.config/zsh/.zshrc'

# PowerShell-like aliases
alias md='mkdir'
alias cls='clear'
alias tree='eza --tree --level=2 --icons'
