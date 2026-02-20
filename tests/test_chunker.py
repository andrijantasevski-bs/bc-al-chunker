"""Tests for the chunking engine."""

from __future__ import annotations

from bc_al_chunker.chunker import chunk_object, chunk_objects
from bc_al_chunker.config import ChunkingConfig
from bc_al_chunker.models import ChunkType
from bc_al_chunker.parser import parse_source

from .conftest import read_fixture


class TestSmallObjectChunking:
    """Small objects should produce a single WholeObject chunk."""

    def test_simple_enum_single_chunk(self) -> None:
        source = read_fixture("simple_enum.al")
        obj = parse_source(source, file_path="simple_enum.al")[0]
        chunks = chunk_object(obj)
        assert len(chunks) == 1
        assert chunks[0].metadata.chunk_type == ChunkType.WHOLE_OBJECT

    def test_simple_table_single_chunk(self) -> None:
        source = read_fixture("simple_table.al")
        obj = parse_source(source, file_path="simple_table.al")[0]
        chunks = chunk_object(obj)
        assert len(chunks) == 1
        assert chunks[0].metadata.chunk_type == ChunkType.WHOLE_OBJECT

    def test_interface_single_chunk(self) -> None:
        source = read_fixture("interface.al")
        obj = parse_source(source, file_path="interface.al")[0]
        chunks = chunk_object(obj)
        assert len(chunks) == 1

    def test_whole_object_contains_full_source(self) -> None:
        source = read_fixture("simple_enum.al")
        obj = parse_source(source, file_path="simple_enum.al")[0]
        chunks = chunk_object(obj)
        # Content should be the full object source.
        assert "enum 50100" in chunks[0].content
        assert "Gold" in chunks[0].content


class TestLargeObjectChunking:
    """Large objects should be split at semantic boundaries."""

    def test_codeunit_splits_into_multiple_chunks(self) -> None:
        source = read_fixture("large_codeunit.al")
        obj = parse_source(source, file_path="large_codeunit.al")[0]
        # Use a small max to force splitting.
        config = ChunkingConfig(max_chunk_chars=200)
        chunks = chunk_object(obj, config)
        assert len(chunks) > 1

    def test_split_produces_procedure_chunks(self) -> None:
        source = read_fixture("large_codeunit.al")
        obj = parse_source(source, file_path="large_codeunit.al")[0]
        config = ChunkingConfig(max_chunk_chars=200)
        chunks = chunk_object(obj, config)
        proc_chunks = [c for c in chunks if c.metadata.chunk_type == ChunkType.PROCEDURE]
        assert len(proc_chunks) > 0

    def test_split_produces_trigger_chunks(self) -> None:
        source = read_fixture("large_codeunit.al")
        obj = parse_source(source, file_path="large_codeunit.al")[0]
        config = ChunkingConfig(max_chunk_chars=200)
        chunks = chunk_object(obj, config)
        trigger_chunks = [c for c in chunks if c.metadata.chunk_type == ChunkType.TRIGGER]
        assert len(trigger_chunks) > 0

    def test_page_splits_into_sections(self) -> None:
        source = read_fixture("page_card.al")
        obj = parse_source(source, file_path="page_card.al")[0]
        config = ChunkingConfig(max_chunk_chars=200)
        chunks = chunk_object(obj, config)
        section_chunks = [c for c in chunks if c.metadata.chunk_type == ChunkType.SECTION]
        assert len(section_chunks) > 0


