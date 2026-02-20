"""Data models for AL parsing and chunking."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field


class ALObjectType(enum.StrEnum):
    """All AL object types including extensions."""

    TABLE = "table"
    TABLE_EXTENSION = "tableextension"
    PAGE = "page"
    PAGE_EXTENSION = "pageextension"
    PAGE_CUSTOMIZATION = "pagecustomization"
    CODEUNIT = "codeunit"
    REPORT = "report"
    REPORT_EXTENSION = "reportextension"
    QUERY = "query"
    XMLPORT = "xmlport"
    ENUM = "enum"
    ENUM_EXTENSION = "enumextension"
    INTERFACE = "interface"
    PERMISSION_SET = "permissionset"
    PERMISSION_SET_EXTENSION = "permissionsetextension"
    PROFILE = "profile"
    CONTROL_ADDIN = "controladdin"
    ENTITLEMENT = "entitlement"
    DOTNET = "dotnet"


class ChunkType(enum.StrEnum):
    """The granularity level of a chunk."""

    WHOLE_OBJECT = "whole_object"
    HEADER = "header"
    SECTION = "section"
    PROCEDURE = "procedure"
    TRIGGER = "trigger"
    APP_METADATA = "app_metadata"
    CROSS_REFERENCE = "cross_reference"


@dataclass(slots=True)
class ALProperty:
    """A single property assignment (e.g., Caption = 'Address')."""

    name: str
    value: str
    line_start: int
    line_end: int


@dataclass(slots=True)
class ALSection:
    """A structural section inside an AL object (fields, keys, layout, etc.)."""

    name: str
    raw_source: str
    line_start: int
    line_end: int
    children: list[ALSection] = field(default_factory=list)


@dataclass(slots=True)
class ALProcedure:
    """A procedure or trigger inside an AL object."""

    name: str
    raw_source: str
    line_start: int
    line_end: int
    is_trigger: bool = False
    access_modifier: str = ""
    attributes: list[str] = field(default_factory=list)
    return_type: str = ""


@dataclass(slots=True)
class ALObject:
    """Parsed representation of a single AL object from a .al file."""

    object_type: ALObjectType
    object_id: int
    object_name: str
    raw_source: str
    file_path: str
    line_start: int
    line_end: int
    extends: str = ""
    implements: list[str] = field(default_factory=list)
    properties: list[ALProperty] = field(default_factory=list)
    sections: list[ALSection] = field(default_factory=list)
    procedures: list[ALProcedure] = field(default_factory=list)


@dataclass(slots=True, frozen=True)
class ChunkMetadata:
    """Metadata attached to each chunk for filtering and context."""

    file_path: str
    object_type: str
    object_id: int
    object_name: str
    chunk_type: str
    line_start: int
    line_end: int
    extends: str = ""
    section_name: str = ""
    procedure_name: str = ""
    parent_context: str = ""
    source_table: str = ""
    attributes: tuple[str, ...] = ()
    relationship_type: str = ""
    target_object_type: str = ""
    target_object_name: str = ""


@dataclass(slots=True, frozen=True)
class Chunk:
    """A single chunk of AL code ready for embedding."""

    content: str
    metadata: ChunkMetadata
    token_estimate: int
