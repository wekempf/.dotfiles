# fzf configuration
if [[ -f ~/.fzf.zsh ]]; then
  source ~/.fzf.zsh
elif command -v fzf >/dev/null 2>&1; then
  # Set up fzf key bindings if available
  if [[ -f /usr/share/doc/fzf/examples/key-bindings.zsh ]]; then
    source /usr/share/doc/fzf/examples/key-bindings.zsh
  fi
  if [[ -f /usr/share/doc/fzf/examples/completion.zsh ]]; then
    source /usr/share/doc/fzf/examples/completion.zsh
  fi
fi

# Configure fzf integrations with other tools
if command -v fzf >/dev/null 2>&1; then
  # Use bat for preview if available
  if has_bat; then
    export FZF_DEFAULT_OPTS="--preview '$(get_bat_cmd) --color=always --style=numbers --line-range=:500 {}'"
  fi
  
  # Use fd for file searching if available
  if has_fd; then
    export FZF_DEFAULT_COMMAND="$(get_fd_cmd) --type f --hidden --follow --exclude .git"
    export FZF_CTRL_T_COMMAND="$FZF_DEFAULT_COMMAND"
    export FZF_ALT_C_COMMAND="$(get_fd_cmd) --type d --hidden --follow --exclude .git"
  fi
fi
