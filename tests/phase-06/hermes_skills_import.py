from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


def load_module(module_name: str, path: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, Path(path))
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
