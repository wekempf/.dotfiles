# bat (cat with syntax highlighting) configuration
if command -v bat >/dev/null 2>&1; then
  alias cat="bat --style=plain"
  export MANPAGER="sh -c 'col -bx | bat -l man -p'"
elif command -v batcat >/dev/null 2>&1; then
  # Ubuntu packages bat as batcat
  alias bat="batcat"
  alias cat="batcat --style=plain"
  export MANPAGER="sh -c 'col -bx | batcat -l man -p'"
fi
