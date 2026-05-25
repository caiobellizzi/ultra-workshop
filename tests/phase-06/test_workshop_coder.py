from __future__ import annotations

import subprocess

import pytest

from hermes_skills_import import load_module


workshop_coder = load_module("workshop_coder", "hermes-skills/workshop_coder.py")


def test_build_aider_task_disambiguates_12_factory_practices() -> None:
    task = workshop_coder._build_aider_task(
        "create a multi agent orchestration using the best 12 factory practices",
        {},
    )

    assert "non-interactive batch pipeline" in task
    assert "Do not ask the reviewer for clarification" in task
    assert "12-factor app methodology" not in task
    assert "HKUDS/OpenHarness" not in task


def test_build_aider_task_includes_previous_review_feedback() -> None:
    task = workshop_coder._build_aider_task(
        "create a multi agent orchestration",
        {
            "feedback": "Review blocked",
            "blocking_issues": ["Invalid changed path 'pytest'"],
        },
    )

    assert "previous attempt was rejected" in task
    assert "Review blocked" in task
    assert "Invalid changed path 'pytest'" in task


def test_no_diff_returns_clarification_request() -> None:
    request = workshop_coder._clarification_request_for_no_diff(
        "ws-test",
        "create a multi agent orchestration",
        "need more information about the desired behavior",
    )

    assert request.source_stage == "coder"
    assert request.needs_clarification is True
    assert request.allow_free_text is True


def test_run_aider_runner_kills_process_group_on_timeout(monkeypatch) -> None:
    killed: list[tuple[int, int]] = []

    class FakeProcess:
        pid = 12345
        returncode = None

        def communicate(self, timeout):
            raise subprocess.TimeoutExpired(["aider"], timeout)

        def wait(self, timeout):
            self.returncode = -15
            return self.returncode

    def fake_popen(*args, **kwargs):
        assert kwargs["start_new_session"] is True
        assert kwargs["shell"] is False
        return FakeProcess()

    monkeypatch.setattr(workshop_coder.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(workshop_coder.os, "killpg", lambda pid, sig: killed.append((pid, sig)))

    with pytest.raises(subprocess.TimeoutExpired):
        workshop_coder._run_aider_runner(["aider"], env={}, timeout=1)

    assert killed == [(12345, workshop_coder.signal.SIGTERM)]
