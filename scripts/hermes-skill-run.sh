#!/usr/bin/env bash
# scripts/hermes-skill-run.sh
# Usage: hermes-skill-run.sh <skill-name> [--dry-run] [--key value ...]
# Wraps `hermes chat --skills <name> --query <q> -Q --max-turns 3 --yolo`.
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

# Dry-run short-circuit: print what would run and exit 0.
if echo "$QUERY" | grep -q -- "--dry-run"; then
  echo "[dry-run] would run: hermes chat --skills ${SKILL} --query '${QUERY}' -Q --max-turns 3 --yolo"
  exit 0
fi

# Production path: exec replaces this process; positional args prevent shell injection.
exec sudo -u uws /opt/ultra-workshop/hermes/venv/bin/hermes chat --skills "$SKILL" --query "$QUERY" -Q --max-turns 3 --yolo
