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

# Per-skill --max-turns budget AND per-skill HERMES_HOME selection (one home per
# model alias — see plan 04-04). Triage stays on private-worker (V17 local-token
# contract); planner and coder use NIM `orchestrator` (DSv4 Pro) — coder was
# routed to private-worker originally but Gemma-4-e4b could not reliably drive
# the SKILL.md tool-use + JSON contract (UAT 04 / 2026-05-22). Reviewer uses
# NIM `research-worker`. Override turns with MAX_TURNS, home with
# SPECIALIST_HOME_OVERRIDE.
if [ -z "${MAX_TURNS:-}" ]; then
  case "$SKILL" in
    triage-specialist)   MAX_TURNS=3;  HOME_DIR=specialist-home-private ;;
    planner-specialist)  MAX_TURNS=8;  HOME_DIR=specialist-home-orchestrator ;;
    reviewer-specialist) MAX_TURNS=10; HOME_DIR=specialist-home-research ;;
    coder-specialist)    MAX_TURNS=15; HOME_DIR=specialist-home-orchestrator ;;
    *)                   MAX_TURNS=8;  HOME_DIR=specialist-home-private ;;
  esac
else
  case "$SKILL" in
    triage-specialist)   HOME_DIR=specialist-home-private ;;
    planner-specialist)  HOME_DIR=specialist-home-orchestrator ;;
    reviewer-specialist) HOME_DIR=specialist-home-research ;;
    coder-specialist)    HOME_DIR=specialist-home-orchestrator ;;
    *)                   HOME_DIR=specialist-home-private ;;
  esac
fi

# Dry-run short-circuit: print what would run and exit 0. Includes the resolved
# HERMES_HOME so per-skill model routing can be asserted in bats smoke tests.
if echo "$QUERY" | grep -q -- "--dry-run"; then
  echo "[dry-run] would run: hermes chat --skills ${SKILL} --query '${QUERY}' -Q --max-turns ${MAX_TURNS} --yolo"
  echo "[dry-run] HERMES_HOME=/opt/ultra-workshop/${HOME_DIR}"
  exit 0
fi

# Production path: exec replaces this process; positional args prevent shell injection.
# Use an isolated HERMES_HOME for specialist subprocess calls to avoid state.db
# conflicts with the running Hermes gateway (which uses /home/uws/.hermes).
# cd to uws home first — hermes walks up from cwd looking for HERMES.md and will
# hit PermissionError if cwd is /root or another directory uws cannot stat.
HERMES_BIN="/opt/ultra-workshop/hermes/venv/bin/hermes"
SPECIALIST_HOME="${SPECIALIST_HOME_OVERRIDE:-/opt/ultra-workshop/${HOME_DIR}}"
UWS_HOME=$(getent passwd uws 2>/dev/null | cut -d: -f6 || echo "/home/uws")
cd "$UWS_HOME" 2>/dev/null || cd /tmp

# Hermes terminal-tool default cmd timeout is 180s. Coder runs aider which
# can take several minutes; bump to 900s (15 min) so legitimate long runs
# don't get killed mid-stream. Override per-call with TERMINAL_TIMEOUT.
SPECIALIST_TERMINAL_TIMEOUT="${TERMINAL_TIMEOUT:-900}"

UWS_UID=$(id -u uws 2>/dev/null || echo "")
if [ -n "$UWS_UID" ] && [ "$(id -u)" = "$UWS_UID" ]; then
  exec env HERMES_HOME="$SPECIALIST_HOME" \
    TERMINAL_TIMEOUT="$SPECIALIST_TERMINAL_TIMEOUT" \
    "$HERMES_BIN" chat --skills "$SKILL" --query "$QUERY" -Q --max-turns "$MAX_TURNS" --yolo
else
  exec sudo -u uws env HERMES_HOME="$SPECIALIST_HOME" \
    TERMINAL_TIMEOUT="$SPECIALIST_TERMINAL_TIMEOUT" \
    "$HERMES_BIN" chat --skills "$SKILL" --query "$QUERY" -Q --max-turns "$MAX_TURNS" --yolo
fi
