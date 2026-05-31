# Plan: Full UI/UX Redesign — Ultra Workshop Dashboard

## Context

The ultra-workshop dashboard (`dashboard/frontend/`) is a React 18 + Vite + TypeScript SPA
that orchestrates an AI build pipeline — 13 pages, a 9-column Kanban board, a 3-panel
task-detail view, HITL approval cards, cost/health charts, and config matrices. It currently
ships the **stock shadcn/ui blue-navy monochrome** with no custom brand layer, dark-mode tokens
defined but **no toggle wired**, and several real UX defects (Config sub-pages unreachable from
nav, broken SSE silently dropping live logs/state, ad-hoc non-shadcn form controls, no
destructive-action confirmations, fixed-width layouts that break under 1400px).

**Goal:** a full redesign — a distinct visual identity *and* UX/IA restructuring — driven by
skill-generated direction exploration, ending in a shipped React implementation of all 13 pages
plus the UX-blocking bug fixes.

**Locked decisions (from grilling):**
- Scope: **both** visual identity + UX/IA (full redesign)
- Direction: **skills decide** — brainstorm + taste-design generate 2-3 directions
- Mockup format: **throwaway HTML** (compare in browser, zero risk to app)
- Structure: **two rounds** — 3 directions × 3 hero screens → pick one → that winner across all 13 pages + lock `DESIGN.md`
- Functional fixes **in scope**: SSE named-event mismatch, Config nav discoverability, ModelsConfigPage render side-effect
- Definition of done: **through full React implementation + verification**

## Stage 1 — Direction Exploration (brainstorm + taste-design)

1. Run `superpowers:brainstorming` then `taste-design`/`redesign-existing-projects` skills to
   define **3 candidate directions** for a dense, developer-facing ops dashboard (e.g. dark-tech/terminal,
   Linear-minimal, editorial-spacious — final set chosen by the skills).
2. Produce **9 throwaway HTML mockups** in `dashboard/frontend/mockups/round1/`:
   3 directions × 3 hero screens (**Board**, **Task Detail**, **HITL**), using realistic dummy
   data drawn from `src/types/task.ts`. Self-contained HTML+inline CSS, openable directly in a browser.
3. **Checkpoint:** user opens the 9 files, compares, and picks ONE direction.

## Stage 2 — Full Mockups + Design System Lock

4. Mock the **winning direction across all 13 pages** in `dashboard/frontend/mockups/round2/`.
5. Write **`dashboard/frontend/src/DESIGN.md`** — the deterministic design-system contract:
   brand identity, full color-token table (`:root` + `.dark` HSL), typography (`--font-mono`),
   spacing/radius, elevation (`--shadow-card`/`--shadow-raised`), motion tokens, component
   conventions, layout conventions, a **13-page status grid** (loading/empty/error/HITL-aware per page),
   and explicit **non-goals** (no API/routing/auth/type/query-key changes).
6. **Checkpoint:** user approves `DESIGN.md` before any production code.

## Stage 3 — React Implementation (layered, parallelizable)

**Layer 1 — Token foundation + bug fixes** (sequential, first):
- Replace `:root`/`.dark` blocks in `src/index.css` with the new brand palette + new semantic
  tokens (`--sidebar-bg`, `--hitl-alert`, `--stage-running/success/paused`, `--chart-1..6`,
  `--font-mono`, `--shadow-*`, `--motion-*`).
- Add `sidebar.bg` mapping to `tailwind.config.js` `theme.extend.colors` (only change to that file).
- Add `ThemeProvider` context + `ThemeToggle` (localStorage + `prefers-color-scheme`), wired in `src/main.tsx`.
- Add primitives: `src/components/ui/{textarea,checkbox,alert-dialog}.tsx` (Radix deps already installed).
- Fix `src/components/ui/badge.tsx` — replace hardcoded `success`/`warning`/`info` Tailwind color
  literals with semantic-token variants (dark-mode safe).
