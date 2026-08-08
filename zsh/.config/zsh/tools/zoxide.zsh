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

    # Offer local directories alongside zoxide's memorized directories for
    # ordinary queries such as `cd h` or `z proj`.
    _files -/

    local -a query_words
    query_words=("${(@)words[2,-1]}")
    if (( ${#query_words[@]} > 0 )) && [[ -z "${query_words[-1]}" ]]; then
      query_words=("${(@)query_words[1,-2]}")
    fi

    # Use zoxide's non-interactive list mode during completion. Interactive
    # query mode prints an error when a partial query has no matches, which
    # makes Tab completion look broken instead of simply returning no results.
    local output
    local -a matches
    if (( ${#query_words[@]} > 0 )); then
      output="$(\command zoxide query --list --exclude "$(__zoxide_pwd)" -- "${query_words[@]}" 2>/dev/null)"
      matches=("${(@f)output}")
    fi
    (( ${#matches[@]} )) && compadd -Q -- "${matches[@]}"
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
    if __zoxide_should_cd_directly "$@"; then
      __zoxide_cd "$1"
    else
      __zoxide_zi "$@"
    fi
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

  # Complete cd/z/zi from both the filesystem and zoxide's database. When
  # fzf is installed, use it to choose among multiple matches; otherwise
  # fall back to the normal zsh completion menu.
  __zoxide_fzf_candidates() {
    local current_word="$1"
    local pattern
    local -a local_matches zoxide_matches candidates

    if [[ "$current_word" == ~/* ]]; then
      pattern="$HOME/${current_word#~/}*"
    elif [[ "$current_word" == /* ]]; then
      pattern="${current_word}*"
    elif [[ "$current_word" == ./* ]]; then
      pattern="$PWD/${current_word#./}*"
    else
      pattern="$PWD/${current_word}*"
    fi
    local_matches=( ${~pattern}(N/) )

    local -a query_words
    query_words=(${(z)LBUFFER})
    query_words=(${query_words[2,-1]})
    [[ -z "$current_word" && ${#query_words} -gt 0 ]] && query_words=(${query_words[1,-2]})
    local output
    if (( ${#query_words} )); then
      output="$(\command zoxide query --list -- "${query_words[@]}" 2>/dev/null)"
    else
      output="$(\command zoxide query --list 2>/dev/null)"
    fi
    zoxide_matches=("${(@f)output}")

    candidates=("${local_matches[@]}" "${zoxide_matches[@]}")
    candidates=("${(@u)candidates}")
    reply=("${candidates[@]}")
  }

  __zoxide_fzf_completion_widget() {
    [[ -z "$RBUFFER" ]] || { zle expand-or-complete; return; }

    local -a tokens
    tokens=(${(z)LBUFFER})
    local command_name="${tokens[1]}"
    case "$command_name" in
      cd|z|zi) ;;
      *)
        if (( ${+widgets[fzf-completion]} )); then
          zle fzf-completion
        else
          zle expand-or-complete
        fi
        return
        ;;
    esac
    (( ${#tokens} > 1 )) || tokens+=("")

    local current_word="${tokens[-1]}"
    local -a candidates
    __zoxide_fzf_candidates "$current_word"
    candidates=("${reply[@]}")
    (( ${#candidates} )) || { zle expand-or-complete; return; }

    local selected preview_command
    if (( ${#candidates} == 1 )); then
      selected="${candidates[1]}"
    elif (( ${+commands[fzf]} )); then
      preview_command='if [ -d {} ]; then if command -v eza >/dev/null 2>&1; then command eza --tree --level=2 --color=always --icons -- {}; elif command -v tree >/dev/null 2>&1; then command tree -C -L 2 -- {}; else command find {} -maxdepth 2 -print 2>/dev/null; fi; elif command -v bat >/dev/null 2>&1; then command bat --color=always --style=numbers --line-range=:500 -- {}; elif command -v batcat >/dev/null 2>&1; then command batcat --color=always --style=numbers --line-range=:500 -- {}; else command sed -n "1,120p" -- {}; fi'
      selected="$(printf '%s\n' "${candidates[@]}" | fzf --height "${FZF_TMUX_HEIGHT:-40%}" --reverse --query "$current_word" --preview "$preview_command" --exit-0)"
      [[ -n "$selected" ]] || return
    else
      zle expand-or-complete
      return
    fi

    local before="$LBUFFER"
    if [[ -n "$current_word" ]]; then
      before="${LBUFFER[1,$(( ${#LBUFFER} - ${#current_word} ))]}"
    fi
    LBUFFER="${before}${(q)selected}"
  }

  if [[ -o zle ]]; then
    zle -N __zoxide_fzf_completion_widget
    bindkey -M viins '^I' __zoxide_fzf_completion_widget
  fi
fi
