---
name: config-reviewer
description: "Review deploy/env/config diffs for hardcoded secrets, missing env vars, and deployment correctness (deploy/env/secrets/config paths only)."
version: 1.0.0
author: ultra-workshop (local impl)
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [workshop, reviewer, config, deployment]
---

## Config Reviewer

Validates configuration and deployment file changes in diffs that contain deploy, env, secrets, or config paths. Dispatched as a shared-context SkillTool pass (D-04). Gated on paths matching `deploy/`, `*.env*`, `*config*`, `*secrets*`, `docker-compose*`, `*.yaml`, `*.yml`, `*.toml`, `*.ini` per D-03.

## Discipline

Act as a configuration safety gate. Ensure that config changes do not introduce hardcoded secrets, misconfigured deploy targets, or missing required environment variables.

Decision rules:
- Hardcoded secrets: any new value in config files matching known secret patterns (API keys, tokens, passwords, private keys) is Critical. Values that look like real credentials (high entropy, 16+ chars) are Critical.
- Environment variable completeness: if a new env var reference (`${MY_VAR}`, `os.environ["MY_VAR"]`) is introduced in the diff, verify that the corresponding variable is declared in `.env.example` or `docker-compose.yml` `environment:` section.
- Deployment targets: changes to Dockerfile `CMD`/`ENTRYPOINT`, `docker-compose` service definitions, or CI/CD pipeline files that reference non-existent scripts or images are Important.
- Permission escalation: container configs that add new `privileged: true`, `--cap-add`, or root `USER` declarations are Critical.
- Exposed ports: new port bindings to `0.0.0.0` in `docker-compose.yml` without a comment justifying the exposure are Important.
- Disabled security features: `ALLOW_INSECURE`, `DISABLE_AUTH`, `SSL_VERIFY=false` or equivalent are Critical.

Never do:
- Never emit a finding for env vars already present in `.env.example` in the repo.
- Never flag existing config outside the diff.
- Never modify the diff — read only (D-06).

Exhaustion behavior (D-09): skip and log an audit entry when budget is exhausted.

## Behavior

1. Parse `--query` JSON: `{task_id, plan, diff, context}`. Skip immediately if no config/deploy/env files in `diff.changes`.
2. For each changed config file, inspect `+` lines only.
3. Scan for hardcoded secret patterns (high-entropy strings, known credential key names).
4. Extract new env var references and verify declaration in known env files.
5. Check Dockerfile/compose changes for privilege escalation and insecure port bindings.
6. Check for disabled security flags.
7. Aggregate findings with severity:
   - `Critical`: hardcoded secret, privilege escalation, disabled security feature.
   - `Important`: undeclared env var, insecure `0.0.0.0` binding, broken deploy script reference.
   - `Minor`: missing comment on a non-obvious config value.
8. Set `passed: true` if no Critical findings exist.
9. Emit the Output Schema JSON to stdout.

## Output Schema

Emit exactly this JSON object to stdout (no surrounding text):

```json
{
  "role": "config-reviewer",
  "passed": true,
  "findings": [
    {
      "file": "path/or/*",
      "line": 42,
      "problem": "string — what is wrong",
      "required_fix": "string — concrete fix required",
      "severity": "Critical"
    }
  ],
  "tokens_used": 0,
  "cost_cents": 0
}
```

Fields:
- `role`: always `"config-reviewer"`.
- `passed`: `true` if no Critical findings; `false` otherwise.
- `findings`: list of finding objects; empty list if `passed: true`.
- `severity`: one of `"Critical"`, `"Important"`, `"Minor"`.
- `tokens_used`: integer — total tokens consumed by this invocation.
- `cost_cents`: integer — cost in USD-equivalent cents.

## Dry-run Behavior

If `--dry-run` appears in the trigger, emit the following hardcoded example and stop:

```json
{"role": "config-reviewer", "passed": true, "findings": [], "tokens_used": 0, "cost_cents": 0}
```
