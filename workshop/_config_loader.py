"""Runtime config loader for stage policies and model aliases.

Reads ``hermes-config/stage-policies.yaml`` at startup and caches the result
for ~10 s.  On any read/parse failure, falls back to the original hard-coded
dicts defined below as ``_FALLBACK_STAGE_POLICIES`` and
``_FALLBACK_MODEL_ALIASES``.

Path resolution order for the YAML file:
1. ``$UWS_CONFIG_DIR/stage-policies.yaml``   (explicit env override)
2. ``/opt/ultra-workshop/hermes-config/stage-policies.yaml``  (production default)
3. ``<repo_root>/hermes-config/stage-policies.yaml``          (dev/test fallback)
"""
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

# Avoid a circular import: StagePolicy lives in stage_policy.py which imports
# us; we import StagePolicy lazily inside the functions that need it.

# ---------------------------------------------------------------------------
# Fallback dicts (originals from stage_policy.py; kept in sync manually)
# ---------------------------------------------------------------------------

# NOTE: The coder entry uses sentinel values (0) for timeout/tool_timeout so the
# _build_stage_policy helper can apply the UWS_CODER_MAX env override at load
# time for BOTH the fallback AND the YAML-loaded paths.

_FALLBACK_STAGE_POLICIES_RAW: dict[str, dict] = {
    "brainstorm": {"timeout": 300, "auto_retries": 0, "hitl_on_timeout": True},
    "triage":     {"timeout": 180, "auto_retries": 1},
    "requirements": {"timeout": 180, "auto_retries": 1},
    "planner":    {"timeout": 900, "auto_retries": 1},
    "coder":      {"timeout": 7200, "tool_timeout": 7200, "auto_retries": 0, "hitl_on_timeout": False},
    "reviewer":   {"timeout": 300, "auto_retries": 1},
}

_FALLBACK_MODEL_ALIASES: dict[str, str] = {
    "triage-specialist": "cheap-fast",
    "requirements-specialist": "cheap-fast",
    "planner-specialist": "planner-reasoner",
    "coder-specialist": "coder-worker",
    "reviewer-specialist": "reviewer-model",
    "correctness-reviewer": "reviewer-model",
    "security-reviewer": "reviewer-model",
    "python-reviewer": "reviewer-model",
    "typescript-reviewer": "reviewer-model",
    "reactjs-reviewer": "reviewer-model",
    "qa-reviewer": "reviewer-model",
    "docs-reviewer": "reviewer-model",
    "config-reviewer": "reviewer-model",
    "merge-agent": "reviewer-model",
    "brainstorm-specialist": "default-worker",
    "brainstorm": "default-worker",
}

# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

_PRODUCTION_CONFIG_DIR = Path("/opt/ultra-workshop/hermes-config")
_REPO_CONFIG_DIR = Path(__file__).parent.parent / "hermes-config"


def _config_dir() -> Path:
    env_override = os.environ.get("UWS_CONFIG_DIR")
    if env_override:
        return Path(env_override)
    if _PRODUCTION_CONFIG_DIR.is_dir():
        return _PRODUCTION_CONFIG_DIR
    return _REPO_CONFIG_DIR


def _yaml_path() -> Path:
    return _config_dir() / "stage-policies.yaml"


# ---------------------------------------------------------------------------
# StagePolicy construction helper
# ---------------------------------------------------------------------------

def _build_stage_policy(stage: str, raw: dict) -> "StagePolicy":  # type: ignore[name-defined]
    from workshop.stage_policy import StagePolicy  # local import to avoid circular dep

    timeout: int = int(raw.get("timeout", 0))
    tool_timeout = raw.get("tool_timeout")
    if tool_timeout is not None:
        tool_timeout = int(tool_timeout)
    auto_retries: int = int(raw.get("auto_retries", 0))
    hitl_on_timeout: bool = bool(raw.get("hitl_on_timeout", False))

    # Apply UWS_CODER_MAX override for the coder stage
    if stage == "coder":
        coder_max = int(os.environ.get("UWS_CODER_MAX", "7200"))
        timeout = coder_max
        if tool_timeout is not None:
            tool_timeout = coder_max

    return StagePolicy(
        timeout=timeout,
        tool_timeout=tool_timeout,
        auto_retries=auto_retries,
        hitl_on_timeout=hitl_on_timeout,
    )


# ---------------------------------------------------------------------------
# Cache (module-level, ~10 s TTL)
# ---------------------------------------------------------------------------

_TTL = 10.0  # seconds

_stage_policies_cache: dict[str, "StagePolicy"] | None = None  # type: ignore[type-arg]
_stage_policies_loaded_at: float = 0.0

_model_aliases_cache: dict[str, str] | None = None
_model_aliases_loaded_at: float = 0.0


