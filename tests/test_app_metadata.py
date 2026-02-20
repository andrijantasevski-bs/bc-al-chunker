"""Tests for app.json metadata chunk generation."""

from __future__ import annotations

from bc_al_chunker.chunker import build_app_metadata_chunk
from bc_al_chunker.config import ChunkingConfig
from bc_al_chunker.models import ChunkType

from .conftest import read_fixture


class TestBuildAppMetadataChunk:
    """Test the app.json metadata chunk builder."""

    def test_basic_metadata_chunk(self) -> None:
        raw = read_fixture("app.json")
        chunk = build_app_metadata_chunk(raw)
        assert chunk is not None
        assert chunk.metadata.chunk_type == ChunkType.APP_METADATA
        assert chunk.metadata.object_type == "app"
        assert chunk.metadata.object_id == 0
        assert chunk.metadata.file_path == "app.json"

    def test_chunk_contains_name(self) -> None:
        raw = read_fixture("app.json")
        chunk = build_app_metadata_chunk(raw)
        assert chunk is not None
        assert "Address Management" in chunk.content
        assert chunk.metadata.object_name == "Address Management"

    def test_chunk_contains_version(self) -> None:
        raw = read_fixture("app.json")
        chunk = build_app_metadata_chunk(raw)
        assert chunk is not None
        assert "1.0.0.0" in chunk.content

    def test_chunk_contains_publisher(self) -> None:
        raw = read_fixture("app.json")
        chunk = build_app_metadata_chunk(raw)
        assert chunk is not None
        assert "Contoso" in chunk.content

    def test_chunk_contains_platform(self) -> None:
        raw = read_fixture("app.json")
        chunk = build_app_metadata_chunk(raw)
        assert chunk is not None
        assert "Platform: 25.0.0.0" in chunk.content

    def test_chunk_contains_application(self) -> None:
        raw = read_fixture("app.json")
        chunk = build_app_metadata_chunk(raw)
        assert chunk is not None
        assert "Application: 25.0.0.0" in chunk.content

    def test_chunk_contains_runtime(self) -> None:
        raw = read_fixture("app.json")
        chunk = build_app_metadata_chunk(raw)
        assert chunk is not None
        assert "Runtime: 14.0" in chunk.content

    def test_chunk_contains_dependencies(self) -> None:
        raw = read_fixture("app.json")
        chunk = build_app_metadata_chunk(raw)
        assert chunk is not None
        assert "System Application" in chunk.content
        assert "Base Application" in chunk.content
        assert "Microsoft" in chunk.content

    def test_invalid_json_returns_none(self) -> None:
        assert build_app_metadata_chunk("not json at all") is None

    def test_non_object_json_returns_none(self) -> None:
        assert build_app_metadata_chunk("[1, 2, 3]") is None

    def test_empty_string_returns_none(self) -> None:
        assert build_app_metadata_chunk("") is None

    def test_minimal_app_json(self) -> None:
        raw = '{"name": "Test", "version": "1.0.0"}'
        chunk = build_app_metadata_chunk(raw)
        assert chunk is not None
        assert "Test" in chunk.content
        assert "1.0.0" in chunk.content

    def test_token_estimate(self) -> None:
        raw = read_fixture("app.json")
        chunk = build_app_metadata_chunk(raw)
        assert chunk is not None
        assert chunk.token_estimate > 0

    def test_token_estimate_disabled(self) -> None:
        raw = read_fixture("app.json")
        config = ChunkingConfig(estimate_tokens=False)
        chunk = build_app_metadata_chunk(raw, config)
        assert chunk is not None
        assert chunk.token_estimate == 0
