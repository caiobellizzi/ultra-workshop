# Dashboard Redesign — Design Spec
**Date:** 2026-05-31  
**Direction:** Terminal Forge  
**Status:** Approved (brainstorming session)

## Overview

Full UI/UX redesign of the ultra-workshop dashboard — a React 18 + Vite + TypeScript SPA
orchestrating an AI build pipeline. Scope: visual identity + UX/IA restructuring across all 13 pages,
plus 3 UX-blocking bug fixes.

**Audience:** solo developer power user; comfortable with dense UIs; works in terminal + browser side-by-side.  
**Aesthetic:** ops room built by engineers who live in the terminal. Hard edges, monospace-first, zero decoration.

---

## Color System

All tokens as CSS custom properties in `:root` and `.dark`.

### Background layers
| Token | Value | Use |
|---|---|---|
| `--background` | `#0a0a0f` | Page bg — near void |
| `--surface` | `#0f0f17` | Cards, sidebar, panels |
| `--surface-raised` | `#141420` | Dropdowns, popovers |
| `--border` | `#1e1e2e` | All dividers |
| `--border-strong` | `#2e2e45` | Focused/hovered borders |

### Text
| Token | Value | Use |
|---|---|---|
| `--text` | `#e5e7eb` | Primary text |
| `--text-muted` | `#6b7280` | Secondary, metadata |
| `--text-dim` | `#4b5563` | Labels, inactive timestamps |

### Amber — primary accent
| Token | Value | Use |
|---|---|---|
| `--accent` | `#f59e0b` | Active nav, primary CTA, running badge |
| `--accent-bg` | `#1a1000` | Badge background |
| `--accent-border` | `#78350f` | Badge border |
| `--accent-dim` | `#92400e` | Hover states |

### Green — success
| Token | Value | Use |
|---|---|---|
| `--success` | `#22c55e` | pushed, build passed, ✓ icons |
| `--success-bg` | `#052e16` | Badge background |
| `--success-border` | `#14532d` | Badge border |

### Red — danger/error
| Token | Value | Use |
|---|---|---|
| `--danger` | `#ef4444` | failed, critical findings, reject |
| `--danger-bg` | `#1c0a0a` | Badge background |
| `--danger-border` | `#7f1d1d` | Badge border |

### Yellow — warning/HITL
| Token | Value | Use |
|---|---|---|
| `--warning` | `#fbbf24` | needs_approval, needs_clarification, HITL |
| `--warning-bg` | `#1a1000` | Badge background |
| `--warning-border` | `#92400e` | Badge border |

### Blue — info
| Token | Value | Use |
|---|---|---|
| `--info` | `#60a5fa` | Reviewer waves, info states |
| `--info-bg` | `#0c1a30` | Badge background |
| `--info-border` | `#1e3a5f` | Badge border |

### Pipeline stage colors
| Token | Value | Use |
|---|---|---|
| `--stage-pending` | `#4b5563` | Pending stage dot |
| `--stage-running` | `#f59e0b` | Active stage dot (pulsing) |
| `--stage-success` | `#22c55e` | Completed stage dot |
| `--stage-paused` | `#fbbf24` | HITL-paused stage dot |
| `--stage-failed` | `#ef4444` | Failed stage dot |

### Log stream
| Token | Value | Use |
|---|---|---|
| `--log-timestamp` | `#f59e0b` | Timestamps in log lines |
| `--log-source` | `#9ca3af` | Source label (aider/llm) |
| `--log-text` | `#d1d5db` | Log line body text |
| `--log-bg` | `#050508` | Log panel background |

---

## Typography

```css
--font-mono: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace;
--font-sans: 'Inter', system-ui, sans-serif;  /* HITL prose only */

--text-xs:    10px;
--text-sm:    12px;
--text-base:  13px;
--text-md:    14px;
--text-lg:    16px;
--text-xl:    20px;  /* cost/health chart numbers */

--font-normal:  400;
--font-medium:  500;
--font-bold:    700;

--tracking-wide:   0.08em;   /* ALL-CAPS labels */
--tracking-tight: -0.01em;   /* large numerals */
```

