# zoxide configuration
if command -v zoxide >/dev/null 2>&1; then
  eval "$(zoxide init zsh --no-cmd)"

  __zoxide_should_cd_directly() {
    [[ "$#" -eq 1 ]] && { [[ -d "$1" ]] || [[ "$1" = '-' ]] || [[ "$1" =~ ^[-+][0-9]$ ]]; }
  }

  __zoxide_should_complete_path() {
    local current_word="$1"
    [[ "$current_word" == [./~]* || "$current_word" == */* || "$current_word" == '-' || "$current_word" =~ ^[-+][0-9]$ ]]
  }

  __zoxide_complete_with_picker() {
    [[ "${#words[@]}" -eq "${CURRENT}" ]] || return 0

    local current_word="${words[CURRENT]}"
    if (( CURRENT == 2 )) && [[ -z "$current_word" ]]; then
      _files -/
      return 0
    fi

    if __zoxide_should_complete_path "$current_word"; then
      _files -/
      return 0
    fi

    local -a query_words
    query_words=("${(@)words[2,-1]}")
    if (( ${#query_words[@]} > 0 )) && [[ -z "${query_words[-1]}" ]]; then
      query_words=("${(@)query_words[1,-2]}")
    fi

    local result
    if result="$(\command zoxide query --exclude "$(__zoxide_pwd)" --interactive -- "${query_words[@]}")"; then
      compadd -Q -- "${(q-)result}"
    fi
    \builtin printf '\e[5n'
    return 0
  }

  z() {
    if __zoxide_should_cd_directly "$@"; then
      __zoxide_cd "$1"
    else
      __zoxide_zi "$@"
    fi
  }

  zi() {
    __zoxide_zi "$@"
  }

  cd() {
    if [[ "$#" -eq 0 ]]; then
      __zoxide_cd ~
    elif __zoxide_should_cd_directly "$@"; then
      __zoxide_cd "$1"
    else
      __zoxide_zi "$@"
    fi
  }

  if [[ -o zle ]] && [[ "${+functions[compdef]}" -ne 0 ]]; then
    compdef __zoxide_complete_with_picker z
    compdef __zoxide_complete_with_picker zi
    compdef __zoxide_complete_with_picker cd
  fi
fi
