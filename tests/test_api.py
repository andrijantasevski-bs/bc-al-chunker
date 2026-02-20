"""Integration tests for the top-level API."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bc_al_chunker import chunk

from .conftest import FIXTURES_DIR

if TYPE_CHECKING:
    from pathlib import Path


class TestChunkFunction:
    """Test the top-level ``chunk()`` convenience function."""

    def test_chunk_fixtures_dir(self) -> None:
        chunks = chunk(FIXTURES_DIR)
        assert len(chunks) > 0
        # Every fixture file should produce at least one chunk.
        file_paths = {c.metadata.file_path for c in chunks}
        assert len(file_paths) >= 5  # We have at least 10 fixture files.

    def test_chunk_single_file(self) -> None:
        path = FIXTURES_DIR / "simple_enum.al"
        chunks = chunk(path)
        assert len(chunks) == 1
        assert "enum 50100" in chunks[0].content

    def test_chunk_multiple_paths(self) -> None:
        chunks = chunk([FIXTURES_DIR])
        assert len(chunks) > 0

    def test_all_chunks_have_content(self) -> None:
        chunks = chunk(FIXTURES_DIR)
        for c in chunks:
            assert len(c.content) > 0

    def test_all_chunks_have_metadata(self) -> None:
        chunks = chunk(FIXTURES_DIR)
        for c in chunks:
            assert c.metadata.object_type != ""
            assert c.metadata.object_name != ""
            assert c.metadata.chunk_type != ""

    def test_json_roundtrip(self, tmp_path: Path) -> None:
        from bc_al_chunker import chunks_from_json, chunks_to_json

        chunks = chunk(FIXTURES_DIR)
        out = tmp_path / "test.json"
        chunks_to_json(chunks, out)
        loaded = chunks_from_json(out)
        assert len(loaded) == len(chunks)

    def test_jsonl_roundtrip(self, tmp_path: Path) -> None:
        from bc_al_chunker import chunks_from_jsonl, chunks_to_jsonl

        chunks = chunk(FIXTURES_DIR)
        out = tmp_path / "test.jsonl"
        chunks_to_jsonl(chunks, out)
        loaded = chunks_from_jsonl(out)
        assert len(loaded) == len(chunks)