**Default:** `--font-mono` everywhere.  
**Exception:** `--font-sans` for long-form prose in HITL clarification cards only.

---

## Depth Strategy

**Borders only — zero box-shadows anywhere.**

- Cards: `1px solid var(--border)`, `border-left: 2px solid <status-color>`
- Active/focused: `1px solid var(--border-strong)`
- Log panel: `1px solid var(--border)` (distinct `--log-bg` makes it read as inset)
- No elevation, no blur, no gradients, no shadows

**Border-radius:**
- `--radius-sm: 2px` — cards, badges, inputs, buttons
- `--radius-md: 4px` — modals, popovers

---

## Layout

### Sidebar (160px, fixed)
- Background: `--surface`; right edge: `1px solid var(--border)`
- Brand: `◆ WORKSHOP` in `--accent`, `--font-bold`, `--tracking-wide`
- Nav links: `--font-mono`, `--text-base`, full-width, 36px tall
  - Active: `background: --accent-bg`, `border-left: 2px solid --accent`, text `--accent`
  - Idle: text `--text-muted`, no background
- Config section: `"CONFIG"` divider in `--text-dim`, `--text-xs`, `--tracking-wide`; then Models / Reviewers / Policies indented 12px (fixes nav discoverability bug)
- No icons — text + ASCII prefix characters only (`▶` active, `○` idle)
- Theme toggle at bottom: `◑ dark / light` text button

### Main content
- Padding: 24px
- Page top bar: title (`--text-lg`) + right-aligned CTA + live status dot
- 8px base unit grid

### Board columns
- Horizontal scroll container
- Each column: 200px wide, label `--text-xs --tracking-wide`
- Task cards: 180px wide, `border-left: 2px solid <status-color>`, `--radius-sm`
- Column header: count badge in `--text-dim`
- Empty column: dashed `--border`, `"--empty--"` in `--text-dim` centered

---

## Component Patterns

### Status badges
`--radius-sm`, `--text-xs`, monospace, `1px` border

| Status | Text color | Bg | Border | Prefix |
|---|---|---|---|---|
| `running` | `--accent` | `--accent-bg` | `--accent-border` | `●` |
| `needs_approval` | `--warning` | `--warning-bg` | `--warning-border` | `⌛` |
| `needs_clarification` | `--warning` | `--warning-bg` | `--warning-border` | `⌛` |
| `needs_step_recovery` | `--warning` | `--warning-bg` | `--warning-border` | `⌛` |
| `needs_review_recovery` | `--warning` | `--warning-bg` | `--warning-border` | `⌛` |
| `needs_timeout_recovery` | `--warning` | `--warning-bg` | `--warning-border` | `⌛` |
| `stopped` | `--text-muted` | `--surface-raised` | `--border` | — |
| `approval_rejected` | `--danger` | `--danger-bg` | `--danger-border` | `✗` |
| `pushing` | `--accent` | `--accent-bg` | `--accent-border` | `↑` |
| `pushed` | `--success` | `--success-bg` | `--success-border` | `✓` |
| `push_failed` | `--danger` | `--danger-bg` | `--danger-border` | `✗` |

### Task cards (Kanban)
- Container: `--surface`, `1px var(--border)`, `border-left: 2px solid <status-color>`, `--radius-sm`
- Goal text: `--text`, `--text-base`, 2 lines max then truncate
- Meta row: `--text-dim`, `--text-xs` — `"repo · cost · time-ago"`
- Status badge inline below meta
- Hover: `border-color → --border-strong`

### Pipeline stage progress (TaskDetail left panel)
- 7 dots vertical list, 8px circle each
- States: pending/running(pulsing)/success/paused/failed
- Active stage label: `--accent`, `--font-medium`
- Connecting line: `1px var(--border)` vertical

