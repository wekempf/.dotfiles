autoload -U colors && colors

if zmodload zsh/datetime 2>/dev/null; then
  typeset -gF __zsh_startup_begin=$EPOCHREALTIME

  autoload -Uz add-zsh-hook
  __zsh_report_startup_time() {
    emulate -L zsh
    add-zsh-hook -d precmd __zsh_report_startup_time 2>/dev/null

    local -F elapsed
    elapsed=$(( EPOCHREALTIME - __zsh_startup_begin ))
    printf 'zsh startup: %.3fs\n' "$elapsed"
  }
  add-zsh-hook -d precmd __zsh_report_startup_time 2>/dev/null
  add-zsh-hook precmd __zsh_report_startup_time
fi

if [[ -f "$ZDOTDIR/local_env.zsh" ]]; then
    source "$ZDOTDIR/local_env.zsh"
fi

if [[ -z "${DOTFILES:-}" ]]; then
  if [[ -d "$HOME/.dotfiles" ]]; then
    DOTFILES="$HOME/.dotfiles"
  else
    echo "Error: DOTFILES environment variable is not set." >&2
  fi
fi

if [[ -n "${DOTFILES:-}" && -d "$DOTFILES" ]]; then
  DOTFILES="$(cd -- "$DOTFILES" && pwd -P)"
  export DOTFILES
fi

path=("$HOME/.local/bin" $path)
export PATH

if [[ -f "$ZDOTDIR/options.zsh" ]]; then
    source "$ZDOTDIR/options.zsh"
fi
setopt autocd
setopt interactive_comments

export HISTSIZE=268435456
export SAVEHIST="$HISTSIZE"
export HISTFILE="${XDG_STATE_HOME:-$HOME/.local/state}/zsh/history"
setopt INC_APPEND_HISTORY

bindkey '^R' history-incremental-search-backward

# Create state directory for zsh runtime files
mkdir -p "${XDG_STATE_HOME:-$HOME/.local/state}/zsh"

autoload -U compinit
zstyle ':completion:*' menu select
zmodload zsh/complist
compinit -d "${XDG_STATE_HOME:-$HOME/.local/state}/zsh/zcompdump"
_comp_options+=(globdots)

# Load tool-specific configurations
if [[ -d "$ZDOTDIR/tools" ]]; then
  # Load helpers first (files starting with _)
  for tool_config in "$ZDOTDIR/tools"/_*.zsh; do
    if [[ -f "$tool_config" ]]; then
      source "$tool_config"
    fi
  done
  
  # Then load other tool configs
  for tool_config in "$ZDOTDIR/tools"/*.zsh; do
    if [[ -f "$tool_config" ]] && [[ ! "$(basename "$tool_config")" =~ ^_ ]]; then
      source "$tool_config"
    fi
  done
fi

bindkey -v
export KEYTIMEOUT=1

bindkey -M viins '^[[A' history-beginning-search-backward
bindkey -M viins '^[[B' history-beginning-search-forward

bindkey -M menuselect 'h' vi-backward-char
bindkey -M menuselect 'k' vi-up-line-or-history
bindkey -M menuselect 'l' vi-forward-char
bindkey -M menuselect 'j' vi-down-line-or-history
bindkey -v '^?' backward-delete-char

function zle-keymap-select () {
    case $KEYMAP in
        vicmd) echo -ne '\e[1 q';;
        viins|main) echo -ne '\e[5 q';;
    esac
}
zle -N zle-keymap-select
#zle-line-init() {
#    zle -K viins  initiate `vi insert` as keymap (can be removed if `bindkey -V` has been set elsewhere)
#    echo -ne "\e[5 q"
#}
#zle -N zle-line-init
echo -ne '\e[5 q'
preexec() { echo -ne '\e[5 q' ;}
#
#bindkey -s '^a' 'bc -lq\n'
#bindkey -s '^f' 'cd "$(dirname "$(fzf)")"\n'
#
#bindkey '^[[P' delete-char
#
#autoload edit-command-line; zle -N edit-command-line
#bindkey '^e' edit-command-line
#
#source /usr/local/opt/zsh-fast-syntax-highlighting/share/zsh-fast-syntax-highlighting/fast-syntax-highlighting.plugin.zsh


#alias rm="trash"
#
#pk() {
#  pgrep -i "$1" | sudo xargs kill -9
#}
#
if [[ -f "$ZDOTDIR/aliases.zsh" ]]; then
    source "$ZDOTDIR/aliases.zsh"
fi
if [[ -f "$ZDOTDIR/functions.zsh" ]]; then
    source "$ZDOTDIR/functions.zsh"
fi
if [[ -f "$ZDOTDIR/prompt.zsh" ]]; then
    source "$ZDOTDIR/prompt.zsh"
fi
if [[ -d "$HOME/.local/bin" ]]; then
    __add_path "$HOME/.local/bin"
fi
