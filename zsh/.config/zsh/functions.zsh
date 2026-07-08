__add_path() {
    local candidate existing
    local -a additions

    for candidate in "$@"; do
        [[ -n "$candidate" ]] || continue

        for existing in "${path[@]}" "${additions[@]}"; do
            [[ "$existing" == "$candidate" ]] && continue 2
        done

        additions+=("$candidate")
    done

    (( ${#additions[@]} )) || return 0

    path=("${additions[@]}" "${path[@]}")
    export PATH
}
# Shell functions

# mcd: make directory and cd into it
mcd() {
  mkdir -p "$1" && cd "$1"
}
