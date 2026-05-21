# Plan 02-04: MCP Server Registration — DEFERRED

**Status:** Deferred by user decision
**Date:** 2026-05-21
**Decision:** All 5 MCP servers (github, crawl4ai, hostinger-api, google-workspace, context7) will NOT be registered in Phase 2.

## Rationale

Pre-deploy gates revealed significant manual setup overhead for no immediate benefit:
- GCP service account + domain-wide delegation for google-workspace
- GITHUB_PAT, HOSTINGER_API_TOKEN credentials not yet provisioned
- Crawl4AI not running on VPS
- workspace-mcp legitimacy review needed

MCP wiring will be addressed in a dedicated future phase when all prerequisites are in place.

## hermes-config/config.yaml state

`mcp_servers: {}` — empty stub remains. No changes committed.

## Forward reference

When MCPs are re-enabled, blockers to resolve first:
1. GITHUB_PAT (fine-grained, scoped to test-workshop-sandbox)
2. HOSTINGER_API_TOKEN (from hpanel.hostinger.com → Profile → API)
3. GCP service account JSON at /etc/uws/gcp-service-account.json with domain-wide delegation
4. Crawl4AI Docker on VPS at localhost:11235
5. GOOGLE_USER_EMAIL=caiobellizzi@gmail.com in /etc/uws/env

## Requirements

REQ-ws-015 deferred — not satisfied in Phase 2.