### Log stream
- Background: `--log-bg`; border: `1px var(--border)`; `--radius-sm`
- Height: `h-full` with `min-h-48` (fixes current `h-64` hardcode bug)
- Line format: `TIMESTAMP  SOURCE   body` fixed-width columns
- Virtualized scroll (TanStack Virtual — keep existing)

### HITL cards
- Container: `--surface`, `1px var(--warning-border)`, `border-top: 2px solid var(--warning)`, `--radius-sm`
- Header: `"⌛ ACTION REQUIRED"` — `--warning`, `--text-xs`, `--tracking-wide`
- Goal/reason prose: `--font-sans`, `--text-sm`
- Steps/questions: numbered list, `--font-mono`, `--text-sm`
- Option buttons: `1px var(--border)`, `--text-sm`, `--font-mono`
  - Selected: `--accent-bg`, `border: --accent`, text `--accent`
  - Hover: `border: --border-strong`
- Primary action: `--accent` background, `--background` text, `--font-bold`
- Reject/destructive: AlertDialog-wrapped

### Destructive confirmations (AlertDialog)
- Trigger: `1px var(--danger-border)`, `--danger` text
- Modal: `--surface-raised`, `--border`, `--radius-md`
- Body: `--font-sans` prose
- Confirm: `--danger` background; Cancel: `--border` button

---

## Light Mode Tokens

Terminal Forge light mode: paper-white background, dark text, amber accent unchanged. Same hard-edge / border-only depth — no shadows added in light mode either.

| Token | Dark | Light |
|---|---|---|
| `--background` | `#0a0a0f` | `#fafaf8` |
| `--surface` | `#0f0f17` | `#f4f3f0` |
| `--surface-raised` | `#141420` | `#eeede9` |
| `--border` | `#1e1e2e` | `#d4d2cc` |
| `--border-strong` | `#2e2e45` | `#b8b5ae` |
| `--text` | `#e5e7eb` | `#1a1a14` |
| `--text-muted` | `#6b7280` | `#6b6b5e` |
| `--text-dim` | `#4b5563` | `#9e9b92` |
| `--accent` | `#f59e0b` | `#b45309` (darkened for contrast on light) |
| `--accent-bg` | `#1a1000` | `#fef3c7` |
| `--accent-border` | `#78350f` | `#d97706` |
| `--log-bg` | `#050508` | `#1a1a14` (log panel stays dark in light mode — intentional) |
| `--log-timestamp` | `#f59e0b` | `#f59e0b` (same — log panel is always dark) |
| `--log-text` | `#d1d5db` | `#d1d5db` (same) |
| All status colors | unchanged | unchanged (semantic colors stay the same) |

**Default:** dark mode. Toggle wired to `localStorage` + `prefers-color-scheme`.

---

## Bug Fixes In Scope

1. **SSE named-event mismatch** (`src/lib/useSSE.ts`): add `addEventListener` for named events `["log","state","progress"]` alongside existing `onmessage`
2. **Config nav discoverability** (`src/components/layout/Sidebar.tsx`): expand single "Config" link into always-visible sub-nav (Models / Reviewers / Policies)
3. **ModelsConfigPage render side-effect** (`src/pages/ModelsConfigPage.tsx`): move `setRouting(initial)` into `useEffect` guarded by `initializedRef`

---

## Out of Scope

API contracts, routing, auth, TypeScript types, TanStack Query keys, SSE URLs, backend changes. Read-only config pages stay read-only.

---

## Implementation Order

1. **Layer 1 (sequential):** Token foundation (`index.css`) + bug fixes + new primitives (`textarea`, `checkbox`, `alert-dialog`) + `ThemeProvider`/`ThemeToggle`
2. **Layers 2–4 (parallel after L1):** Layout shell → shared components → HITL components
3. **Layer 5 (parallel after 2–4):** All 13 pages, one subagent each

Verification: `pnpm typecheck && pnpm build`, Playwright screenshot matrix (all 13 routes, light + dark), theme toggle assertion, SSE named-event test.
