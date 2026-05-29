<!-- generated-by: gsd-doc-writer -->
# Dashboard Deploy Runbook

Human-executed steps. All commands run as `root` (or `sudo`) on the VPS unless noted.
This file covers the one-time deployment of the Workshop Dashboard.

---

## Pre-checks (run before any step)

```bash
# 1. Confirm uws service is running and healthy
systemctl status uws-hermes.service

# 2. Confirm no build is in flight
ls /home/uws/.ultra-workshop/tasks/*/state.json 2>/dev/null \
  | xargs -I{} sh -c 'python3 -c "import json,sys; s=json.load(open(\"$1\")); print(\"$1\",s.get(\"status\"))" _ {}' \
  | grep -E "running|needs_"

# 3. Verify /etc/uws/env has all required keys
grep -E "NVIDIA_API_KEY|ANTHROPIC_API_KEY|GROQ_API_KEY|LITELLM_MASTER_KEY|LM_STUDIO_API" /etc/uws/env

# 4. Confirm Docker is available
docker info --format '{{.ServerVersion}}'
```

---

## Step 1 — Fix skills drift (SAFE per-skill symlinks)

> ⚠️ **DO NOT `rm -rf /home/uws/.hermes/skills`.** Verified on 2026-05-29: `~/.hermes/skills` is
> Hermes's GLOBAL skills home (51 entries) — the 33 Workshop skills PLUS ~28 non-Workshop skills
> (apple, creative, devops, github, mcp, research, red-teaming, …) and curator state
> (`.hub`, `.bundled_manifest`, `.curator_state`, `.usage.json`). A blanket `rm -rf` destroys all of those.

