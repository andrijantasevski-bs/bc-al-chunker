"""Tests for the AL parser."""

from __future__ import annotations

from bc_al_chunker.models import ALObjectType
from bc_al_chunker.parser import parse_source

from .conftest import read_fixture


class TestObjectDetection:
    """Test that the parser correctly identifies AL object headers."""

    def test_parse_simple_enum(self) -> None:
        source = read_fixture("simple_enum.al")
        objects = parse_source(source, file_path="simple_enum.al")
        assert len(objects) == 1
        obj = objects[0]
        assert obj.object_type == ALObjectType.ENUM
        assert obj.object_id == 50100
        assert obj.object_name == "Customer Loyalty"

    def test_parse_simple_table(self) -> None:
        source = read_fixture("simple_table.al")
        objects = parse_source(source, file_path="simple_table.al")
        assert len(objects) == 1
        obj = objects[0]
        assert obj.object_type == ALObjectType.TABLE
        assert obj.object_id == 50100
        assert obj.object_name == "Simple Address"

    def test_parse_codeunit(self) -> None:
        source = read_fixture("large_codeunit.al")
        objects = parse_source(source, file_path="large_codeunit.al")
        assert len(objects) == 1
        obj = objects[0]
        assert obj.object_type == ALObjectType.CODEUNIT
        assert obj.object_id == 50100
        assert obj.object_name == "Address Management"

    def test_parse_page_card(self) -> None:
        source = read_fixture("page_card.al")
        objects = parse_source(source, file_path="page_card.al")
        assert len(objects) == 1
        obj = objects[0]
        assert obj.object_type == ALObjectType.PAGE
        assert obj.object_id == 50100
        assert obj.object_name == "Customer Address Card"

    def test_parse_page_extension(self) -> None:
        source = read_fixture("page_extension.al")
        objects = parse_source(source, file_path="page_extension.al")
        assert len(objects) == 1
        obj = objects[0]
        assert obj.object_type == ALObjectType.PAGE_EXTENSION
        assert obj.object_id == 50100
        assert obj.object_name == "Customer Card Ext"
        assert obj.extends == "Customer Card"

    def test_parse_table_extension(self) -> None:
        source = read_fixture("table_extension.al")
        objects = parse_source(source, file_path="table_extension.al")
        assert len(objects) == 1
        obj = objects[0]
        assert obj.object_type == ALObjectType.TABLE_EXTENSION
        assert obj.object_id == 50100
        assert obj.extends == "Customer"

    def test_parse_report(self) -> None:
        source = read_fixture("report.al")
        objects = parse_source(source, file_path="report.al")
        assert len(objects) == 1
        obj = objects[0]
        assert obj.object_type == ALObjectType.REPORT
        assert obj.object_id == 50100

    def test_parse_interface(self) -> None:
        source = read_fixture("interface.al")
        objects = parse_source(source, file_path="interface.al")
        assert len(objects) == 1
        obj = objects[0]
        assert obj.object_type == ALObjectType.INTERFACE
        assert obj.object_id == 0  # interfaces have no ID
        assert obj.object_name == "IAddress Provider"

    def test_parse_query(self) -> None:
        source = read_fixture("query.al")
        objects = parse_source(source, file_path="query.al")
        assert len(objects) == 1
        obj = objects[0]
        assert obj.object_type == ALObjectType.QUERY


class TestSectionExtraction:
    """Test that structural sections are correctly extracted."""

    def test_table_has_fields_and_keys(self) -> None:
        source = read_fixture("simple_table.al")
        obj = parse_source(source)[0]
        section_names = {s.name for s in obj.sections}
        assert "fields" in section_names
        assert "keys" in section_names

    def test_page_has_layout_and_actions(self) -> None:
        source = read_fixture("page_card.al")
        obj = parse_source(source)[0]
        section_names = {s.name for s in obj.sections}
        assert "layout" in section_names
        assert "actions" in section_names

    def test_report_has_dataset(self) -> None:
        source = read_fixture("report.al")
        obj = parse_source(source)[0]
        section_names = {s.name for s in obj.sections}
        assert "dataset" in section_names

    def test_page_list_has_views(self) -> None:
        source = read_fixture("page_list.al")
        obj = parse_source(source)[0]
        section_names = {s.name for s in obj.sections}
        assert "views" in section_names

    def test_query_has_elements(self) -> None:
        source = read_fixture("query.al")
        obj = parse_source(source)[0]
        section_names = {s.name for s in obj.sections}
        assert "elements" in section_names

    def test_report_has_requestpage(self) -> None:
        source = read_fixture("report.al")
        obj = parse_source(source)[0]
        section_names = {s.name for s in obj.sections}
        assert "requestpage" in section_names

    def test_report_has_rendering(self) -> None:
        source = read_fixture("report.al")
        obj = parse_source(source)[0]
        section_names = {s.name for s in obj.sections}
        assert "rendering" in section_names


