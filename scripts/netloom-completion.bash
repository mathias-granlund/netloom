_netloom_backend_path() {
  local cli
  cli="$1"
  local backend

  backend="$(type -P -- "${cli}")"
  if [[ -z "${backend}" ]]; then
    backend="$(type -P -- netloom)"
  fi
  printf '%s\n' "${backend}"
}

_netloom_emit_timing() {
  local stderr_file
  stderr_file="$1"
  if [[ -s "${stderr_file}" ]]; then
    grep '^\[netloom timing\]' "${stderr_file}" >&2 || true
  fi
}

_netloom_insert_question_mark() {
  READLINE_LINE="${READLINE_LINE:0:READLINE_POINT}?${READLINE_LINE:READLINE_POINT}"
  READLINE_POINT=$((READLINE_POINT + 1))
}

_netloom_complete() {
  local cur
  cur="${COMP_WORDS[COMP_CWORD]}"
  local cli
  cli="${COMP_WORDS[0]}"
  local backend

  backend="$(_netloom_backend_path "${cli}")"
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

  _netloom_emit_timing "${stderr_file}"
  rm -f "${stderr_file}"

  COMPREPLY=( $(compgen -W "${candidates}" -- "${cur}") )
  return 0
}

_netloom_describe_context() {
  local backend
  backend="$(_netloom_backend_path "netloom")"
  if [[ -z "${backend}" ]]; then
    _netloom_insert_question_mark
    return 0
  fi

  if [[ "${READLINE_POINT}" -ne "${#READLINE_LINE}" ]]; then
    _netloom_insert_question_mark
    return 0
  fi
  if [[ -n "${READLINE_LINE}" && "${READLINE_LINE}" != *[[:space:]] ]]; then
    _netloom_insert_question_mark
    return 0
  fi

  local words=()
  read -r -a words <<< "${READLINE_LINE}"
  if [[ "${#words[@]}" -eq 0 || "${words[0]}" != "netloom" ]]; then
    _netloom_insert_question_mark
    return 0
  fi

  local stderr_file
  stderr_file="$(mktemp)"
  local output
  output="$("${backend}" --_describe "${words[@]:1}" 2>"${stderr_file}")"

  _netloom_emit_timing "${stderr_file}"
  rm -f "${stderr_file}"

  if [[ -n "${output}" ]]; then
    printf '\n%s\n' "${output}"
  fi
  return 0
}

complete -F _netloom_complete netloom
bind -x '"?":_netloom_describe_context'
