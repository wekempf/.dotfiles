# eza (modern ls) configuration
if command -v eza >/dev/null 2>&1; then
  alias ls="eza --icons"
  alias la="eza --icons -a --group-directories-first"
  alias ll="eza --icons -lh --group-directories-first"
  alias lla="eza --icons -lha --group-directories-first"
  alias lt="eza --icons --tree"
fi
