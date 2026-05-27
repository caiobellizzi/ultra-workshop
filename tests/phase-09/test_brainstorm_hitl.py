from __future__ import annotations

"""
Brainstorm HITL loop guards (REQ-ws-043).

These tests verify that the brainstorm stage:
  1. Does NOT exit without brainstorm_approved=True (stays in brainstorm stage).
  2. DOES exit when brainstorm_approved=True (advances to triage).

The brainstorm stage handler is implemented in 09-03 (wired into workshop_build.py).
These stubs are skipped until that implementation lands.
"""

import pytest


@pytest.mark.skip(reason="brainstorm stage not yet implemented (09-03)")
def test_brainstorm_loop_does_not_exit_without_approval() -> None:
    """
    When state['brainstorm_approved'] is False (or absent), the brainstorm
    stage handler must set state['next_stage'] = 'brainstorm' (re-enter loop)
    rather than advancing to 'triage'.

    Implementation note (09-03): patch subprocess and sys.exit; call the
    brainstorm stage block in workshop_build.py via _load_module; assert
    state['next_stage'] == 'brainstorm'.
    """
    raise NotImplementedError("Implement after 09-03 wires the brainstorm stage")


@pytest.mark.skip(reason="brainstorm stage not yet implemented (09-03)")
def test_brainstorm_loop_exits_when_approved() -> None:
    """
    When state['brainstorm_approved'] is True, the brainstorm stage handler
    must set state['next_stage'] = 'triage' and leave brainstorm_approved=True.

    Implementation note (09-03): patch subprocess and sys.exit; call the
    brainstorm stage block; assert state['next_stage'] == 'triage'.
    """
    raise NotImplementedError("Implement after 09-03 wires the brainstorm stage")
