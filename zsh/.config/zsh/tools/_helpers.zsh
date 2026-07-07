# Helper functions for tool configurations
# Loaded first before individual tool configs

# Check if bat is available (handles both bat and batcat)
has_bat() {
  whence -p bat >/dev/null 2>&1 || whence -p batcat >/dev/null 2>&1
}

# Get the actual bat command name
get_bat_cmd() {
  if whence -p bat >/dev/null 2>&1; then
    echo "bat"
  elif whence -p batcat >/dev/null 2>&1; then
    echo "batcat"
  fi
}

# Check if fd is available (handles both fd and fdfind)
has_fd() {
  whence -p fd >/dev/null 2>&1 || whence -p fdfind >/dev/null 2>&1
}

# Get the actual fd command name
get_fd_cmd() {
  if whence -p fd >/dev/null 2>&1; then
    echo "fd"
  elif whence -p fdfind >/dev/null 2>&1; then
    echo "fdfind"
  fi
}
