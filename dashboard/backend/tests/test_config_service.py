"""Tests for config_service: atomic write + validation rejection."""
from __future__ import annotations

import pytest
import yaml


@pytest.fixture()
def tmp_config_dir(tmp_path, monkeypatch):
    """Monkeypatch settings.hermes_config_dir to a tmp dir with a seed YAML."""
    config_dir = tmp_path / "hermes-config"
    config_dir.mkdir()

    # Seed a minimal stage-policies.yaml
    policies_yaml = config_dir / "stage-policies.yaml"
    seed = {
        "stage_policies": {
            "brainstorm": {"timeout": 300, "auto_retries": 0},
            "triage": {"timeout": 180, "auto_retries": 1},
            "requirements": {"timeout": 180, "auto_retries": 1},
            "planner": {"timeout": 900, "auto_retries": 1},
            "coder": {"timeout": 7200, "tool_timeout": 7200, "auto_retries": 0},
            "reviewer": {"timeout": 300, "auto_retries": 1},
        },
        "model_aliases": {
            "coder-specialist": "coder-worker",
            "triage-specialist": "cheap-fast",
        },
    }
    policies_yaml.write_text(yaml.dump(seed), encoding="utf-8")

    # Seed a review-roster.yaml
    roster_yaml = config_dir / "review-roster.yaml"
    roster = {
        "reviewers": [
            {"role": "security", "model_alias": "reviewer-model", "isolation": True},
            {"role": "correctness", "model_alias": "reviewer-model", "isolation": True},
        ]
    }
    roster_yaml.write_text(yaml.dump(roster), encoding="utf-8")

    from dashboard.backend import config as cfg_module
    monkeypatch.setattr(cfg_module.settings, "hermes_config_dir", str(config_dir))

    return config_dir


class TestStagePolicies:
    def test_get_returns_all_stages(self, tmp_config_dir):
        from dashboard.backend.services.config_service import get_stage_policies
        policies = get_stage_policies()
        assert "coder" in policies
        assert "triage" in policies
        assert policies["coder"]["timeout"] == 7200

    def test_write_valid_policies(self, tmp_config_dir):
        from dashboard.backend.services.config_service import get_stage_policies, set_stage_policies
        new_policies = {
            "brainstorm": {"timeout": 400},
            "triage": {"timeout": 200},
            "requirements": {"timeout": 200},
            "planner": {"timeout": 1000},
            "coder": {"timeout": 3600, "tool_timeout": 3600},
            "reviewer": {"timeout": 400},
        }
        set_stage_policies(new_policies)
        result = get_stage_policies()
        assert result["brainstorm"]["timeout"] == 400
        assert result["coder"]["timeout"] == 3600

    def test_write_missing_stage_rejected(self, tmp_config_dir):
        from dashboard.backend.services.config_service import set_stage_policies
        # Missing 'coder' stage — should be rejected
        incomplete = {
            "brainstorm": {"timeout": 300},
            "triage": {"timeout": 180},
            "requirements": {"timeout": 180},
            "planner": {"timeout": 900},
            # coder missing
            "reviewer": {"timeout": 300},
        }
        with pytest.raises(ValueError, match="missing stages"):
            set_stage_policies(incomplete)

    def test_atomic_write_no_partial_state(self, tmp_config_dir):
        """Verify .tmp file does not remain after successful write."""
        from dashboard.backend.services.config_service import set_stage_policies
        full_policies = {
            s: {"timeout": 100}
            for s in ("brainstorm", "triage", "requirements", "planner", "coder", "reviewer")
        }
        set_stage_policies(full_policies)
        # No .tmp file should remain
        tmp_files = list(tmp_config_dir.glob("*.tmp"))
        assert tmp_files == []


class TestModelAliases:
    def test_get_aliases(self, tmp_config_dir):
        from dashboard.backend.services.config_service import get_model_aliases
        aliases = get_model_aliases()
        assert aliases["coder-specialist"] == "coder-worker"

    def test_write_aliases_no_litellm_config(self, tmp_config_dir, monkeypatch):
        """When no litellm config is present, write should succeed without validation."""
        from dashboard.backend.services import config_service
        # Stub _get_litellm_model_names to return empty set (no config file)
        monkeypatch.setattr(config_service, "_get_litellm_model_names", lambda: set())

        from dashboard.backend.services.config_service import get_model_aliases, set_model_aliases
        set_model_aliases({"coder-specialist": "new-model", "triage-specialist": "cheap-fast"})
        aliases = get_model_aliases()
        assert aliases["coder-specialist"] == "new-model"

    def test_write_aliases_unknown_target_rejected(self, tmp_config_dir, monkeypatch):
        """When litellm config is present, unknown targets should be rejected."""
        from dashboard.backend.services import config_service
        monkeypatch.setattr(
            config_service, "_get_litellm_model_names",
            lambda: {"coder-worker", "cheap-fast"}
        )
        from dashboard.backend.services.config_service import set_model_aliases
        with pytest.raises(ValueError, match="unknown LiteLLM model targets"):
            set_model_aliases({"coder-specialist": "nonexistent-model"})


class TestRoster:
    def test_get_roster(self, tmp_config_dir):
        from dashboard.backend.services.config_service import get_roster
        roster = get_roster()
        assert any(r["role"] == "security" for r in roster)
        assert any(r["role"] == "correctness" for r in roster)

    def test_write_valid_roster(self, tmp_config_dir):
        from dashboard.backend.services.config_service import get_roster, set_roster
        new_roster = [
            {"role": "security", "model_alias": "reviewer-model", "isolation": True},
            {"role": "correctness", "model_alias": "reviewer-model", "isolation": True},
            {"role": "python", "model_alias": "reviewer-model", "isolation": False},
        ]
        set_roster(new_roster)
        result = get_roster()
        assert len(result) == 3

    def test_write_missing_security_rejected(self, tmp_config_dir):
        from dashboard.backend.services.config_service import set_roster
        with pytest.raises(ValueError, match="required reviewers"):
            set_roster([
                {"role": "correctness", "model_alias": "reviewer-model", "isolation": True},
                # security missing
            ])

    def test_write_missing_correctness_rejected(self, tmp_config_dir):
        from dashboard.backend.services.config_service import set_roster
        with pytest.raises(ValueError, match="required reviewers"):
            set_roster([
                {"role": "security", "model_alias": "reviewer-model", "isolation": True},
                # correctness missing
            ])
