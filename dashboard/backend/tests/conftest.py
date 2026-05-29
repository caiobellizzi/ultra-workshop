"""Pytest configuration for dashboard backend tests."""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure the repo root is on sys.path so both `workshop` and `dashboard` are importable.
_repo_root = Path(__file__).parent.parent.parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))
