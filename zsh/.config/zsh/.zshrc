autoload -U colors && colors

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

setopt autocd
setopt interactive_comments

export HISTSIZE=268435456
export SAVEHIST="$HISTSIZE"
export HISTFILE="$ZDOTDIR/.zsh_history"
setopt INC_APPEND_HISTORY

bindkey '^R' history-incremental-search-backward

autoload -U compinit
zstyle ':completion:*' menu select
zmodload zsh/complist
compinit
_comp_options+=(globdots)

bindkey -v
export KEYTIMEOUT=1

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
[ -f ~/.fzf.zsh ] && source ~/.fzf.zsh

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
