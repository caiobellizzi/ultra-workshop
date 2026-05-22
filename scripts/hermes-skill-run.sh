#!/usr/bin/env bash
# scripts/hermes-skill-run.sh
# Usage: hermes-skill-run.sh <skill-name> [--dry-run] [--key value ...]
# Wraps `hermes chat --skills <name> --query <q> -Q --max-turns <N> --yolo`.
# Per-skill --max-turns defaults below; override with MAX_TURNS env var.
# Note: --dry-run is signalled at the SKILL.md body level via this guard only;
# the Hermes binary itself does not understand --dry-run.

set -euo pipefail

if [ $# -eq 0 ] || [ -z "${1:-}" ]; then
  echo "Usage: hermes-skill-run.sh <skill-name> [--dry-run] [--key value ...]" >&2
  exit 1
fi

SKILL="$1"
shift
QUERY="$*"

# Per-skill --max-turns budget. Triage just classifies (cheap); coder/reviewer/planner
# need headroom to read, plan, write, and verify. Override with MAX_TURNS env var.
if [ -z "${MAX_TURNS:-}" ]; then
  case "$SKILL" in
    triage-specialist)   MAX_TURNS=3 ;;
    planner-specialist)  MAX_TURNS=8 ;;
    reviewer-specialist) MAX_TURNS=10 ;;
    coder-specialist)    MAX_TURNS=15 ;;
    *)                   MAX_TURNS=8 ;;
  esac
fi

# Dry-run short-circuit: print what would run and exit 0.
if echo "$QUERY" | grep -q -- "--dry-run"; then
  echo "[dry-run] would run: hermes chat --skills ${SKILL} --query '${QUERY}' -Q --max-turns ${MAX_TURNS} --yolo"
  exit 0
fi

# Production path: exec replaces this process; positional args prevent shell injection.
# Use an isolated HERMES_HOME for specialist subprocess calls to avoid state.db
# conflicts with the running Hermes gateway (which uses /home/uws/.hermes).
# cd to uws home first — hermes walks up from cwd looking for HERMES.md and will
# hit PermissionError if cwd is /root or another directory uws cannot stat.
HERMES_BIN="/opt/ultra-workshop/hermes/venv/bin/hermes"
SPECIALIST_HOME="/opt/ultra-workshop/specialist-home"
UWS_HOME=$(getent passwd uws 2>/dev/null | cut -d: -f6 || echo "/home/uws")
cd "$UWS_HOME" 2>/dev/null || cd /tmp
UWS_UID=$(id -u uws 2>/dev/null || echo "")
if [ -n "$UWS_UID" ] && [ "$(id -u)" = "$UWS_UID" ]; then
  exec env HERMES_HOME="$SPECIALIST_HOME" \
    "$HERMES_BIN" chat --skills "$SKILL" --query "$QUERY" -Q --max-turns "$MAX_TURNS" --yolo
else
  exec sudo -u uws env HERMES_HOME="$SPECIALIST_HOME" \
    "$HERMES_BIN" chat --skills "$SKILL" --query "$QUERY" -Q --max-turns "$MAX_TURNS" --yolo
fi
