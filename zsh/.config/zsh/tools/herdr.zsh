# herdr configuration
if command -v herdr >/dev/null 2>&1 && command -v direnv >/dev/null 2>&1; then
  alias herds='herdr --session $HERDR_SESSION'
fi
