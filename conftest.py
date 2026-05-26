from __future__ import annotations

import sys
from pathlib import Path

# Add the repo root to sys.path so that `workshop` and `hermes-skills` packages
# are importable when running pytest from the project root.
_repo_root = Path(__file__).parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))
