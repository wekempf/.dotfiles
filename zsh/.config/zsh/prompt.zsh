autoload -Uz vcs_info
precmd() { vcs_info }
dir_status() {
    local sstatus
    if [ -n "${vcs_info_msg_0_}" ]; then
        local gitstatus
        gitstatus=$(git status --porcelain 2>/dev/null)

        sstatus=''
        if [ -n "$(grep '^\?\?' <<< "$gitstatus")" ]; then
            sstatus+="%F{red}●"
        fi
        if [ -n "$(grep '^.[^ ?]' <<< "$gitstatus")" ]; then
            sstatus+="%F{cyan}●"
        fi
        if [ -n "$(grep '^[^? ]' <<< "$gitstatus")" ]; then
            sstatus+="%F{green}●"
        fi
    fi
    echo $sstatus
}
zstyle ':vcs_info:*' check-for-changes true
zstyle ':vcs_info:git*' formats "%F{blue}⎇ %b"
zstyle ':vcs_info:git*' actionformats "%F{yellow}⎇ %b|%a"
PROMPT='🐧 %F{cyan}%~ %f$vcs_info_msg_0_$(dir_status) %F{white}→ '
