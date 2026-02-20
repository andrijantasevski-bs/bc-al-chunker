"""Integration tests for the top-level API."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bc_al_chunker import chunk
from bc_al_chunker.config import ChunkingConfig
from bc_al_chunker.models import ChunkType

from .conftest import FIXTURES_DIR

if TYPE_CHECKING:
    from pathlib import Path


class TestChunkFunction:
    """Test the top-level ``chunk()`` convenience function."""

    def test_chunk_fixtures_dir(self) -> None:
        chunks = chunk(FIXTURES_DIR)
        assert len(chunks) > 0
        # Every fixture .al file should produce at least one chunk.
        al_chunks = [
            c
            for c in chunks
            if c.metadata.chunk_type != ChunkType.APP_METADATA
            and c.metadata.chunk_type != ChunkType.CROSS_REFERENCE
        ]
        file_paths = {c.metadata.file_path for c in al_chunks}
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

    def test_app_metadata_chunk_present(self) -> None:
        chunks = chunk(FIXTURES_DIR)
        app_chunks = [c for c in chunks if c.metadata.chunk_type == ChunkType.APP_METADATA]
        assert len(app_chunks) == 1
        assert app_chunks[0].metadata.object_type == "app"
        assert "Address Management" in app_chunks[0].content

    def test_app_metadata_disabled(self) -> None:
        config = ChunkingConfig(emit_app_metadata=False)
        chunks = chunk(FIXTURES_DIR, config=config)
        app_chunks = [c for c in chunks if c.metadata.chunk_type == ChunkType.APP_METADATA]
        assert len(app_chunks) == 0

    def test_cross_reference_chunks_present(self) -> None:
        chunks = chunk(FIXTURES_DIR)
        xrefs = [c for c in chunks if c.metadata.chunk_type == ChunkType.CROSS_REFERENCE]
        # Should have at least extension + implements + event subscriber cross-refs
        assert len(xrefs) >= 3

    def test_cross_references_disabled(self) -> None:
        config = ChunkingConfig(emit_cross_references=False)
        chunks = chunk(FIXTURES_DIR, config=config)
        xrefs = [c for c in chunks if c.metadata.chunk_type == ChunkType.CROSS_REFERENCE]
        assert len(xrefs) == 0

    def test_app_metadata_is_first_chunk(self) -> None:
        chunks = chunk(FIXTURES_DIR)
        assert len(chunks) > 0
        assert chunks[0].metadata.chunk_type == ChunkType.APP_METADATA

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
