# Ultra Workshop Dashboard — DESIGN.md

**Direction:** Terminal Forge  
**Version:** 1.0.0  
**Date:** 2026-05-31  
**Status:** Production contract — do not deviate without updating this file

---

## 1. Identity

**Direction name:** Terminal Forge  
**Tagline:** Ops room built by engineers who live in the terminal  
**Audience:** Solo developer power user. Comfortable with dense UIs. Works in a terminal and browser side-by-side.

**Aesthetic philosophy:** Terminal Forge treats the browser as an extension of the terminal — not a softened consumer interface laid on top of it. Everything reads as a technical instrument: hard edges, monospace text as the primary typeface, a near-void dark background that recedes behind the content, and an amber accent that reads as the active cursor. Decoration is zero. Every visual element must earn its presence by communicating state or hierarchy. The design is dense by intent — a power user reads 40 task statuses at a glance without scrolling.

**Non-goals:**
- No box-shadows anywhere (not even `box-shadow: 0 1px 2px` — zero tolerance)
- No CSS gradients anywhere (not even subtle background gradients)
- No emojis in code or UI (ASCII prefix characters only: `●`, `◆`, `▶`, `○`, `⌛`, `✓`, `✗`, `↑`, `◑`)
- No fabricated metrics, placeholder data, or lorem ipsum
- No rounded corners beyond `--radius-sm: 2px` and `--radius-md: 4px`
- No Lucide icons in the sidebar navigation (text + ASCII prefix characters only)
- No elevation layers beyond border differentiation

---

## 2. Color Tokens

Copy-paste this block into `src/index.css`, replacing any existing `:root` and `.dark` blocks.

```css
/* ─── Terminal Forge Design System ─────────────────────────────────────── */

:root {
  /* Background layers */
  --background:      #0a0a0f;  /* Page bg — near void */
  --surface:         #0f0f17;  /* Cards, sidebar, panels */
  --surface-raised:  #141420;  /* Dropdowns, popovers */
  --border:          #1e1e2e;  /* All dividers */
  --border-strong:   #2e2e45;  /* Focused/hovered borders */

  /* Text */
  --text:            #e5e7eb;  /* Primary text */
  --text-muted:      #6b7280;  /* Secondary, metadata */
  --text-dim:        #4b5563;  /* Labels, inactive timestamps */

  /* Amber — primary accent */
  --accent:          #f59e0b;  /* Active nav, primary CTA, running badge */
  --accent-bg:       #1a1000;  /* Badge background */
  --accent-border:   #78350f;  /* Badge border */
  --accent-dim:      #92400e;  /* Hover states */

  /* Green — success */
  --success:         #22c55e;  /* pushed, build passed, check icons */
  --success-bg:      #052e16;  /* Badge background */
  --success-border:  #14532d;  /* Badge border */

  /* Red — danger/error */
  --danger:          #ef4444;  /* failed, critical findings, reject */
  --danger-bg:       #1c0a0a;  /* Badge background */
  --danger-border:   #7f1d1d;  /* Badge border */

  /* Yellow — warning/HITL */
  --warning:         #fbbf24;  /* needs_approval, needs_clarification, HITL */
  --warning-bg:      #1a1000;  /* Badge background */
  --warning-border:  #92400e;  /* Badge border */

  /* Blue — info */
  --info:            #60a5fa;  /* Reviewer waves, info states */
  --info-bg:         #0c1a30;  /* Badge background */
  --info-border:     #1e3a5f;  /* Badge border */

  /* Pipeline stage dots */
  --stage-pending:   #4b5563;  /* Pending stage dot */
  --stage-running:   #f59e0b;  /* Active stage dot — animate-pulse */
  --stage-success:   #22c55e;  /* Completed stage dot */
  --stage-paused:    #fbbf24;  /* HITL-paused stage dot */
  --stage-failed:    #ef4444;  /* Failed stage dot */

  /* Log stream */
  --log-timestamp:   #f59e0b;  /* Timestamps in log lines */
  --log-source:      #9ca3af;  /* Source label (aider/llm) */
  --log-text:        #d1d5db;  /* Log line body text */
  --log-bg:          #050508;  /* Log panel background — always dark */
}

/* Light mode — paper-white, same hard-edge / border-only depth */
.light {
  --background:      #fafaf8;
  --surface:         #f4f3f0;
  --surface-raised:  #eeede9;
  --border:          #d4d2cc;
  --border-strong:   #b8b5ae;
  --text:            #1a1a14;
  --text-muted:      #6b6b5e;
  --text-dim:        #9e9b92;
  --accent:          #b45309;  /* Darkened for contrast on light bg */
  --accent-bg:       #fef3c7;
  --accent-border:   #d97706;
  --accent-dim:      #a16207;

  /* Log panel intentionally stays dark in light mode */
  --log-bg:          #1a1a14;
  --log-timestamp:   #f59e0b;  /* Same — log panel is always dark */
  --log-text:        #d1d5db;  /* Same — log panel is always dark */

  /* All semantic status colors unchanged in light mode */
  /* --success, --danger, --warning, --info and their -bg/-border variants
     remain identical to the :root (dark) values above */
}
```

