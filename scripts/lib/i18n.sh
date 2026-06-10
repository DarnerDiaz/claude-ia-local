#!/bin/bash
# i18n.sh — bilingual (Spanish/English) message helper for Claude IA Local.
#
# Scripts source this file and then call `t` to print the message in the
# user's language. Auto-detects from $LANG (anything starting with "es" →
# Spanish, otherwise English). Override explicitly with IDIOMA=es | IDIOMA=en.
#
#   source "$(dirname "$0")/lib/i18n.sh"
#   t "Hola mundo" "Hello world"
#   echo "$(t "Listo" "Done")"
#
# Keep it dependency-free: pure bash, safe to source from any script.

# ── Language detection ────────────────────────────────────────
# IDIOMA wins if set; otherwise sniff $LANG/$LC_ALL. Default: English, since
# the bare scripts historically printed English and HF/MLX tooling is English.
_detect_lang() {
  local pref="${IDIOMA:-}"
  if [ -z "$pref" ]; then
    case "${LC_ALL:-${LANG:-}}" in
      es*|ES*|Es*) pref="es" ;;
      *)           pref="en" ;;
    esac
  fi
  case "$pref" in
    es|ES|spanish|español|espanol) echo "es" ;;
    *)                             echo "en" ;;
  esac
}

CLAUDE_LOCAL_LANG="$(_detect_lang)"

# t SPANISH ENGLISH — print the right one (no trailing newline control;
# callers wrap in echo or use printf as needed). Returns the string on stdout.
t() {
  if [ "$CLAUDE_LOCAL_LANG" = "es" ]; then
    printf '%s' "$1"
  else
    printf '%s' "$2"
  fi
}

# tln SPANISH ENGLISH — like t, but appends a newline. Convenience for echo-style use.
tln() {
  t "$1" "$2"
  printf '\n'
}