class TestProcedureExtraction:
    """Test procedure and trigger extraction."""

    def test_codeunit_procedures(self) -> None:
        source = read_fixture("large_codeunit.al")
        obj = parse_source(source)[0]
        proc_names = [p.name for p in obj.procedures if not p.is_trigger]
        assert "ValidateAddress" in proc_names
        assert "NormalizePostCode" in proc_names
        assert "GetFormattedAddress" in proc_names
        assert "BatchValidateAddresses" in proc_names
        assert "OnAfterInsertCustomer" in proc_names

    def test_codeunit_triggers(self) -> None:
        source = read_fixture("large_codeunit.al")
        obj = parse_source(source)[0]
        triggers = [p for p in obj.procedures if p.is_trigger]
        trigger_names = [t.name for t in triggers]
        assert "OnRun" in trigger_names

    def test_table_triggers(self) -> None:
        source = read_fixture("table_with_triggers.al")
        obj = parse_source(source)[0]
        triggers = [p for p in obj.procedures if p.is_trigger]
        trigger_names = [t.name for t in triggers]
        assert "OnInsert" in trigger_names
        assert "OnModify" in trigger_names

    def test_event_subscriber_attributes(self) -> None:
        source = read_fixture("large_codeunit.al")
        obj = parse_source(source)[0]
        sub = next(p for p in obj.procedures if p.name == "OnAfterInsertCustomer")
        assert len(sub.attributes) > 0
        assert any("EventSubscriber" in attr for attr in sub.attributes)

    def test_local_procedure_access_modifier(self) -> None:
        source = read_fixture("large_codeunit.al")
        obj = parse_source(source)[0]
        local_proc = next(p for p in obj.procedures if p.name == "OnAfterInsertCustomer")
        assert local_proc.access_modifier == "local"

    def test_internal_procedure(self) -> None:
        source = read_fixture("large_codeunit.al")
        obj = parse_source(source)[0]
        proc = next(p for p in obj.procedures if p.name == "LogAddressChange")
        assert proc.access_modifier == "internal"


class TestPropertyExtraction:
    """Test top-level property extraction."""

    def test_table_properties(self) -> None:
        source = read_fixture("simple_table.al")
        obj = parse_source(source)[0]
        prop_names = {p.name for p in obj.properties}
        assert "Caption" in prop_names
        assert "DataPerCompany" in prop_names

    def test_page_properties(self) -> None:
        source = read_fixture("page_card.al")
        obj = parse_source(source)[0]
        prop_names = {p.name for p in obj.properties}
        assert "PageType" in prop_names
        assert "SourceTable" in prop_names


class TestEdgeCases:
    """Test parser edge cases."""

    def test_bom_handling(self) -> None:
        source = "\ufeff" + read_fixture("simple_enum.al")
        objects = parse_source(source)
        assert len(objects) == 1
        assert objects[0].object_name == "Customer Loyalty"

    def test_empty_source(self) -> None:
        assert parse_source("") == []

    def test_no_objects(self) -> None:
        assert parse_source("// just a comment") == []

    def test_quoted_name_with_spaces(self) -> None:
        source = read_fixture("simple_table.al")
        obj = parse_source(source)[0]
        assert obj.object_name == "Simple Address"

    def test_line_numbers_are_positive(self) -> None:
        source = read_fixture("large_codeunit.al")
        obj = parse_source(source)[0]
        assert obj.line_start >= 1
        assert obj.line_end > obj.line_start
        for proc in obj.procedures:
            assert proc.line_start >= 1