**Default mode:** dark (`:root` block is the dark theme). The `ThemeProvider` applies `.light` class to `<html>` for light mode. See Section 9 for ThemeProvider spec.

---

## 3. Typography

### Google Fonts import

Add to `index.html` `<head>` (before any CSS):

```html
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link
  href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Inter:wght@400;500&display=swap"
  rel="stylesheet"
/>
```

### CSS custom properties

Add to `:root` block in `index.css`:

```css
/* Typography */
--font-mono: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace;
--font-sans: 'Inter', system-ui, sans-serif;  /* HITL prose only */

--text-xs:   10px;
--text-sm:   12px;
--text-base: 13px;
--text-md:   14px;
--text-lg:   16px;
--text-xl:   20px;   /* Cost/health chart numerals */

--font-normal: 400;
--font-medium: 500;
--font-bold:   700;

--tracking-wide:  0.08em;   /* ALL-CAPS labels */
--tracking-tight: -0.01em;  /* Large numerals */
```

### Usage rules

| Context | Font | Notes |
|---|---|---|
| All UI text by default | `--font-mono` | Sidebar, nav, badges, cards, tables, inputs, buttons |
| HITL clarification prose | `--font-sans` | `HITLCard` goal/reason block and numbered question list only |
| AlertDialog body | `--font-sans` | Prose only — button labels stay mono |
| Chart numerals (cost/health) | `--font-mono` | `--text-xl`, `--tracking-tight` |
| ALL-CAPS labels | `--font-mono` | `--text-xs`, `--tracking-wide`, `--text-dim` |

Set the global default in `index.css` body:

```css
body {
  font-family: var(--font-mono);
  font-size: var(--text-base);
  background-color: var(--background);
  color: var(--text);
}
```

---

## 4. Spacing & Radius

**Base unit: 8px.** All padding, margin, and gap values must be multiples of 8px. The 4px value is permitted for tight typographic rhythm inside a text block only (e.g. label + value pairs within a card).

```css
/* Radius */
--radius-sm: 2px;  /* Cards, badges, inputs, buttons */
--radius-md: 4px;  /* Modals, popovers */
```

### Standard padding values

| Surface | Value |
|---|---|
| Main content area | `24px` all sides |
| Sidebar inner padding (top/bottom) | `16px` |
| Sidebar nav link | `0 8px` (height: `36px`) |
| Cards | `16px` |
| Table cells | `8px 0` vertical, `0` horizontal (border-b separates rows) |
| Badge | `2px 6px` |
| Button (sm) | `4px 12px` |
| Board column | `8px` |
| Board task card | `10px 12px` |

### Deviations policy

Any spacing value that does not fit the 8px grid must be documented inline with a comment and justified by a typographic or layout constraint. Never add arbitrary pixel values silently.

---

## 5. Depth (Borders Only)

**Absolute rule: zero box-shadow, zero blur, zero gradients anywhere in the codebase.** This applies to all themes including light mode. Depth is expressed exclusively through background color differentiation and border weight.

### Border patterns

