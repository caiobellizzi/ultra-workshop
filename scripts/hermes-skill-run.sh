#!/usr/bin/env bash
# scripts/hermes-skill-run.sh
# Usage: hermes-skill-run.sh <skill-name> [--dry-run] [--key value ...]
# Wraps `hermes chat --skills <name> --query <q> -Q --max-turns <N> --yolo`.
# Some JSON-only specialists may short-circuit to deterministic local scripts.
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

# Per-skill --max-turns budget AND per-skill HERMES_HOME selection. Planner,
# coder, and reviewer are short-circuited to deterministic Python scripts below,
# so their model settings are retained only to keep this routing table exhaustive.
# Triage stays on private-worker (V17 local-token contract). Reviewer uses NIM
# `research-worker`. Override turns with MAX_TURNS, home with
# SPECIALIST_HOME_OVERRIDE.
if [ -z "${MAX_TURNS:-}" ]; then
  case "$SKILL" in
    triage-specialist)   MAX_TURNS=3;  HOME_DIR=specialist-home-private ;;
    requirements-specialist) MAX_TURNS=6; HOME_DIR=specialist-home-orchestrator ;;
    planner-specialist)  MAX_TURNS=8;  HOME_DIR=specialist-home-orchestrator ;;
    reviewer-specialist) MAX_TURNS=10; HOME_DIR=specialist-home-research ;;
    coder-specialist)    MAX_TURNS=15; HOME_DIR=specialist-home-orchestrator ;;
    *)                   MAX_TURNS=8;  HOME_DIR=specialist-home-private ;;
  esac
else
  case "$SKILL" in
    triage-specialist)   HOME_DIR=specialist-home-private ;;
    requirements-specialist) HOME_DIR=specialist-home-orchestrator ;;
    planner-specialist)  HOME_DIR=specialist-home-orchestrator ;;
    reviewer-specialist) HOME_DIR=specialist-home-research ;;
    coder-specialist)    HOME_DIR=specialist-home-orchestrator ;;
    *)                   HOME_DIR=specialist-home-private ;;
  esac
fi

# Dry-run short-circuit: print what would run and exit 0. Includes the resolved
# HERMES_HOME so per-skill model routing can be asserted in bats smoke tests.
if echo "$QUERY" | grep -q -- "--dry-run"; then
  if [ "$SKILL" = "planner-specialist" ]; then
    echo "[dry-run] would run: python3 /opt/ultra-workshop/hermes-skills/workshop_planner.py ${QUERY}"
    echo "[dry-run] planner-specialist is deterministic; no HERMES_HOME"
  elif [ "$SKILL" = "requirements-specialist" ]; then
    echo "[dry-run] would run: python3 /opt/ultra-workshop/hermes-skills/workshop_requirements.py ${QUERY}"
    echo "[dry-run] requirements-specialist is deterministic; no HERMES_HOME"
  elif [ "$SKILL" = "reviewer-specialist" ]; then
    echo "[dry-run] would run: python3 /opt/ultra-workshop/hermes-skills/workshop_reviewer.py ${QUERY}"
    echo "[dry-run] reviewer-specialist is deterministic; no HERMES_HOME"
  elif [ "$SKILL" = "coder-specialist" ]; then
    echo "[dry-run] would run: python3 /opt/ultra-workshop/hermes-skills/workshop_coder.py ${QUERY}"
    echo "[dry-run] coder-specialist is deterministic; no HERMES_HOME"
  else
    echo "[dry-run] would run: hermes chat --skills ${SKILL} --query '${QUERY}' -Q --max-turns ${MAX_TURNS} --yolo"
    echo "[dry-run] HERMES_HOME=/opt/ultra-workshop/${HOME_DIR}"
  fi
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
UWS_UID=$(id -u uws 2>/dev/null || echo "")

if [ "$SKILL" = "requirements-specialist" ] || [ "$SKILL" = "planner-specialist" ] || [ "$SKILL" = "reviewer-specialist" ] || [ "$SKILL" = "coder-specialist" ]; then
  PYTHON_BIN="/opt/ultra-workshop/hermes/venv/bin/python3"
  if [ ! -x "$PYTHON_BIN" ]; then
    PYTHON_BIN="python3"
  fi
  case "$SKILL" in
    requirements-specialist) SCRIPT_PATH="/opt/ultra-workshop/hermes-skills/workshop_requirements.py" ;;
    planner-specialist)  SCRIPT_PATH="/opt/ultra-workshop/hermes-skills/workshop_planner.py" ;;
    reviewer-specialist) SCRIPT_PATH="/opt/ultra-workshop/hermes-skills/workshop_reviewer.py" ;;
    coder-specialist)    SCRIPT_PATH="/opt/ultra-workshop/hermes-skills/workshop_coder.py" ;;
  esac
  if [ -n "$UWS_UID" ] && [ "$(id -u)" = "$UWS_UID" ]; then
    exec "$PYTHON_BIN" "$SCRIPT_PATH" "$@"
  else
    exec sudo -u uws "$PYTHON_BIN" "$SCRIPT_PATH" "$@"
  fi
fi

# Hermes terminal-tool default cmd timeout is 180s. Coder runs aider which
# can take several minutes; bump to 900s (15 min) so legitimate long runs
# don't get killed mid-stream. Override per-call with TERMINAL_TIMEOUT.
SPECIALIST_TERMINAL_TIMEOUT="${TERMINAL_TIMEOUT:-900}"

if [ -n "$UWS_UID" ] && [ "$(id -u)" = "$UWS_UID" ]; then
  exec env HERMES_HOME="$SPECIALIST_HOME" \
    TERMINAL_TIMEOUT="$SPECIALIST_TERMINAL_TIMEOUT" \
    "$HERMES_BIN" chat --skills "$SKILL" --query "$QUERY" -Q --max-turns "$MAX_TURNS" --yolo
else
  exec sudo -u uws env HERMES_HOME="$SPECIALIST_HOME" \
    TERMINAL_TIMEOUT="$SPECIALIST_TERMINAL_TIMEOUT" \
    "$HERMES_BIN" chat --skills "$SKILL" --query "$QUERY" -Q --max-turns "$MAX_TURNS" --yolo
fi
