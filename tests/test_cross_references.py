"""Tests for cross-reference chunk generation."""

from __future__ import annotations

from bc_al_chunker.chunker import chunk_objects
from bc_al_chunker.config import ChunkingConfig
from bc_al_chunker.cross_references import (
    build_cross_reference_chunks,
    is_event_publisher,
    parse_event_subscriber,
)
from bc_al_chunker.models import ChunkType
from bc_al_chunker.parser import parse_source

from .conftest import read_fixture


class TestParseEventSubscriber:
    """Test the EventSubscriber attribute argument parser."""

    def test_parse_codeunit_subscriber(self) -> None:
        attr = (
            '[EventSubscriber(ObjectType::Codeunit, Codeunit::"Customer Mgt.", '
            "'OnAfterInsertCustomer', '', true, true)]"
        )
        result = parse_event_subscriber(attr)
        assert result is not None
        obj_type, obj_name, event_name = result
        assert obj_type == "codeunit"
        assert obj_name == "Customer Mgt."
        assert event_name == "OnAfterInsertCustomer"

    def test_parse_table_subscriber(self) -> None:
        attr = (
            "[EventSubscriber(ObjectType::Table, Database::Customer, "
            "'OnAfterInsert', '', false, false)]"
        )
        result = parse_event_subscriber(attr)
        assert result is not None
        obj_type, obj_name, event_name = result
        assert obj_type == "table"
        assert obj_name == "Customer"
        assert event_name == "OnAfterInsert"

    def test_returns_none_for_non_subscriber(self) -> None:
        assert parse_event_subscriber("[IntegrationEvent(false, false)]") is None
        assert parse_event_subscriber("[BusinessEvent(false)]") is None
        assert parse_event_subscriber("[NonDestructiveTest]") is None

    def test_is_event_publisher_integration(self) -> None:
        assert is_event_publisher("[IntegrationEvent(false, false)]") is True
        assert is_event_publisher("[BusinessEvent(true)]") is True

    def test_is_event_publisher_negative(self) -> None:
        assert is_event_publisher("[EventSubscriber(...)]") is False
        assert is_event_publisher("[NonDestructiveTest]") is False


class TestBuildCrossReferenceChunks:
    """Test cross-reference chunk generation from parsed objects."""

    def test_table_extension_cross_ref(self) -> None:
        source = read_fixture("table_extension.al")
        objects = parse_source(source, file_path="table_extension.al")
        config = ChunkingConfig()
        xrefs = build_cross_reference_chunks(objects, config)
        assert len(xrefs) == 1
        xref = xrefs[0]
        assert xref.metadata.chunk_type == ChunkType.CROSS_REFERENCE
        assert xref.metadata.relationship_type == "extends_table"
        assert xref.metadata.target_object_type == "table"
        assert xref.metadata.target_object_name == "Customer"

    def test_page_extension_cross_ref(self) -> None:
        source = read_fixture("page_extension.al")
        objects = parse_source(source, file_path="page_extension.al")
        config = ChunkingConfig()
        xrefs = build_cross_reference_chunks(objects, config)
        assert len(xrefs) == 1
        xref = xrefs[0]
        assert xref.metadata.relationship_type == "extends_page"
        assert xref.metadata.target_object_type == "page"
        assert xref.metadata.target_object_name == "Customer Card"

    def test_implements_single_interface(self) -> None:
        source = read_fixture("codeunit_implements.al")
        objects = parse_source(source, file_path="codeunit_implements.al")
        config = ChunkingConfig()
        xrefs = build_cross_reference_chunks(objects, config)
        iface_xrefs = [x for x in xrefs if x.metadata.relationship_type == "implements_interface"]
        assert len(iface_xrefs) == 1
        assert iface_xrefs[0].metadata.target_object_name == "IAddress Provider"
        assert iface_xrefs[0].metadata.target_object_type == "interface"

    def test_implements_multiple_interfaces(self) -> None:
        source = read_fixture("codeunit_multi_implements.al")
        objects = parse_source(source, file_path="codeunit_multi_implements.al")
        config = ChunkingConfig()
        xrefs = build_cross_reference_chunks(objects, config)
        iface_xrefs = [x for x in xrefs if x.metadata.relationship_type == "implements_interface"]
        assert len(iface_xrefs) == 2
        names = {x.metadata.target_object_name for x in iface_xrefs}
        assert names == {"IAddress Provider", "INotification Service"}

    def test_event_subscriber_cross_ref(self) -> None:
        source = read_fixture("large_codeunit.al")
        objects = parse_source(source, file_path="large_codeunit.al")
        config = ChunkingConfig()
        xrefs = build_cross_reference_chunks(objects, config)
        sub_xrefs = [x for x in xrefs if x.metadata.relationship_type == "subscribes_to"]
        assert len(sub_xrefs) == 1
        xref = sub_xrefs[0]
        assert xref.metadata.target_object_type == "codeunit"
        assert xref.metadata.target_object_name == "Customer Mgt."
        assert xref.metadata.procedure_name == "OnAfterInsertCustomer"
        assert "OnAfterInsertCustomer" in xref.content

    def test_no_cross_refs_for_plain_object(self) -> None:
        source = read_fixture("simple_enum.al")
        objects = parse_source(source)
        config = ChunkingConfig()
        xrefs = build_cross_reference_chunks(objects, config)
        assert xrefs == []

    def test_cross_ref_content_is_descriptive(self) -> None:
        source = read_fixture("table_extension.al")
        objects = parse_source(source, file_path="table_extension.al")
        config = ChunkingConfig()
        xrefs = build_cross_reference_chunks(objects, config)
        assert len(xrefs) == 1
        assert "Customer Ext" in xrefs[0].content
        assert "Customer" in xrefs[0].content


class TestCrossRefsInChunkObjects:
    """Test that cross-references are emitted by chunk_objects."""

    def test_chunk_objects_includes_cross_refs(self) -> None:
        source = read_fixture("table_extension.al")
        objects = parse_source(source, file_path="table_extension.al")
        config = ChunkingConfig(emit_cross_references=True)
        chunks = chunk_objects(objects, config)
        xrefs = [c for c in chunks if c.metadata.chunk_type == ChunkType.CROSS_REFERENCE]
        assert len(xrefs) >= 1

    def test_chunk_objects_cross_refs_disabled(self) -> None:
        source = read_fixture("table_extension.al")
        objects = parse_source(source, file_path="table_extension.al")
        config = ChunkingConfig(emit_cross_references=False)
        chunks = chunk_objects(objects, config)
        xrefs = [c for c in chunks if c.metadata.chunk_type == ChunkType.CROSS_REFERENCE]
        assert len(xrefs) == 0
