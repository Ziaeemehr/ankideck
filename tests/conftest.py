"""Shared fixtures for ankideck tests."""

import pytest


@pytest.fixture
def tmp_csv(tmp_path):
    """Return a helper that writes a temp file and gives back its path."""

    def _write(name: str, content: str) -> str:
        p = tmp_path / name
        p.write_text(content, encoding="utf-8")
        return str(p)

    return _write
