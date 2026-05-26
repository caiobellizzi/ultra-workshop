# Roadmap: ultra-workshop

## Overview

Bootstrap a Tier 2 autonomous coding agent that runs alongside Brain on the same VPS. Six phases deliver the system in dependency order: vault sync first (everything reads from vault), then deploy infrastructure (Hermes + Telegram live), then skills (the tools the pipeline calls), then the core pipeline itself (build/fix/HITL/ledger), then autonomous routines and Brain↔Workshop integration loops, then owner-approved repo selection for multi-repo builds. Phase 1 is fully linear; LangGraph is reserved for Phase 2 as an opt-in upgrade per L22.

---

## Phases

- [x] **Phase 1: Vault Sync** - Wire vault to GitHub remote so Brain writes are visible to Workshop before any code runs
- [x] **Phase 2: Hermes Deploy** - Install Hermes on VPS with Telegram gateway, systemd service, and MCP registration *(REQ-ws-015 deferred)*
- [x] **Phase 3: Skill Toolkit** - Build and smoke-test all skills the pipeline needs: audit, Tier-1 ports, brain-bridge, Aider (completed 2026-05-21)
- [x] **Phase 4: Build/Fix Pipeline** - Implement 5-role specialist pipeline with HITL, ledgers, cost circuit breaker, and PR output (completed 2026-05-23)
- [ ] **Phase 5: Autonomous Routines & Integration Loops** - Ship 3 cron routines plus Brain↔Workshop vault signaling flows
- [x] **Phase 6: Repo Selection & Multi-Repo Builds** - Add a Brain-backed repo registry so Telegram builds and fixes can target active repos beyond the sandbox (VPS dry-run verified 2026-05-24; live Telegram acceptance pending)
- [ ] **Phase 7: Agentic Repo-Aware Planner** - Replace the blind keyword-heuristic planner with an LLM planner that reads a pre-cloned repo and resolved reference docs (prd.md), keeping the subprocess transport and deterministic state machine (no delegate_task)

---

## Phase Details

### Phase 1: Vault Sync

**Goal**: The vault is a live GitHub-backed shared store that both Brain (VPS) and Obsidian (Mac) read and write without manual intervention
**Depends on**: Nothing (first phase — prerequisite for all others per L27)
**Requirements**: REQ-ws-024, REQ-ws-025, REQ-ws-026, REQ-ws-027
**Success Criteria** (what must be TRUE):

  1. A file written to the vault on the VPS appears in Mac Obsidian within ~5 minutes without manual action
  2. A note saved in Mac Obsidian appears on the VPS vault within ~5 minutes without manual action
  3. `git log` on both sides shows the same commit after a sync cycle
  4. Vault env vars (`VAULT_VPS_PATH`, `VAULT_DEFAULT_BRANCH`, `VAULT_REMOTE`) are present on both VPS and Mac

**Plans**: 2 plans
Plans:

- [ ] 01-01-PLAN.md — GitHub remote, VPS deploy key, VPS cron, env vars on both systems
- [ ] 01-02-PLAN.md — Mac vault remote, Obsidian-Git install+config, end-to-end smoke test

### Phase 2: Hermes Deploy

**Goal**: Hermes Agent is running on the VPS as a systemd service, accepting Telegram commands from the allowed chat ID, with all 5 MCP servers registered
**Depends on**: Phase 1
**Requirements**: REQ-ws-001, REQ-ws-002, REQ-ws-013, REQ-ws-014, REQ-ws-015
**Success Criteria** (what must be TRUE):

  1. `systemctl status uws-hermes` returns `active (running)` and the service starts after Brain (`After=uab-brain.service`)
  2. Telegram `/start` command from chat ID `7113965359` gets a reply within 5 seconds
  3. `systemctl status uab-telegram` returns `inactive (dead)` — no dual-gateway
  4. `hermes mcp list` shows all 5 servers: `github`, `context7`, `crawl4ai`, `hostinger-api`, `google-workspace`
  5. `systemctl restart uws-hermes` mid-flow preserves a pending HITL approval in Hermes FTS5; tapping Approve completes the flow