| Pattern | CSS |
|---|---|
| Default card | `border: 1px solid var(--border); border-radius: var(--radius-sm);` |
| Status left-accent card | `border: 1px solid var(--border); border-left: 2px solid var(<status-color>); border-radius: var(--radius-sm);` |
| HITL card | `border: 1px solid var(--warning-border); border-top: 2px solid var(--warning); border-radius: var(--radius-sm);` |
| Sidebar right edge | `border-right: 1px solid var(--border);` |
| Log panel | `border: 1px solid var(--border); border-radius: var(--radius-sm);` (distinct `--log-bg` creates inset read) |
| Focused input | `border: 1px solid var(--border-strong);` — no outline, no ring |
| Hovered card | `border-color: var(--border-strong);` — border only, no transform |
| Modal/popover | `border: 1px solid var(--border); border-radius: var(--radius-md); background: var(--surface-raised);` |
| Empty board column | `border: 1px dashed var(--border); border-radius: var(--radius-sm);` |
| Table row divider | `border-bottom: 1px solid var(--border);` |
| Section divider | `border-top: 1px solid var(--border);` |

### Focus/hover contract

- **Hover on interactive elements:** change `border-color` to `var(--border-strong)` only.
- **Focus on inputs:** change `border-color` to `var(--border-strong)`, remove default `outline`. Do not add `box-shadow` focus rings.
- **Active nav link:** `background: var(--accent-bg)`, `border-left: 2px solid var(--accent)`. No shadow.
- **Selected option button (HITL):** `background: var(--accent-bg)`, `border: 1px solid var(--accent)`.

---

## 6. Sidebar Spec

### Dimensions

| Property | Value |
|---|---|
| Width | `160px`, fixed |
| Background | `var(--surface)` |
| Right border | `1px solid var(--border)` |
| Position | `fixed`, full height |

### Brand treatment

```
◆ WORKSHOP
```

- Color: `var(--accent)`
- Font: `var(--font-mono)`, `var(--font-bold)`, `var(--tracking-wide)`
- Letter-case: ALL CAPS
- Top padding: `16px`
- No subtitle, no version number

### Nav link states

| State | Background | Border-left | Text color | Prefix |
|---|---|---|---|---|
| Active | `var(--accent-bg)` | `2px solid var(--accent)` | `var(--accent)` | `▶` |
| Idle | none | none | `var(--text-muted)` | `○` |
| Hover | none | none | `var(--text)` | `○` |

- Height: `36px`
- Font: `var(--font-mono)`, `var(--text-base)`
- Width: full sidebar width
- Padding: `0 8px`
- Prefix is a fixed-width ASCII character, `width: 14px`, `display: inline-block`
- No Lucide icons

### Config sub-nav (always expanded — no toggle)

The single "Config" link is replaced with a labeled sub-section. It is always visible — never collapsed, never behind a toggle. This fixes the nav discoverability bug where `ModelsConfigPage`, `ReviewersConfigPage`, and `PoliciesConfigPage` were unreachable from the sidebar.

```
CONFIG                    ← --text-dim, --text-xs, --tracking-wide, uppercase divider
  ○ Models               ← indented 12px
  ○ Reviewers            ← indented 12px
  ○ Policies             ← indented 12px
```

- Divider label: `var(--text-dim)`, `var(--text-xs)`, `var(--tracking-wide)`, no background, `padding: 8px 8px 4px`
- Sub-items follow identical active/idle/hover link states as primary nav items
- Routes: `/config/models`, `/config/reviewers`, `/config/policies`

### HITL badge

The HITL Queue nav item shows a count badge when `hitlCount > 0`:

- Badge: `var(--warning)` background, `var(--background)` text, `var(--text-xs)`, `border-radius: 9999px`, `min-width: 18px`, `height: 18px`
- Truncate at `9+` if count exceeds 9

### Theme toggle (bottom)

- Position: bottom of sidebar, above the logout button, `border-top: 1px solid var(--border)`
- Text: `◑ dark` or `◑ light` depending on current mode
- Behavior: toggles `.light` class on `<html>`, persists to `localStorage`
- Font: `var(--font-mono)`, `var(--text-sm)`, `var(--text-muted)`
- Hover: `var(--text)`
- No background on hover — text color change only

### Logout button (very bottom)

- Text: `→ sign out` (no Lucide icon)
- Font: `var(--font-mono)`, `var(--text-sm)`, `var(--text-muted)`
- Hover: `var(--text)`

---

## 7. Component Token Map

### StatusBadge

`border-radius: var(--radius-sm)`, `font-family: var(--font-mono)`, `font-size: var(--text-xs)`, `border: 1px solid`, `padding: 2px 6px`

