_netloom_complete() {
  local cur
  cur="${COMP_WORDS[COMP_CWORD]}"
  local cli
  cli="${COMP_WORDS[0]}"
  local backend

  backend="$(type -P -- "${cli}")"
  if [[ -z "${backend}" ]]; then
    backend="$(type -P -- netloom)"
  fi
  if [[ -z "${backend}" ]]; then
    COMPREPLY=()
    return 0
  fi

  local candidates
  local stderr_file
  stderr_file="$(mktemp)"
  candidates="$("${backend}" --_complete \
    --_cword="${COMP_CWORD}" \
    --_cur="${cur}" \
    "${COMP_WORDS[@]:1}" 2>"${stderr_file}")"

  if [[ -s "${stderr_file}" ]]; then
    grep '^\[netloom timing\]' "${stderr_file}" >&2 || true
  fi
  rm -f "${stderr_file}"

  COMPREPLY=( $(compgen -W "${candidates}" -- "${cur}") )
  return 0
}

complete -F _netloom_complete netloom
