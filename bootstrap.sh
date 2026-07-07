#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "$(readlink -f -- "${BASH_SOURCE[0]}")")" && pwd -P)"
DOTFILES="$SCRIPT_DIR"
BIN_HOME="${XDG_BIN_HOME:-$HOME/.local/bin}"
QENV_SOURCE="$DOTFILES/qenv/qenv"
QENV_LINK="$BIN_HOME/qenv"

find_python_command() {
  if command -v python3 >/dev/null 2>&1; then
    return 0
  fi

  if command -v python >/dev/null 2>&1 \
    && python -c 'import sys; raise SystemExit(0 if sys.version_info.major == 3 else 1)' >/dev/null 2>&1; then
    return 0
  fi

  return 1
}

have_stow_command() {
  command -v stow >/dev/null 2>&1
}

detect_package_manager() {
  if command -v apt-get >/dev/null 2>&1; then
    echo apt
    return 0
  fi

  if command -v dnf >/dev/null 2>&1; then
    echo dnf
    return 0
  fi

  if command -v pacman >/dev/null 2>&1; then
    echo pacman
    return 0
  fi

  if command -v brew >/dev/null 2>&1; then
    echo brew
    return 0
  fi

  return 1
}

package_name_for_tool() {
  local manager="$1"
  local tool="$2"

  case "$manager:$tool" in
    apt:python|dnf:python)
      echo python3
      ;;
    pacman:python|brew:python)
      echo python
      ;;
    apt:stow|dnf:stow|pacman:stow|brew:stow)
      echo stow
      ;;
    *)
      echo "bootstrap: no package mapping for $tool via $manager" >&2
      return 1
      ;;
  esac
}

install_system_packages() {
  local manager="$1"
  shift

  if [[ "$manager" == apt ]]; then
    if [[ "$(id -u)" -eq 0 ]]; then
      apt-get update
      apt-get install -y "$@"
    elif command -v sudo >/dev/null 2>&1; then
      "$DOTFILES/__setup/apt-update"
      sudo apt-get install -y "$@"
    else
      echo "bootstrap: apt-get requires sudo to install $*" >&2
      return 1
    fi
    return 0
  fi

  if [[ "$manager" == dnf ]]; then
    if [[ "$(id -u)" -eq 0 ]]; then
      dnf install -y "$@"
    elif command -v sudo >/dev/null 2>&1; then
      sudo dnf install -y "$@"
    else
      echo "bootstrap: dnf requires sudo to install $*" >&2
      return 1
    fi
    return 0
  fi

  if [[ "$manager" == pacman ]]; then
    if [[ "$(id -u)" -eq 0 ]]; then
      pacman -Sy --noconfirm "$@"
    elif command -v sudo >/dev/null 2>&1; then
      sudo pacman -Sy --noconfirm "$@"
    else
      echo "bootstrap: pacman requires sudo to install $*" >&2
      return 1
    fi
    return 0
  fi

  if [[ "$manager" == brew ]]; then
    brew install "$@"
    return 0
  fi

  echo "bootstrap: unable to install required tools automatically: $*" >&2
  return 1
}

ensure_bootstrap_tools() {
  local -a missing_tools=()
  local -a packages=()
  local manager
  local tool
  local package

  if ! find_python_command; then
    missing_tools+=(python)
  fi

  if ! have_stow_command; then
    missing_tools+=(stow)
  fi

  if (( ${#missing_tools[@]} == 0 )); then
    return 0
  fi

  if ! manager="$(detect_package_manager)"; then
    echo "bootstrap: unable to install required tools automatically: ${missing_tools[*]}" >&2
    echo "bootstrap: install ${missing_tools[*]} and rerun $0" >&2
    return 1
  fi

  for tool in "${missing_tools[@]}"; do
    package="$(package_name_for_tool "$manager" "$tool")" || return 1
    packages+=("$package")
  done

  echo "bootstrap: installing required tools: ${missing_tools[*]}"
  install_system_packages "$manager" "${packages[@]}"
}

bin_home_in_path() {
  case ":$PATH:" in
    *":$BIN_HOME:"*)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

print_path_guidance() {
  if bin_home_in_path; then
    echo "bootstrap: $BIN_HOME already in PATH"
    return 0
  fi

  echo "bootstrap: qenv is linked at $QENV_LINK" >&2
  echo "bootstrap: add $BIN_HOME to PATH in your shell profile to run qenv directly in new shells" >&2
}

if [[ ! -f "$QENV_SOURCE" ]]; then
  echo "bootstrap: missing qenv launcher at $QENV_SOURCE" >&2
  exit 1
fi

ensure_bootstrap_tools

if ! find_python_command; then
  echo "bootstrap: python3 is still unavailable after bootstrap" >&2
  exit 1
fi

if ! have_stow_command; then
  echo "bootstrap: stow is still unavailable after bootstrap" >&2
  exit 1
fi

mkdir -p "$BIN_HOME"
ln -sfn "$QENV_SOURCE" "$QENV_LINK"

echo "bootstrap: linked $QENV_LINK -> $QENV_SOURCE"
print_path_guidance

if (( $# > 0 )); then
  echo "bootstrap: environment bootstrapped; bootstrap does not execute qenv commands" >&2
  echo "bootstrap: run $QENV_LINK yourself after bootstrap completes" >&2
fi