| Status | Text | Background | Border | ASCII prefix |
|---|---|---|---|---|
| `running` | `var(--accent)` | `var(--accent-bg)` | `var(--accent-border)` | `● ` |
| `needs_approval` | `var(--warning)` | `var(--warning-bg)` | `var(--warning-border)` | `⌛ ` |
| `needs_clarification` | `var(--warning)` | `var(--warning-bg)` | `var(--warning-border)` | `⌛ ` |
| `needs_step_recovery` | `var(--warning)` | `var(--warning-bg)` | `var(--warning-border)` | `⌛ ` |
| `needs_review_recovery` | `var(--warning)` | `var(--warning-bg)` | `var(--warning-border)` | `⌛ ` |
| `needs_timeout_recovery` | `var(--warning)` | `var(--warning-bg)` | `var(--warning-border)` | `⌛ ` |
| `stopped` | `var(--text-muted)` | `var(--surface-raised)` | `var(--border)` | (none) |
| `approval_rejected` | `var(--danger)` | `var(--danger-bg)` | `var(--danger-border)` | `✗ ` |
| `pushing` | `var(--accent)` | `var(--accent-bg)` | `var(--accent-border)` | `↑ ` |
| `pushed` | `var(--success)` | `var(--success-bg)` | `var(--success-border)` | `✓ ` |
| `push_failed` | `var(--danger)` | `var(--danger-bg)` | `var(--danger-border)` | `✗ ` |
| `failed` | `var(--danger)` | `var(--danger-bg)` | `var(--danger-border)` | `✗ ` |
| `pending` | `var(--text-dim)` | `var(--surface)` | `var(--border)` | `○ ` |

### TaskCard (Kanban board)

| Property | Token |
|---|---|
| Container background | `var(--surface)` |
| Container border | `1px solid var(--border)` |
| Container border-left | `2px solid var(<status-color>)` |
| Container border-radius | `var(--radius-sm)` |
| Container hover border-color | `var(--border-strong)` |
| Goal text color | `var(--text)` |
| Goal font | `var(--font-mono)`, `var(--text-base)` |
| Goal max lines | 2 (CSS `line-clamp: 2`) |
| Meta row color | `var(--text-dim)` |
| Meta row font | `var(--font-mono)`, `var(--text-xs)` |
| Meta format | `repo · $cost · time-ago` |
| Card width | `180px` |
| Card padding | `10px 12px` |

Status-color for border-left uses the same color as the badge text token for that status (e.g. `running` → `var(--accent)`, `pushed` → `var(--success)`, `failed` → `var(--danger)`).

### PipelineStageProgress

7-dot vertical list in the TaskDetail left panel.

| Property | Value |
|---|---|
| Dot size | `8px × 8px`, `border-radius: 50%` |
| Connecting line | `1px solid var(--border)`, vertical, centered between dots |
| Dot spacing | `16px` between dot centers |

| Stage state | Dot color | Animation |
|---|---|---|
| `pending` | `var(--stage-pending)` | none |
| `running` | `var(--stage-running)` | `animate-pulse` (Tailwind built-in or `@keyframes pulse`) |
| `success` | `var(--stage-success)` | none |
| `paused` | `var(--stage-paused)` | none |
| `failed` | `var(--stage-failed)` | none |

Active stage label:
- Color: `var(--accent)`
- Font: `var(--font-mono)`, `var(--font-medium)`, `var(--text-sm)`
- Inactive labels: `var(--text-muted)`, `var(--font-normal)`

Pulse animation spec (if not using Tailwind `animate-pulse`):
```css
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.35; }
}
```

### LogStream

| Property | Token/Value |
|---|---|
| Container background | `var(--log-bg)` |
| Container border | `1px solid var(--border)` |
| Container border-radius | `var(--radius-sm)` |
| Container height | `h-full` with `min-height: 192px` (replaces hardcoded `h-64`) |
| Font | `var(--font-mono)`, `var(--text-xs)` |
| Scroll | Virtualized (TanStack Virtual — keep existing) |
| Overflow | `overflow: hidden` on container; virtual scroller handles scroll |

Line format — fixed-width columns separated by double-space:

```
TIMESTAMP  SOURCE   body text here
```

- Timestamp: `var(--log-timestamp)`, fixed `width: 8ch`
- Source label: `var(--log-source)`, fixed `width: 8ch`
- Body: `var(--log-text)`

### HITLCard

