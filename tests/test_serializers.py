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