class TestContextHeaders:
    """Test that context headers are correctly prepended."""

    def test_sub_chunks_have_context_header(self) -> None:
        source = read_fixture("large_codeunit.al")
        obj = parse_source(source, file_path="large_codeunit.al")[0]
        config = ChunkingConfig(max_chunk_chars=200, include_context_header=True)
        chunks = chunk_object(obj, config)
        # Sub-chunks (not WholeObject) should have context headers.
        for c in chunks:
            if c.metadata.chunk_type != ChunkType.WHOLE_OBJECT:
                assert c.content.startswith("// Object:")

    def test_context_header_disabled(self) -> None:
        source = read_fixture("large_codeunit.al")
        obj = parse_source(source, file_path="large_codeunit.al")[0]
        config = ChunkingConfig(max_chunk_chars=200, include_context_header=False)
        chunks = chunk_object(obj, config)
        for c in chunks:
            assert not c.content.startswith("// Object:")

    def test_whole_object_no_context_header(self) -> None:
        source = read_fixture("simple_enum.al")
        obj = parse_source(source, file_path="simple_enum.al")[0]
        config = ChunkingConfig(include_context_header=True)
        chunks = chunk_object(obj, config)
        assert len(chunks) == 1
        assert not chunks[0].content.startswith("// Object:")


class TestMetadata:
    """Test that chunk metadata is correctly populated."""

    def test_object_type_in_metadata(self) -> None:
        source = read_fixture("simple_table.al")
        obj = parse_source(source, file_path="simple_table.al")[0]
        chunks = chunk_object(obj)
        assert chunks[0].metadata.object_type == "table"

    def test_file_path_in_metadata(self) -> None:
        source = read_fixture("simple_table.al")
        obj = parse_source(source, file_path="src/tables/simple_table.al")[0]
        chunks = chunk_object(obj)
        assert chunks[0].metadata.file_path == "src/tables/simple_table.al"

    def test_extends_in_metadata(self) -> None:
        source = read_fixture("page_extension.al")
        obj = parse_source(source, file_path="page_extension.al")[0]
        chunks = chunk_object(obj)
        assert chunks[0].metadata.extends == "Customer Card"

    def test_procedure_name_populated(self) -> None:
        source = read_fixture("large_codeunit.al")
        obj = parse_source(source, file_path="large_codeunit.al")[0]
        config = ChunkingConfig(max_chunk_chars=200)
        chunks = chunk_object(obj, config)
        proc_chunks = [c for c in chunks if c.metadata.chunk_type == ChunkType.PROCEDURE]
        for pc in proc_chunks:
            assert pc.metadata.procedure_name != ""

    def test_source_table_for_page(self) -> None:
        source = read_fixture("page_card.al")
        obj = parse_source(source, file_path="page_card.al")[0]
        chunks = chunk_object(obj)
        assert chunks[0].metadata.source_table == "Customer Address"

    def test_event_subscriber_attributes_in_metadata(self) -> None:
        source = read_fixture("large_codeunit.al")
        obj = parse_source(source, file_path="large_codeunit.al")[0]
        config = ChunkingConfig(max_chunk_chars=200)
        chunks = chunk_object(obj, config)
        sub_chunk = next(
            (c for c in chunks if c.metadata.procedure_name == "OnAfterInsertCustomer"),
            None,
        )
        assert sub_chunk is not None
        assert len(sub_chunk.metadata.attributes) > 0


class TestTokenEstimation:
    """Test token estimation on chunks."""

    def test_token_estimate_positive(self) -> None:
        source = read_fixture("simple_enum.al")
        obj = parse_source(source)[0]
        chunks = chunk_object(obj)
        assert chunks[0].token_estimate > 0

    def test_token_estimate_disabled(self) -> None:
        source = read_fixture("simple_enum.al")
        obj = parse_source(source)[0]
        config = ChunkingConfig(estimate_tokens=False)
        chunks = chunk_object(obj, config)
        assert chunks[0].token_estimate == 0


class TestChunkObjects:
    """Test the batch chunking function."""

    def test_multiple_objects(self) -> None:
        source1 = read_fixture("simple_enum.al")
        source2 = read_fixture("simple_table.al")
        objs = parse_source(source1) + parse_source(source2)
        config = ChunkingConfig(emit_cross_references=False)
        chunks = chunk_objects(objs, config)
        assert len(chunks) >= 2
