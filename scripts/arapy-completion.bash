_arapy_complete() {
  local cur
  cur="${COMP_WORDS[COMP_CWORD]}"

  # Pass words after arapy, plus cursor index and current token
  local candidates
  candidates="$(arapy --_complete \
    --_cword="${COMP_CWORD}" \
    --_cur="${cur}" \
    "${COMP_WORDS[@]:1}" 2>/dev/null)"

  COMPREPLY=( $(compgen -W "${candidates}" -- "${cur}") )
  return 0
}

complete -F _arapy_complete arapy