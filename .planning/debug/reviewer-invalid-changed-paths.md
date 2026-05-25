---
status: resolved
trigger: "$gsd-debug the reviwer issue and fix"
created: "2026-05-25"
updated: "2026-05-25T19:43:41Z"
---

# Debug Session: reviewer-invalid-changed-paths

## Symptoms

Expected behavior: Workshop reviewer should evaluate only real file changes from the coder workspace and should not reject shell commands or stdout fragments as changed paths.

Actual behavior: Telegram build task `ws-9d1bf0` failed after three reviewer attempts. Reviewer blocked paths such as `pytest tests` and `python openharness_orchestration.py` as invalid changed paths outside the plan.

Error messages:
- `review failed after 3 attempts: Review blocked with 3 issue(s); fix the blocking issues and retry.`
- `Invalid changed path 'pytest tests': whitespace makes it look like a shell command, not a file.`
- `Invalid changed path 'python openharness_orchestration.py': whitespace makes it look like a shell command, not a file.`

Timeline: Observed during Telegram `/build --repo test-workshop-sandbox ... OpenHarness` live run on 2026-05-25.

Reproduction: Run the workshop build pipeline until coder output is reviewed. The reviewer sees command-like strings in `diff.changes[].path`.

## Current Focus

hypothesis: The reviewer is correct; the coder emits every path from `git diff --name-only <head_before_aider>` without validating against the plan or command-artifact rules, so files accidentally created by Aider with command-like names become `diff.changes[].path`.
test: Completed focused source inspection, live state inspection, controlled git reproduction, coder-boundary patch, and regression tests.
expecting: Patched coder sanitizes/cleans produced diff paths before reviewer receives the envelope, while keeping reviewer rejection as defense-in-depth.
next_action: Deploy patched `workshop_coder.py` and rerun Telegram `/build`.
reasoning_checkpoint:
tdd_checkpoint:

## Evidence

- timestamp: 2026-05-25T19:19:34Z; task `ws-9d1bf0` recorded `review_complete` with `passed=false`, reviewer attempt 3.
- timestamp: 2026-05-25; state `stages.review.blocking_issues` contains invalid changed paths `pytest tests` and `python openharness_orchestration.py`.
- timestamp: 2026-05-25T19:39:24Z
  checked: active debug/session prerequisites
  found: Resumed existing `.planning/debug/reviewer-invalid-changed-paths.md`; no project-local `.codex/skills` or `.agents/skills` directories found; no `.planning/debug/knowledge-base.md` found.
  implication: Continue with direct source investigation; no known-pattern candidate or project-specific skill rules are available.
- timestamp: 2026-05-25T19:42:29Z
  checked: live task state and local source
  found: Remote task `ws-9d1bf0` has clean planner `affected_files` (`openharness_orchestration.py`, `tests/test_openharness_orchestration.py`, `README.md`) but reviewer saw invalid `diff.changes[].path` values `pytest tests` and `python openharness_orchestration.py`. `workshop_coder.py` builds `changes` by iterating every non-empty line from `git diff --name-only <head_before_aider>` and appending it directly as `{"path": file_path, ...}`.
  implication: Bad paths were introduced after planning, at the coder/Aider diff boundary; reviewer validation is detecting the contaminated envelope rather than creating it.
- timestamp: 2026-05-25T19:43:00Z
  checked: controlled git reproduction of coder diff primitive
  found: A temp repo with a valid file plus files named `pytest tests` and `python openharness_orchestration.py` returns all three names from `git diff --name-only <baseline>`.
  implication: The exact Git command used by `workshop_coder.py` can surface command-shaped file names unchanged; without coder-side filtering/cleanup they become reviewer-visible changed paths.
- timestamp: 2026-05-25T19:43:41Z
  checked: focused existing tests
  found: `python3 -m pytest tests/phase-04/test_reviewer.py tests/phase-06/test_workshop_reviewer.py tests/phase-06/test_workshop_coder.py -q` passed (`9 passed`).
  implication: Current tests cover reviewer blocking behavior and coder task construction, but not coder-side sanitization/cleanup of invalid or out-of-plan diff paths.
- timestamp: 2026-05-25
  checked: remote failed workspace
  found: Aider commit `0569f2e` added files literally named `pytest tests` and `python openharness_orchestration.py`.
  implication: The reviewer was rejecting real committed files produced by Aider, not hallucinated paths.
- timestamp: 2026-05-25
  checked: fixed local tests
  found: `python3 -m pytest tests/phase-04 tests/phase-06 -q` passed (`56 passed`).
  implication: Coder-side sanitization and reviewer command-artifact coverage are now tested.

## Eliminated

- hypothesis: Reviewer fallback parsing is extracting command/output lines from stdout.
  evidence: `workshop/reviewer.py::review_query` never parses coder stdout; it only validates `Diff.model_validate(query["diff"])` and iterates `diff.changes`.
  timestamp: 2026-05-25T19:43:00Z
- hypothesis: Planner emitted `pytest tests` or `python openharness_orchestration.py` as planned files.
  evidence: Remote task `ws-9d1bf0` state shows planner `affected_files` and all step files are clean (`openharness_orchestration.py`, `tests/test_openharness_orchestration.py`, `README.md`).
  timestamp: 2026-05-25T19:43:00Z

## Resolution

root_cause: `hermes-skills/workshop_coder.py` trusted every path returned by `git diff --name-only <head_before_aider>` and emitted it as `Diff.changes[].path` without validating against the plan or the reviewer path rules. The live planner output was clean, and reviewer only validates the supplied `Diff`; therefore command-shaped files created by Aider inside the workspace passed through the coder envelope and caused reviewer rejection.
fix: Added coder-side sanitization/cleanup at the diff boundary. The coder now builds the allowed planned path set from `plan.affected_files` and `steps[].files`, removes or restores invalid/out-of-plan workspace changes, commits the cleanup on the task branch, and rebuilds `changes` only from clean planned paths. Reviewer validation remains defense-in-depth.
verification: `python3 -m pytest tests/phase-04 tests/phase-06 -q` passed (`56 passed`).
files_changed: `hermes-skills/workshop_coder.py`, `tests/phase-06/test_workshop_coder.py`, `tests/phase-06/test_workshop_reviewer.py`
