"""Tests for JSON/JSONL serialization."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from bc_al_chunker.chunker import chunk_object

if TYPE_CHECKING:
    from pathlib import Path
from bc_al_chunker.parser import parse_source
from bc_al_chunker.serializers import (
    chunks_from_json,
    chunks_from_jsonl,
    chunks_to_dicts,
    chunks_to_json,
    chunks_to_jsonl,
)

from .conftest import read_fixture


def _make_chunks() -> list:
    source = read_fixture("simple_table.al")
    obj = parse_source(source, file_path="simple_table.al")[0]
    return chunk_object(obj)


class TestDictConversion:
    def test_to_dicts(self) -> None:
        chunks = _make_chunks()
        dicts = chunks_to_dicts(chunks)
        assert len(dicts) == len(chunks)
        assert "content" in dicts[0]
        assert "metadata" in dicts[0]
        assert "token_estimate" in dicts[0]

    def test_metadata_fields(self) -> None:
        chunks = _make_chunks()
        d = chunks_to_dicts(chunks)[0]
        meta = d["metadata"]
        assert meta["object_type"] == "table"
        assert meta["object_name"] == "Simple Address"


class TestJsonSerialization:
    def test_round_trip(self, tmp_path: Path) -> None:
        chunks = _make_chunks()
        out = tmp_path / "chunks.json"
        chunks_to_json(chunks, out)
        loaded = chunks_from_json(out)
        assert len(loaded) == len(chunks)
        assert loaded[0].content == chunks[0].content
        assert loaded[0].metadata.object_type == chunks[0].metadata.object_type

    def test_valid_json(self, tmp_path: Path) -> None:
        chunks = _make_chunks()
        out = tmp_path / "chunks.json"
        chunks_to_json(chunks, out)
        data = json.loads(out.read_text())
        assert isinstance(data, list)


class TestJsonlSerialization:
    def test_round_trip(self, tmp_path: Path) -> None:
        chunks = _make_chunks()
        out = tmp_path / "chunks.jsonl"
        chunks_to_jsonl(chunks, out)
        loaded = chunks_from_jsonl(out)
        assert len(loaded) == len(chunks)
        assert loaded[0].content == chunks[0].content

    def test_one_json_per_line(self, tmp_path: Path) -> None:
        chunks = _make_chunks()
        out = tmp_path / "chunks.jsonl"
        chunks_to_jsonl(chunks, out)
        lines = [line for line in out.read_text().splitlines() if line.strip()]
        assert len(lines) == len(chunks)
        for line in lines:
            json.loads(line)  # Should not raise.

    def test_attributes_preserved_as_list(self, tmp_path: Path) -> None:
        chunks = _make_chunks()
        out = tmp_path / "chunks.json"
        chunks_to_json(chunks, out)
        loaded = chunks_from_json(out)
        # attributes should be a tuple after deserialization
        assert isinstance(loaded[0].metadata.attributes, tuple)

    def test_cross_reference_fields_roundtrip(self, tmp_path: Path) -> None:
        """Cross-reference metadata fields survive a JSON roundtrip."""
        from bc_al_chunker.models import Chunk, ChunkMetadata, ChunkType

        xref = Chunk(
            content="tableextension extends table",
            metadata=ChunkMetadata(
                file_path="ext.al",
                object_type="tableextension",
                object_id=50100,
                object_name="Customer Ext",
                chunk_type=ChunkType.CROSS_REFERENCE.value,
                line_start=1,
                line_end=10,
                extends="Customer",
                relationship_type="extends_table",
                target_object_type="table",
                target_object_name="Customer",
            ),
            token_estimate=10,
        )
        out = tmp_path / "xref.json"
        chunks_to_json([xref], out)
        loaded = chunks_from_json(out)
        assert len(loaded) == 1
        assert loaded[0].metadata.relationship_type == "extends_table"
        assert loaded[0].metadata.target_object_type == "table"
        assert loaded[0].metadata.target_object_name == "Customer"

    def test_app_metadata_roundtrip(self, tmp_path: Path) -> None:
        """App metadata chunk survives a JSON roundtrip."""
        from bc_al_chunker.models import Chunk, ChunkMetadata, ChunkType

        app = Chunk(
            content="// App Metadata\n// Name: Test",
            metadata=ChunkMetadata(
                file_path="app.json",
                object_type="app",
                object_id=0,
                object_name="Test",
                chunk_type=ChunkType.APP_METADATA.value,
                line_start=1,
                line_end=2,
            ),
            token_estimate=5,
        )
        out = tmp_path / "app.json"
        chunks_to_json([app], out)
        loaded = chunks_from_json(out)
        assert len(loaded) == 1
        assert loaded[0].metadata.chunk_type == ChunkType.APP_METADATA


class TestFileHashSerialization:
    """Verify that file_hash survives JSON / JSONL roundtrips."""

    def test_file_hash_present_in_dict(self) -> None:
        chunks = _make_chunks()
        d = chunks_to_dicts(chunks)[0]
        assert "file_hash" in d["metadata"]
        assert len(d["metadata"]["file_hash"]) == 16

    def test_file_hash_roundtrip_json(self, tmp_path: Path) -> None:
        chunks = _make_chunks()
        original_hash = chunks[0].metadata.file_hash
        out = tmp_path / "chunks.json"
        chunks_to_json(chunks, out)
        loaded = chunks_from_json(out)
        assert loaded[0].metadata.file_hash == original_hash

    def test_file_hash_roundtrip_jsonl(self, tmp_path: Path) -> None:
        chunks = _make_chunks()
        original_hash = chunks[0].metadata.file_hash
        out = tmp_path / "chunks.jsonl"
        chunks_to_jsonl(chunks, out)
        loaded = chunks_from_jsonl(out)
        assert loaded[0].metadata.file_hash == original_hash

    def test_missing_file_hash_defaults_to_empty_string(self, tmp_path: Path) -> None:
        """Legacy JSON files without file_hash should deserialize without error."""
        import json

        chunks = _make_chunks()
        d = chunks_to_dicts(chunks)[0]
        del d["metadata"]["file_hash"]
        out = tmp_path / "legacy.json"
        out.write_text(json.dumps([d]), encoding="utf-8")
        loaded = chunks_from_json(out)
        assert loaded[0].metadata.file_hash == ""