Verified drift state (2026-05-29):
- 23 Workshop skills are REAL-DIR copies in `~/.hermes` → drift-prone (edits to `/opt` don't propagate).
- 10 Workshop skills are MISSING from `~/.hermes` entirely: `brainstorm-specialist`, `correctness-reviewer`,
  `security-reviewer`, `python-reviewer`, `typescript-reviewer`, `reactjs-reviewer`, `qa-reviewer`,
  `docs-reviewer`, `config-reviewer`, `merge-agent` → these likely fail to load / fail-open in the review wave today.

Fix = replace ONLY the 33 Workshop entries with per-skill symlinks → the `/opt` canonical copy. Preserves the
28 non-Workshop skills + curator state, fixes the 23 drifted copies, and ADDS the 10 missing skills.

```bash
# Dry-run: show what will change
for s in $(ls /opt/ultra-workshop/skills); do
  t="/home/uws/.hermes/skills/$s"
  if [ -L "$t" ]; then echo "skip (already symlink): $s"
  elif [ -e "$t" ]; then echo "replace copy:        $s"
  else echo "add (was missing):   $s"; fi
done

# Apply: back up any drifted real copies, then symlink each Workshop skill
ts=$(date +%Y%m%d-%H%M%S); bk="/home/uws/.hermes/skills-backup-$ts"; mkdir -p "$bk"
for s in $(ls /opt/ultra-workshop/skills); do
  t="/home/uws/.hermes/skills/$s"
  [ -L "$t" ] && continue              # already a symlink — leave it
  [ -e "$t" ] && mv "$t" "$bk/$s"      # back up drifted real copy
  ln -s "/opt/ultra-workshop/skills/$s" "$t"
done
chown -h -R uws:uws /home/uws/.hermes/skills

# Verify: every Workshop skill is now a symlink; non-Workshop skills untouched
for s in $(ls /opt/ultra-workshop/skills); do printf '%-24s -> ' "$s"; readlink "/home/uws/.hermes/skills/$s" || echo "NOT A SYMLINK"; done
ls /home/uws/.hermes/skills | wc -l   # expect >= 51 (unchanged count + the 10 added)
```

> ⚠️ **Behavior change:** symlinking the 10 currently-missing reviewer/brainstorm/merge skills makes them
> loadable by Hermes for the first time. The diff-gated review wave may begin actually running those
> reviewers (it may have been failing-open until now), which can raise per-build cost. Confirm this is intended.

---

## Step 2 — Bring up dedicated LiteLLM proxy on :4001

```bash
# Start the container (from repo root on the VPS)
cd /opt/ultra-workshop
docker compose -f deploy/litellm/docker-compose.workshop.yml up -d

# Confirm it is reachable
curl -s http://127.0.0.1:4001/health | python3 -m json.tool

# Repoint Hermes config to :4001
# Edit /opt/ultra-workshop/hermes-config/config.yaml:
#   base_url: http://127.0.0.1:4001
# Then restart Hermes to pick up the change (done in Step 3 via daemon-reload).

# If aider is called with --openai-api-base / --user flags, update those too.
# They are typically set in /etc/uws/env or hermes-config/config.yaml.
```

---

## Step 3 — Install systemd unit + sudoers; start dashboard service

```bash
# Install the sudoers drop-in
cp /opt/ultra-workshop/deploy/sudoers.d/uws-dashboard /etc/sudoers.d/uws-dashboard
chmod 440 /etc/sudoers.d/uws-dashboard
visudo -c   # validate — must print "parsed OK"

# Install the systemd unit
cp /opt/ultra-workshop/deploy/systemd/uws-hermes-dashboard.service \
   /etc/systemd/system/uws-hermes-dashboard.service

# Reload systemd and start both services
systemctl daemon-reload
systemctl restart uws-hermes.service          # picks up :4001 base_url edit
systemctl enable --now uws-hermes-dashboard.service

# Confirm both services are active
systemctl status uws-hermes.service uws-hermes-dashboard.service

# Tail dashboard logs
journalctl -u uws-hermes-dashboard.service -f
```

---

## Step 4 — Build frontend, deploy static files, verify

Run on your LOCAL machine (or a CI job that has Node + pnpm):

```bash
cd dashboard/frontend
pnpm install
pnpm run build   # produces dashboard/frontend/dist/

# rsync dist to VPS (adjust SSH target as needed)
rsync -av --delete dashboard/frontend/dist/ \
  uws@srv1381850.hstgr.cloud:/opt/ultra-workshop/dashboard/frontend/dist/
```

Back on the VPS:

```bash
# Confirm dist is present
ls /opt/ultra-workshop/dashboard/frontend/dist/index.html

# Restart dashboard so StaticFiles mount picks up the new build
systemctl restart uws-hermes-dashboard.service
```

### Tailscale reachability check

```bash
# From your laptop (on Tailscale)
curl -s http://<tailscale-ip>:7010/api/health | python3 -m json.tool
# Expected: {"ok": true, "services": [...], "queue_depth": 0, "disk_free_gb": 0.0}
```

### Cookie-auth check

```bash
# POST to obtain a session cookie (use value of UWS_DASH_LOGIN_PASSWORD from /etc/uws/env)
curl -c /tmp/dash-cookies.txt -X POST http://<tailscale-ip>:7010/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"password": "<UWS_DASH_LOGIN_PASSWORD>"}'

# Use cookie to hit a protected endpoint
curl -b /tmp/dash-cookies.txt http://<tailscale-ip>:7010/api/tasks | python3 -m json.tool
```

---

## Verification checklist

- [ ] `systemctl is-active uws-hermes.service` → `active`
- [ ] `systemctl is-active uws-hermes-dashboard.service` → `active`
- [ ] `curl -s http://127.0.0.1:7010/api/health` returns JSON with `"ok": true`
- [ ] `curl -s http://127.0.0.1:4001/health` returns 200 (LiteLLM proxy)
- [ ] Dashboard UI loads at `http://<tailscale-ip>:7010/` (redirects to `/board`)
- [ ] `/board` shows task list (may be empty if no tasks ran yet)
- [ ] `/health` page shows all model aliases reachable (green indicators)
- [ ] HITL queue at `/hitl` shows any pending items from `pending_hitl.db`
- [ ] `visudo -c` passes with no errors
- [ ] `ls -la /home/uws/.hermes/skills` is a symlink → `/opt/ultra-workshop/skills`
- [ ] `journalctl -u uws-hermes-dashboard.service --since "1 min ago"` has no ERROR lines
- [ ] `docker ps --filter name=uws-litellm` shows container `Up`
- [ ] A test build triggered via `/launch` creates a task and appears on `/board`