| Property | Token/Value |
|---|---|
| Container background | `var(--surface)` |
| Container border | `1px solid var(--warning-border)` |
| Container border-top | `2px solid var(--warning)` |
| Container border-radius | `var(--radius-sm)` |
| Header text | `"⌛ ACTION REQUIRED"` |
| Header color | `var(--warning)` |
| Header font | `var(--font-mono)`, `var(--text-xs)`, `var(--tracking-wide)` |
| Goal/reason text | `var(--font-sans)`, `var(--text-sm)`, `var(--text)` |
| Steps/questions | `var(--font-mono)`, `var(--text-sm)` |

Option buttons:

| State | Border | Background | Text |
|---|---|---|---|
| Default | `1px solid var(--border)` | `var(--surface)` | `var(--text-muted)` |
| Hover | `1px solid var(--border-strong)` | `var(--surface)` | `var(--text)` |
| Selected | `1px solid var(--accent)` | `var(--accent-bg)` | `var(--accent)` |

Primary action button: `background: var(--accent)`, `color: var(--background)`, `font-weight: var(--font-bold)`, `border-radius: var(--radius-sm)`

Reject/destructive action: see DestructiveConfirmButton below.

### DestructiveConfirmButton (AlertDialog)

Trigger button:
- Border: `1px solid var(--danger-border)`
- Text color: `var(--danger)`
- Background: `var(--surface)`
- Font: `var(--font-mono)`, `var(--text-sm)`

AlertDialog modal:
- Overlay: `background: rgba(0,0,0,0.7)` — no blur
- Container: `background: var(--surface-raised)`, `border: 1px solid var(--border)`, `border-radius: var(--radius-md)`
- Title: `var(--font-mono)`, `var(--text-md)`, `var(--text)`
- Description: `var(--font-sans)`, `var(--text-sm)`, `var(--text-muted)`
- Confirm button: `background: var(--danger)`, `color: var(--background)`, `border-radius: var(--radius-sm)`
- Cancel button: `border: 1px solid var(--border)`, `background: var(--surface)`, `color: var(--text-muted)`

---

## 8. Page Status Grid

| Page | Route | Loading | Empty | Error | HITL-aware? |
|---|---|---|---|---|---|
| BoardPage | `/board` | Skeleton columns (3 dashed outlines) | `"--empty--"` centered in dashed column | Inline error banner | Yes — tasks surface HITL status badges |
| HITLQueuePage | `/hitl` | Skeleton cards (2 rows) | `"no pending actions"` in `--text-dim` | Inline error banner | Yes — is the HITL page |
| TaskDetailPage | `/tasks/:id` | Skeleton: left panel dots + right log | `"no logs yet"` in log panel | Full-page error with retry | Yes — shows HITLCard when paused |
| LaunchPage | `/launch` | None (form is static) | n/a | Form-level field errors | No |
| CostPage | `/cost` | Spinner centered | `"no cost data"` in `--text-dim` | Inline error banner | No |
| HealthPage | `/health` | Spinner centered | `"no health data"` | Inline error banner | No |
| SkillsPage | `/skills` | Skeleton rows | `"no skills found"` | Inline error banner | No |
| SkillEditorPage | `/skills/:id` | Spinner | n/a | Inline error | No |
| ReposPage | `/repos` | Skeleton rows | `"no repos configured"` | Inline error banner | No |
| ModelsConfigPage | `/config/models` | Spinner centered | n/a — page has no empty state | Inline error + disabled Save button | No |
| ReviewersConfigPage | `/config/reviewers` | Spinner centered | `"no reviewers configured"` | Inline error | No |
| PoliciesConfigPage | `/config/policies` | Spinner centered | `"no policies configured"` | Inline error | No |
| LoginPage | `/login` | None | n/a | Form error inline | No |

**Skeleton convention:** use `var(--surface-raised)` with `animate-pulse` for all skeleton blocks. No third-party skeleton library.

**Error banner convention:** single-line bar, `background: var(--danger-bg)`, `border: 1px solid var(--danger-border)`, `color: var(--danger)`, `var(--text-xs)`, `var(--font-mono)`. Positioned at the top of the content area, below `PageHeader`.

**Empty state convention:** centered vertically in the content area, `"--empty--"` or descriptive string in `var(--text-dim)`, `var(--font-mono)`, `var(--text-sm)`.

---

## 9. New Primitives Needed

