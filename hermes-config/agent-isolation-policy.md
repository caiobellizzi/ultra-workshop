# Agent Isolation Policy

**Version:** 1.0.0
**Phase:** 09-advanced-agent-architecture
**Owner:** ultra-workshop
**Control plane:** `hermes-config/review-roster.yaml` (enforcement), this document (rationale)

---

## Purpose

This policy controls context-window isolation for each agent role in the review wave. Each role is assigned to either **AgentTool** (isolated dispatch) or **SkillTool** (shared-context pass) based on the cost-correctness tradeoff documented in D-04/D-06/D-07.

**Background:** The VILA-Lab finding that AgentTool dispatch costs approximately 7x more than SkillTool is the primary cost lever. Since ultra-workshop's review wave uses NVIDIA NIM via LiteLLM proxy (not Claude tiers, per D-05), the absolute cost multiplier differs, but the isolation benefit remains: a fresh context window per invocation prevents prior pipeline events from biasing judgment-heavy roles.

AgentTool isolation is reserved for roles that make **blocking decisions** (push/no-push, HITL escalation). Shared-context passes are used for all diagnostic, non-blocking roles to minimize NIM token spend.

---

## Policy

### AgentTool (Isolated dispatch — fresh context per invocation)

**Applies to:** `security-reviewer`, `correctness-reviewer`, `merge-agent`

**Rationale:**
These roles make irreversible or blocking decisions. A contaminated context window (from prior pipeline stages, earlier reviewer outputs, or partial diff artifacts) must not bias their judgment. Each invocation receives only the frozen diff artifact and the relevant plan — nothing else.

- `security-reviewer`: determines whether a push is blocked for security reasons. False negatives are high-cost. Fresh context prevents suppression by prior "clean" review outputs.
- `correctness-reviewer`: determines whether all plan steps are addressed and the build/test gate passed. Contaminated context from a prior failure/retry cycle could cause under-reporting.
- `merge-agent`: applies auto-fixes and sets the final `block_push` decision. Operates in its own git worktree (B5). Must not be influenced by the coder's reasoning context.

**Implementation:** Each role is dispatched as a separate Hermes `delegate_task` call. The only context injected is:
1. The frozen diff artifact (read-only, produced by the coder).
2. The task plan (plan steps + affected files).
3. The role's SKILL.md soul (via `--soul` flag).

### SkillTool (Shared-context pass — shared pipeline context)

**Applies to:** `python-reviewer`, `typescript-reviewer`, `reactjs-reviewer`, `qa-reviewer`, `docs-reviewer`, `config-reviewer`

**Rationale:**
These are diagnostic, non-blocking roles. They produce findings that inform the merge-agent but do not individually block the push. Shared context reduces cost and allows cross-file awareness within the same pipeline context window.

**Implementation:** Dispatched as skill invocations within the existing pipeline context. The diff artifact, plan, and prior pipeline state are all available. Reviewer findings are serialized as structured JSON and passed to the merge-agent.

---

## Role Table

| Role | Isolation Type | Budget (USD-cents/month) | Exhaustion Behavior |
|------|---------------|--------------------------|---------------------|
| `security-reviewer` | AgentTool | 4000 (=$40) | BLOCK to HITL — never skip security |
| `correctness-reviewer` | AgentTool | 3000 (=$30) | BLOCK to HITL — always-on, no substitute |
| `merge-agent` | AgentTool | 1500 (=$15) | BLOCK to HITL — merge decision not skippable |
| `python-reviewer` | SkillTool | 2000 (=$20) | Substitute cheap-fast fallback model |
| `typescript-reviewer` | SkillTool | 2000 (=$20) | Substitute cheap-fast fallback model |
| `reactjs-reviewer` | SkillTool | 2000 (=$20) | Substitute cheap-fast fallback model |
| `qa-reviewer` | SkillTool | 1000 (=$10) | Skip and log audit entry |
| `docs-reviewer` | SkillTool | 1000 (=$10) | Skip and log audit entry |
| `config-reviewer` | SkillTool | 1000 (=$10) | Skip and log audit entry |

Default caps from D-12. Tune per-role in `review-roster.yaml` (`budget_cents_monthly` field). All spending tracked in `brain/_system/cost-ledger.md` via `workshop/cost.py` + `hermes-skills/brain_http.py` (D-11).

---

## Enforcement

Enforcement is **mechanical** — the `isolation` field in `review-roster.yaml` drives dispatch behavior in `workshop_build.py`'s wave dispatcher (implemented in Phase 09, plan 09-03).

```
review-roster.yaml (control plane)
  └─ isolation: "agent" | "skill"
       └─ workshop_build.py wave dispatcher
            ├─ "agent" → delegate_task(..., fresh_context=True)
            └─ "skill" → skill_call(..., shared_context=True)
```

This document is the **rationale**. The YAML is the **control plane**. These must stay in sync.

**Rule:** Never modify dispatch logic in `workshop_build.py` without updating both this document AND `review-roster.yaml`. A divergence between the policy document and the YAML is a P1 defect — the YAML governs runtime behavior.

---

## Prohibited Patterns

- **Never skip `security-reviewer`** even if the budget is exhausted. Budget exhaustion for security must escalate to HITL with a `{"reason": "security-reviewer budget exhausted", "action": "BLOCK"}` payload. There is no fallback model for security.
- **Never run any reviewer with write access to the workspace.** All reviewers except `merge-agent` read a frozen diff artifact only (D-06). The diff is produced by the coder, snapshotted, and immutable for the duration of the review wave.
- **Never add a reviewer to the always-on category** (`always_on: true` in `review-roster.yaml`) without owner sign-off recorded in `PROJECT.md` as an owner amendment. Always-on reviewers consume budget on every wave regardless of diff content.
- **Never run `merge-agent` without first completing the full review wave.** The merge agent requires all WaveReport inputs to dedup correctly. Partial wave inputs lead to under-reported findings.
- **Never bypass `block_push: true`** from the merge agent without explicit owner approval at the HITL gate. Automated systems must not override a block decision.

---

## References

- `hermes-config/review-roster.yaml` — per-role isolation, model, budget, always_on, exhaustion_behavior
- `workshop/cost.py` — cost tracking (USD-cents per invocation)
- `hermes-skills/brain_http.py` — brain ingest for per-role ledger writes and Important finding notes
- `hermes-skills/workshop_build.py` — wave dispatcher implementation (09-03)
- `.planning/phases/09-advanced-agent-architecture/09-CONTEXT.md` — decisions D-04 through D-09
