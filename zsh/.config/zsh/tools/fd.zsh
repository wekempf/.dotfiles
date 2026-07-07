# fd (modern find) configuration
if command -v fd >/dev/null 2>&1; then
  alias find="fd"
elif command -v fdfind >/dev/null 2>&1; then
  # Ubuntu packages fd as fdfind
  alias fd="fdfind"
  alias find="fdfind"
fi