All primitives use shadcn/ui as the base. Install via `pnpm dlx shadcn@latest add <component>`. Reskin to Terminal Forge tokens — do not use the default shadcn color variables.

### `textarea`

```tsx
// shadcn: pnpm dlx shadcn@latest add textarea
// Props to expose:
interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  error?: boolean;
}
```

Styles: `font-family: var(--font-mono)`, `font-size: var(--text-sm)`, `background: var(--surface)`, `color: var(--text)`, `border: 1px solid var(--border)`, `border-radius: var(--radius-sm)`, `padding: 8px 10px`. Focus: `border-color: var(--border-strong)`, no outline, no ring. Error: `border-color: var(--danger-border)`. Resize: `vertical` only.

### `checkbox`

```tsx
// shadcn: pnpm dlx shadcn@latest add checkbox
// Props: standard Radix Checkbox props
```

Styles: `width: 14px`, `height: 14px`, `border: 1px solid var(--border)`, `border-radius: 1px` (tighter than `--radius-sm`), `background: var(--surface)`. Checked: `background: var(--accent)`, `border-color: var(--accent-border)`. Checkmark: `color: var(--background)`. Focus: `border-color: var(--border-strong)`.

### `alert-dialog`

```tsx
// shadcn: pnpm dlx shadcn@latest add alert-dialog
// Re-export all Radix parts: AlertDialog, AlertDialogTrigger, AlertDialogContent,
// AlertDialogHeader, AlertDialogFooter, AlertDialogTitle, AlertDialogDescription,
// AlertDialogAction, AlertDialogCancel
```

Token overrides per DestructiveConfirmButton spec in Section 7. No animation blur. Overlay: `rgba(0,0,0,0.7)` flat. Entry animation: `opacity 0 → 1` over `120ms` only — no scale, no translate.

### ThemeProvider

```tsx
// File: src/components/ThemeProvider.tsx

const STORAGE_KEY = 'ultra-workshop-theme';
type Theme = 'dark' | 'light';

// On mount:
// 1. Read localStorage.getItem(STORAGE_KEY)
// 2. If null, check window.matchMedia('(prefers-color-scheme: light)').matches
// 3. Apply theme by toggling class 'light' on document.documentElement
//    (dark mode = no class added; light mode = add class 'light')
// 4. Expose setTheme(theme: Theme) via context

interface ThemeContextValue {
  theme: Theme;
  setTheme: (theme: Theme) => void;
}
```

- **Default:** `'dark'` (`:root` styles apply when no class on `<html>`)
- **Light mode:** add class `'light'` to `<html>` element
- **Storage key:** `'ultra-workshop-theme'`
- **Class toggle target:** `document.documentElement` (the `<html>` element)
- **System pref:** only used as fallback when localStorage has no entry

### ThemeToggle

```tsx
// File: src/components/ThemeToggle.tsx
// Renders: <button> with text "◑ dark" or "◑ light"
// Calls setTheme() from ThemeContext on click
// No icon library — ASCII prefix only
```

Styles: see Sidebar spec Section 6 (theme toggle placement at sidebar bottom).

---

## 10. Bug Fix Specs

### A. useSSE.ts — addEventListener for named events

**File:** `src/lib/useSSE.ts`  
**Problem:** The SSE server emits named events (`log`, `state`, `progress`) via `event: log\ndata: ...` syntax. The browser `EventSource` `onmessage` handler only fires for unnamed events (i.e. `event: message` or no `event:` field). Named events are silently dropped.

**Fix:** After setting `es.onmessage`, add `addEventListener` calls for each named event type. All three handlers share identical parse-and-push logic with `onmessage`.

```typescript
// In the connect() function, after the es.onmessage = ... block,
// add the following three event listeners:

const namedEvents = ['log', 'state', 'progress'] as const;
const handleNamedEvent = (e: MessageEvent<string>) => {
  try {
    const parsed = JSON.parse(e.data) as T;
    if (onMessage) onMessage(parsed);
    setLines((prev) => {
      const next = prev.length >= cap ? prev.slice(-(cap - 1)) : prev;
      return [...next, parsed];
    });
  } catch {
    // Ignore parse errors for non-JSON SSE messages
  }
};

namedEvents.forEach((name) => {
  es.addEventListener(name, handleNamedEvent);
});
```

The `handleNamedEvent` function body is intentionally identical to the `es.onmessage` body — this is correct, not duplication to be abstracted away.