- **Bug fix A — `src/lib/useSSE.ts`:** add `es.addEventListener` for named events
  (`["log","state","progress"]`, exposed as an optional param defaulting to that set) alongside the
  existing `es.onmessage`. Backward compatible; `useTaskLogStream`/`useTaskEventStream` inherit the fix.
- **Bug fix B — `src/components/layout/Sidebar.tsx`:** convert the single "Config" link into an
  always-expanded sub-nav group exposing Models / Reviewers / Policies (routes already exist; zero router changes).
- **Bug fix C — `src/pages/ModelsConfigPage.tsx`:** move the in-render `setRouting(initial)` into a
  `useEffect` guarded by an `initializedRef` (no eslint suppression needed).

**Layer 2 — Layout shell:** `AppShell.tsx` (place `ThemeToggle`), `Sidebar.tsx` (new skin +
sub-nav + toggle), `PageHeader.tsx` polish.

**Layer 3 — Shared + task components** (parallel with L2):
StatusBadge/CostPill/StageLabel/SeverityBadge re-skin; TaskCard (`bg-blue-500`→`bg-stage-running`);
PipelineGraph status colors; **LogStream `h-64`→`h-full min-h-[12rem]`** + token colors;
DiffViewer + ReviewWaveTable diff/row tint colors → semantic tokens.

**Layer 4 — HITL components:** normalize raw `<button>` option selectors in Step/Review/Timeout
recovery cards to shadcn `Button` + `data-selected` ring; add `DestructiveConfirmButton`
(AlertDialog) and apply to ApprovalCard/BrainstormCard reject + PoliciesConfigPage Hermes-restart +
ReposPage delete; replace bare `<textarea>` in ClarificationCard with `<Textarea>`.

**Layer 5 — Pages** (highly parallel, one subagent each):
- Re-skin-only: Board (column widths + empty states), HITLQueue, Cost (CHART_COLORS → CSS-var refs),
  Health, Skills, Repos.
- Structural: **TaskDetailPage** (responsive 3-panel; HITL right panel → responsive slide-over Sheet),
  LaunchPage (`<Textarea>` + `<Checkbox>`), SkillEditorPage (amber banner → token, Monaco theme bound
  to context), LoginPage (brand card), Models/Reviewers/Policies config polish.

**Parallelization:** Layer 1 sequential; Layers 2–4 fan out after L1; Layer 5 fans out after 2–4
(peak ~5-6 subagents). Each subagent owns distinct files to avoid conflicts.

## Critical Files

- `dashboard/frontend/src/index.css` — token source of truth
- `dashboard/frontend/tailwind.config.js` — single `sidebar.bg` addition
- `dashboard/frontend/src/lib/useSSE.ts` — SSE named-event fix
- `dashboard/frontend/src/components/layout/Sidebar.tsx` — config sub-nav + skin
- `dashboard/frontend/src/pages/ModelsConfigPage.tsx` — render-side-effect fix
- `dashboard/frontend/src/components/ui/badge.tsx` — token-safe variants
- New: `src/components/ui/{textarea,checkbox,alert-dialog}.tsx`, `ThemeProvider`/`ThemeToggle`, `src/DESIGN.md`

## Verification

1. `cd dashboard/frontend && pnpm typecheck && pnpm build` — zero errors (catches import/prop/variant breaks).
2. **Playwright screenshot matrix** — all 13 routes incl. `/config/reviewers` & `/config/policies`
   (proves the nav fix), TaskDetail in both running and HITL states, light **and** dark.
3. **Theme toggle:** click toggle on `/board`, assert `documentElement` gains/loses `.dark`, screenshot each.
4. **SSE fix:** Playwright `page.evaluate()` mocks `EventSource`, dispatches a named `log` event,
   assert the line renders in `LogStream` (or live: open a running task, confirm logs stream without manual reconnect).
5. Final `pnpm build` — bundle size in same ballpark (guards against accidental static Monaco/Recharts imports).

## Out of Scope (non-goals)

API contracts, routing structure, auth flow, TypeScript types, TanStack Query keys, SSE URLs, and
backend changes. Read-only config pages stay read-only (edit controls are a separate task).