**Plans**: 5 plans
Plans:

- [x] 02-01-PLAN.md — Wave 0: pre-deploy gates (swap, uab-telegram mask, Node.js 24, LiteLLM 30s)
- [x] 02-02-PLAN.md — Wave 1: uws user + dirs + Hermes install + systemd unit + base config
- [x] 02-03-PLAN.md — Wave 2: Telegram gateway wiring + chat-ID gate (REQ-ws-002, REQ-ws-013)
- [x] 02-04-PLAN.md — Wave 2: 5 MCP registrations — DEFERRED (prerequisites not in place)
- [x] 02-05-PLAN.md — Wave 3: HITL restart-resilience (startup-skill + bats V14 smoke + Approve flow)

### Phase 3: Skill Toolkit

**Goal**: All skills the pipeline depends on exist, have correct Hermes frontmatter, and pass smoke tests — including the skill audit toolchain itself
**Depends on**: Phase 2
**Requirements**: REQ-ws-003, REQ-ws-004, REQ-ws-005, REQ-ws-006
**Success Criteria** (what must be TRUE):

  1. `scripts/audit-claude-skills.py --dry-run` produces `skill-audit.json` tagging all `~/.claude/skills/` entries without touching production Hermes skills
  2. `scripts/audit-claude-skills.py --apply` writes translated skills to `~/.hermes/skills/translated/` with `TRANSLATION_NOTES.md` per skill
  3. ~10 agent-agnostic skills are live in `~/.hermes/skills/` and each passes `hermes skill run <name> --dry-run`
  4. `hermes skill run brain-query --question "what is PARA"` returns HTTP 200 + run_id *(V4 relaxation: Brain Groq structured-output conflict defers citation-grounded answer to manual-only)*
  5. `hermes skill run aider --task "echo to file"` returns a diff; Brain curator endpoint is reachable (HTTP 200 + run_id) *(OPTION B: 2-LLM-call ledger entry deferred to future plan)*

**Plans**: 5 plans
Plans:
**Wave 1**

- [x] 03-01-PLAN.md — Wave 0: hermes-skill-run.sh wrapper + bats helpers + pytest frontmatter validator
- [x] 03-02-PLAN.md — Wave 1: audit-claude-skills.py script (REQ-ws-003)
- [x] 03-03-PLAN.md — Wave 1: ~10 Tier 1 skill ports (REQ-ws-004)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 03-04-PLAN.md — Wave 2: brain_http.py + 3 brain-bridge skills (REQ-ws-005)
- [x] 03-05-PLAN.md — Wave 2: aider skill + LiteLLM precheck + SKIP logic (REQ-ws-006)

### Phase 4: Build/Fix Pipeline

**Goal**: A user can type `/build <task>` or `/fix <issue-url>` in Telegram, approve a HITL prompt, and receive a pull request URL — with a full audit trail in the task ledger and cost posted to Brain's ledger
**Depends on**: Phase 3
**Requirements**: REQ-ws-028, REQ-ws-007, REQ-ws-008, REQ-ws-009, REQ-ws-010, REQ-ws-011, REQ-ws-012
**Success Criteria** (what must be TRUE):

  1. Phase 4 baseline: `/build <task>` runs the full triage → planner → coder → reviewer → pr_opener pipeline and produces a PR on `caiobellizzi/test-workshop-sandbox` within ~5 minutes; Phase 6 supersedes targeting semantics with `/build --repo <repo> <task>`
  2. Flow pauses at pr_opener with Telegram inline buttons; [Approve] pushes and opens PR; [Reject] aborts without touching any remote
  3. `~/.ultra-workshop/tasks/<id>/task_ledger.md` and `progress_log.jsonl` both exist after every completed build
  4. An ADR appears at `vault/_system/workshop-adrs/<task-id>.md` with correct frontmatter after PR creation
  5. At $20/day spend the system refuses new LLM calls with "budget exhausted"; at $18 cron routines self-cancel with a single Telegram warning