The cleanup in the existing `useEffect` return function does not need to change — `es.close()` removes all listeners automatically.

### B. Sidebar.tsx — config sub-nav expansion

**File:** `src/components/layout/Sidebar.tsx`  
**Problem:** The single `{ to: "/config/models", label: "Config", icon: <Settings /> }` nav item only navigates to the models page. The reviewers (`/config/reviewers`) and policies (`/config/policies`) pages are unreachable from the sidebar.

**Fix:** Remove the `NavItem` entry for `"Config"`. Add a separate rendering block after the main `navItems.map()` loop that renders the always-visible CONFIG section:

```tsx
// After the navItems.map() block:
<div className="config-section">
  <div className="config-label">CONFIG</div>
  {[
    { to: '/config/models',    label: 'Models' },
    { to: '/config/reviewers', label: 'Reviewers' },
    { to: '/config/policies',  label: 'Policies' },
  ].map((item) => (
    <Link
      key={item.to}
      to={item.to}
      className={cn('nav-link nav-link--indented', '[&.active]:nav-link--active')}
    >
      {/* prefix handled via CSS :is([data-status=active]) or activeProps */}
      {item.label}
    </Link>
  ))}
</div>
```

The `icon` prop is removed entirely from the `NavItem` interface and all nav items. No Lucide icons in the sidebar in the redesigned version.

The active/idle prefix (`▶`/`○`) is rendered as an inline span before the label text, toggled via TanStack Router's `activeProps` or `inactiveProps`.

### C. ModelsConfigPage.tsx — useEffect guard on setRouting

**File:** `src/pages/ModelsConfigPage.tsx`  
**Problem:** The current initialization logic runs `setRouting(initial)` synchronously in the component body during render:

```typescript
// BUGGY — runs setRouting during render, causing React warnings and
// potential infinite re-render loops if the parent re-renders while
// data is the same object reference.
if (data && Object.keys(routing).length === 0) {
  const initial = Object.fromEntries(data.routing.map((r) => [r.agent, r.alias]));
  setRouting(initial);
  originalRef.current = initial;
}
```

**Fix:** Move initialization into a `useEffect` guarded by an `initializedRef`:

```typescript
const initializedRef = useRef(false);

useEffect(() => {
  if (data && !initializedRef.current) {
    initializedRef.current = true;
    const initial = Object.fromEntries(data.routing.map((r) => [r.agent, r.alias]));
    setRouting(initial);
    originalRef.current = initial;
  }
}, [data]);

// Remove the inline if-block entirely from the component body.
```

The `initializedRef.current = true` guard ensures that if `data` is refetched (e.g. after a save), the local routing state is not reset to the server state while the user has unsaved changes. The `isDirty` check continues to work correctly because `originalRef.current` is only updated on successful save (in `handleSave`'s `onSuccess` callback).

---

## 11. Non-Goals

This DESIGN.md governs visual identity, component tokens, and the three named bug fixes. It explicitly does NOT change:

- **API contracts** — all `/api/*` endpoint URLs, request/response shapes, and TypeScript types remain untouched
- **Routing** — TanStack Router route definitions, route tree, and `router.tsx` are not modified
- **Authentication** — `src/lib/auth.tsx` and login flow are not modified
- **TanStack Query keys** — all `queryKey` arrays and cache invalidation logic remain untouched
- **SSE URLs** — the URL strings passed to `useSSE`, `useTaskLogStream`, and `useTaskEventStream` are not modified (only the internal listener registration is fixed)
- **Business logic** — any computation, mutation, or state logic in hooks and pages outside the three named bug fixes
- **Read-only config pages** — `ReviewersConfigPage` and `PoliciesConfigPage` remain read-only; no edit functionality is added
- **Backend changes** — nothing in the server, worker, or API layer
- **Test infrastructure** — existing Playwright or vitest tests are not deleted; new tests for the bug fixes are additive only
- **Dependency versions** — no package upgrades except installing shadcn primitives (`textarea`, `checkbox`, `alert-dialog`) via `pnpm dlx shadcn@latest add`
- **TanStack Virtual** — the existing log stream virtualization implementation is kept; only the container height token changes
- **`src/components/ui/`** — existing shadcn components (card, button, badge, select, etc.) are reskinned via CSS tokens, not replaced. Only the three new primitives listed in Section 9 are added.
```