# ---------------------------------------------------------------------------
# Public loaders
# ---------------------------------------------------------------------------

def load_stage_policies() -> "dict[str, StagePolicy]":  # type: ignore[type-arg]
    """Return the current stage-policies mapping, using the ~10s TTL cache."""
    global _stage_policies_cache, _stage_policies_loaded_at

    now = time.monotonic()
    if _stage_policies_cache is not None and (now - _stage_policies_loaded_at) < _TTL:
        return _stage_policies_cache

    raw_policies = _read_yaml_section("stage_policies")
    if raw_policies is None:
        raw_policies = _FALLBACK_STAGE_POLICIES_RAW

    result: dict = {}
    for stage, raw in raw_policies.items():
        try:
            result[stage] = _build_stage_policy(stage, raw if isinstance(raw, dict) else {})
        except Exception:
            # Single-stage parse failure: fall back for this stage only
            fb_raw = _FALLBACK_STAGE_POLICIES_RAW.get(stage, {})
            result[stage] = _build_stage_policy(stage, fb_raw)

    _stage_policies_cache = result
    _stage_policies_loaded_at = now
    return result


def load_model_aliases() -> dict[str, str]:
    """Return the current model-aliases mapping, using the ~10s TTL cache."""
    global _model_aliases_cache, _model_aliases_loaded_at

    now = time.monotonic()
    if _model_aliases_cache is not None and (now - _model_aliases_loaded_at) < _TTL:
        return _model_aliases_cache

    raw_aliases = _read_yaml_section("model_aliases")
    if raw_aliases is None or not isinstance(raw_aliases, dict):
        _model_aliases_cache = dict(_FALLBACK_MODEL_ALIASES)
    else:
        _model_aliases_cache = {str(k): str(v) for k, v in raw_aliases.items()}

    _model_aliases_loaded_at = now
    return _model_aliases_cache


def invalidate_cache() -> None:
    """Force the next call to reload from disk (used by dashboard config writes)."""
    global _stage_policies_cache, _model_aliases_cache
    _stage_policies_cache = None
    _model_aliases_cache = None


# ---------------------------------------------------------------------------
# YAML reader (stdlib only — no PyYAML required for the simple flat structure)
# ---------------------------------------------------------------------------

def _read_yaml_section(section: str) -> dict | None:
    """Read *section* from stage-policies.yaml.

    Returns ``None`` on any error (missing file, parse error, wrong type).
    Prefers PyYAML when available; falls back to a minimal line-by-line parser
    for the specific flat format used by this file.
    """
    yaml_file = _yaml_path()
    try:
        text = yaml_file.read_text(encoding="utf-8")
    except OSError:
        return None

    try:
        import yaml  # type: ignore[import]
        data = yaml.safe_load(text)
    except ImportError:
        data = _parse_yaml_minimal(text)
    except Exception:
        return None

    if not isinstance(data, dict):
        return None
    return data.get(section)  # type: ignore[return-value]


def _parse_yaml_minimal(text: str) -> dict:
    """Minimal parser for the specific two-section YAML format.

    Handles only:
      top_key:
        child_key: {key: value, key2: value2}
      top_key:
        child_key: scalar_value

    Sufficient for stage-policies.yaml without a PyYAML dependency.
    """
    import re

    result: dict = {}
    current_section: str | None = None

    # Inline-dict pattern: key: {k: v, k2: v2, ...}
    inline_dict_re = re.compile(r"^\s{2,}(\S+):\s*\{(.+)\}\s*$")
    # Simple scalar: key: value
    scalar_re = re.compile(r"^\s{2,}(\S+):\s*(\S+)\s*$")
    # Section header: key:
    section_re = re.compile(r"^(\w[\w_-]*):\s*$")

    def _coerce(v: str) -> object:
        v = v.strip().rstrip(",")
        if v.lower() == "true":
            return True
        if v.lower() == "false":
            return False
        try:
            return int(v)
        except ValueError:
            pass
        try:
            return float(v)
        except ValueError:
            pass
        return v

    for line in text.splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue

        m = section_re.match(line)
        if m:
            current_section = m.group(1)
            result[current_section] = {}
            continue

        if current_section is None:
            continue

        m = inline_dict_re.match(line)
        if m:
            key = m.group(1).rstrip(":")
            pairs_str = m.group(2)
            pairs: dict = {}
            for pair in re.split(r",\s*", pairs_str):
                if ":" in pair:
                    pk, pv = pair.split(":", 1)
                    pairs[pk.strip()] = _coerce(pv.strip())
            result[current_section][key] = pairs
            continue

        m = scalar_re.match(line)
        if m:
            key = m.group(1).rstrip(":")
            result[current_section][key] = _coerce(m.group(2))
            continue

    return result