**Plans**: 8 plans
Plans:

- [x] 04-00-PLAN.md — Wave 0 prerequisites: GITHUB_PAT, gh CLI, test-workshop-sandbox repo
- [x] 04-01-PLAN.md — workshop/ Python package: types, subprocess orchestrator, ledger, cost
- [x] 04-02-PLAN.md — Five specialist SKILL.md files + workshop_push.py
- [x] 04-03-PLAN.md — Entry-point scripts, SKILL.md wrappers, VPS deploy, smoke tests
- [x] 04-04-PLAN.md — Specialist model matrix: NIM upgrade for planner/reviewer/architect (imported 2026-05-22)
- [x] 04-05-PLAN.md — Async /build & /fix via background terminal (lift 600s cap)
- [x] 04-06-PLAN.md — Make coder-specialist envelope deterministic (gap closure)
- [x] 04-07-PLAN.md — HITL-first ambiguity handling for workshop agents

**UI hint**: yes

### Phase 5: Autonomous Routines & Integration Loops

**Goal**: Three cron routines run unsupervised on their schedules, Brain→Workshop vault signaling dispatches correctly, and the full V1–V24 verification matrix passes
**Depends on**: Phase 4
**Requirements**: REQ-ws-016, REQ-ws-017, REQ-ws-018, REQ-ws-019, REQ-ws-020, REQ-ws-021, REQ-ws-022, REQ-ws-023
**Success Criteria** (what must be TRUE):

  1. `daily-research` runs at 07:00, pulls from `vault/_system/research-queue.md`, posts synthesis to `vault/Inbox/`, and notifies Telegram
  2. `nightly-tests` at 02:00 writes results to vault with `workshop.suggested_action: fix-test-failure` (not auto-dispatched); results appear in Brain's daily-digest
  3. `bug-scan` fast-poll (30s) picks up a `.workshop-queue.jsonl` entry and dispatches only when both `workshop.action:` and `workshop.confirmed: true` are present; HITL prompts are deferred between 22:00–07:00
  4. Brain's daily-digest `post-to-telegram` action appears in Telegram within 30 seconds of Brain writing to `.workshop-queue.jsonl`
  5. `readlink /opt/ultra-workshop/workshop/trust_shared.py` returns the Brain trust module path; `trust_shared.classify_action('git push')` returns the expected risk tier
  6. `vault/_system/integration-contract.md` exists and matches the frontmatter vocabulary spec

**Plans**: TBD
Plans:

- [ ] Phase 5 plans not generated yet

### Phase 6: Repo Selection & Multi-Repo Builds

**Goal**: Telegram can create, register, list, disable, and target active repos through a Brain-backed registry while preserving HITL before repo mutations, pushes, and PR creation
**Depends on**: Phase 4
**Requirements**: REQ-ws-029
**Success Criteria** (what must be TRUE):

  1. `/repo list` auto-seeds and displays `caiobellizzi/test-workshop-sandbox` when the registry is missing
  2. `/repo add`, `/repo create`, and `/repo remove` validate permissions and require Telegram approval before mutating registry or GitHub state
  3. `/build --repo <repo> <task>` validates an active registry repo before launching the background pipeline and opens the PR against that repo's default branch
  4. `/fix <issue-url>` derives the repo from the GitHub issue URL and rejects unknown or inactive repos with a `/repo add` hint
  5. Final PR approval shows repo, base branch, feature branch, changed files, and diff summary

**Plans**: 1 plan
Plans:

- [x] 06-01-PLAN.md — Telegram repo registry and repo-targeted builds

---

### Phase 7: Agentic Repo-Aware Planner

