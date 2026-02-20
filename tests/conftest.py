"""Shared test fixtures and helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


def read_fixture(name: str) -> str:
    """Read a fixture file by name and return its content."""
    return (FIXTURES_DIR / name).read_text(encoding="utf-8-sig")
