from __future__ import annotations

import pytest

try:
    from workshop.doc_resolver import resolve_doc  # type: ignore[import]
except ImportError:
    resolve_doc = None  # type: ignore[assignment]


def _skip_if_missing() -> None:
    if resolve_doc is None:
        pytest.xfail("workshop.doc_resolver not yet implemented")


@pytest.mark.xfail(reason="workshop.doc_resolver not yet implemented", strict=False)
def test_tier1_repo_first(tmp_path) -> None:
    """resolve_doc finds a doc in workspace_dir before falling back to vault."""
    _skip_if_missing()
    doc_file = tmp_path / "prd.md"
    doc_file.write_text("# PRD content")
    result = resolve_doc("prd.md", workspace_dir=tmp_path)
    assert result is not None
    assert "PRD content" in result


@pytest.mark.xfail(reason="workshop.doc_resolver not yet implemented", strict=False)
def test_tier2_vault_grep(tmp_path) -> None:
    """resolve_doc falls back to vault path when doc not in workspace_dir."""
    _skip_if_missing()
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()
    (vault_dir / "prd.md").write_text("# Vault PRD")
    result = resolve_doc("prd.md", workspace_dir=tmp_path / "empty", vault_dir=vault_dir)
    assert result is not None
    assert "Vault PRD" in result


@pytest.mark.xfail(reason="workshop.doc_resolver not yet implemented", strict=False)
def test_tier3_brain_degraded(tmp_path) -> None:
    """resolve_doc returns None gracefully when Brain raises an error."""
    _skip_if_missing()
    result = resolve_doc(
        "prd.md",
        workspace_dir=tmp_path / "empty",
        vault_dir=tmp_path / "empty_vault",
        brain_error=True,
    )
    assert result is None


@pytest.mark.xfail(reason="workshop.doc_resolver not yet implemented", strict=False)
def test_doc_name_traversal_blocked(tmp_path) -> None:
    """resolve_doc rejects path-traversal doc_name like ../etc/passwd."""
    _skip_if_missing()
    with pytest.raises((ValueError, PermissionError)):
        resolve_doc("../etc/passwd", workspace_dir=tmp_path)