**Goal**: The planner produces repo-grounded implementation plans — it reads a pre-cloned workspace and any referenced design doc (resolved from the target repo, the second-brain vault, or Brain) so that `Plan.affected_files` reflect real paths instead of keyword guesses. Built entirely on the existing subprocess + per-specialist `HERMES_HOME` transport and the deterministic state machine; **no `delegate_task`** (consistent with the Phase 4 Wave 0 "delegate_task NOT_SUPPORTED" finding).
**Depends on**: Phase 4 (pipeline + state machine), Phase 6 (repo registry + repo-aware clone)
**Requirements**: TBD (new REQ ids assigned during planning)
**Success Criteria** (what must be TRUE):

  1. The repo is cloned **before** the planner stage and a single `workspace_dir` is shared by planner (read), coder (write), and reviewer (verify), persisted in `state.json` and resumable after a restart
  2. `planner-specialist` runs as an LLM on the `orchestrator` model (L25) via `hermes chat`, with read-only repo tools (`read_file`/`list_files`/`grep_files`) scoped to `workspace_dir`; write/web/code-exec stay forbidden
  3. `/build --repo <repo> "<task referencing prd.md>"` resolves the referenced doc deterministically — repo-first, second-brain vault-grep second, Brain HTTP semantic third (degraded while Brain's Groq issue is open) — and injects its content into the planner context
  4. For a task whose true target files differ from keyword guesses, the planner's `affected_files` match the files the coder actually changes, and the reviewer raises zero "changed files outside the plan" false-blocks
  5. Subprocess + `HERMES_HOME` isolation, `state.json` resumability, and `exit(2)` HITL are unchanged; no `delegate_task` is introduced; reviewer deterministic safety gates (`_path_issue`, secret regex, `py_compile`) remain authoritative
  6. Phase-4 and Phase-6 bats + pytest suites stay green; the planner stage timeout accommodates repo I/O without regressing pipeline latency

**Plans**: 5 plans
**Requirements**: REQ-ws-030, REQ-ws-031, REQ-ws-032, REQ-ws-033, REQ-ws-034
Plans:

**Wave 1**

- [ ] 07-01-PLAN.md — Wave 0: test scaffold + VPS Hermes tool verification checkpoint
- [ ] 07-02-PLAN.md — Wave 1: workspace_dir in state.py, stage_policy timeout 480s, doc_resolver.py

**Wave 2** *(blocked on Wave 1 completion)*

- [ ] 07-03-PLAN.md — Wave 2: hermes-skill-run.sh routing change + planner SKILL.md LLM rewrite

**Wave 3** *(blocked on Wave 2 completion)*

- [ ] 07-04-PLAN.md — Wave 3: clone-before-planner in workshop_build.py + planner_query update

**Wave 4** *(blocked on Wave 3 completion)*

- [ ] 07-05-PLAN.md — Wave 3: phase gate — activate all tests, full regression suite green

---

## Progress

**Execution Order:** 1 → 2 → 3 → 4 → 5 → 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Vault Sync | 2/2 | ✓ Complete | 2026-05-20 |
| 2. Hermes Deploy | 5/5 | ✓ Complete (REQ-ws-015 deferred) | 2026-05-21 |
| 3. Skill Toolkit | 5/5 | Complete   | 2026-05-21 |
| 4. Build/Fix Pipeline | 8/8 | Complete | 2026-05-25 |
| 5. Autonomous Routines & Integration Loops | 0/TBD | Not started | - |
| 6. Repo Selection & Multi-Repo Builds | 1/1 | VPS dry-run verified (live acceptance pending) | 2026-05-24 |
| 7. Agentic Repo-Aware Planner | 0/TBD | Not started | - |

---

## Phase 2 Reservation (LangGraph)

Per L22 (LOCKED): LangGraph StateGraph, conditional edges, and SqliteSaver are NOT in Phase 1. If oscillation or complex branching failure modes emerge after 10+ clean runs, Phase 2 will evaluate `langgraph>=0.2,<0.3` as an opt-in upgrade to the coordination layer.
