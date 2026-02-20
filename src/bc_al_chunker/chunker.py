"""Chunking engine — converts parsed ALObject trees into embedding-ready chunks.

Implements a hierarchical, AST-aware chunking strategy:

1. Small objects (≤ ``max_chunk_chars``) → one ``WholeObject`` chunk.
2. Large objects are split at semantic boundaries:
   - A *header* chunk with the object declaration + top-level properties.
   - One chunk per structural section (``fields``, ``layout``, ``actions``, …).
     Sections that still exceed the limit are split at child-element level.
   - One chunk per procedure / trigger.
3. Every sub-object chunk gets a synthetic context header prepended so that
   each chunk is self-contained for the embedding model.
"""

from __future__ import annotations

import json
import re

from bc_al_chunker.config import ChunkingConfig
from bc_al_chunker.models import (
    ALObject,
    Chunk,
    ChunkMetadata,
    ChunkType,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_RE_SOURCE_TABLE = re.compile(
    r"^\s*SourceTable\s*=\s*(?P<tbl>.+?)\s*;",
    re.IGNORECASE | re.MULTILINE,
)
_RE_TABLE_NO = re.compile(
    r"^\s*TableNo\s*=\s*(?P<tbl>.+?)\s*;",
    re.IGNORECASE | re.MULTILINE,
)


def _estimate_tokens(text: str) -> int:
    """Cheap token estimate: roughly 1 token per 4 characters."""
    return max(1, len(text) // 4)


def _build_context_header(obj: ALObject, *, extra: str = "") -> str:
    """Build a context comment block to prepend to sub-object chunks."""
    lines = [f'// Object: {obj.object_type.value} {obj.object_id} "{obj.object_name}"']
    if obj.extends:
        lines.append(f"// Extends: {obj.extends}")
    if obj.file_path:
        lines.append(f"// File: {obj.file_path}")

    # Extract SourceTable / TableNo from properties.
    src_table = _get_source_table(obj)
    if src_table:
        lines.append(f"// SourceTable: {src_table}")

    if extra:
        lines.append(f"// {extra}")
    return "\n".join(lines) + "\n"


def _get_source_table(obj: ALObject) -> str:
    """Try to extract the SourceTable or TableNo property."""
    for prop in obj.properties:
        if prop.name.lower() in ("sourcetable", "tableno"):
            return prop.value.strip().strip("'\"")
    # Fallback: regex the raw source header area.
    for pattern in (_RE_SOURCE_TABLE, _RE_TABLE_NO):
        m = pattern.search(obj.raw_source[:500])
        if m:
            return m.group("tbl").strip().strip("'\"")
    return ""


def _make_chunk(
    content: str,
    obj: ALObject,
    chunk_type: ChunkType,
    line_start: int,
    line_end: int,
    *,
    section_name: str = "",
    procedure_name: str = "",
    attributes: tuple[str, ...] = (),
    config: ChunkingConfig,
    context_header: str = "",
) -> Chunk:
    """Construct a ``Chunk`` from its parts."""
    if config.include_context_header and context_header and chunk_type != ChunkType.WHOLE_OBJECT:
        full_content = context_header + content
    else:
        full_content = content
    return Chunk(
        content=full_content,
        metadata=ChunkMetadata(
            file_path=obj.file_path,
            object_type=obj.object_type.value,
            object_id=obj.object_id,
            object_name=obj.object_name,
            chunk_type=chunk_type.value,
            line_start=line_start,
            line_end=line_end,
            extends=obj.extends,
            section_name=section_name,
            procedure_name=procedure_name,
            parent_context=context_header,
            source_table=_get_source_table(obj),
            attributes=attributes,
        ),
        token_estimate=_estimate_tokens(full_content) if config.estimate_tokens else 0,
    )


# ---------------------------------------------------------------------------
# Section splitting
# ---------------------------------------------------------------------------

# Regex to find child blocks within a section:
#   field(1; Address; Text[50]) { ... }
#   action(NewAction) { ... }
#   group(General) { ... }
#   value(0; None) { ... }
_RE_CHILD_BLOCK = re.compile(
    r"""
    ^[ \t]*
    (?:field|action|group|part|repeater|area|column|dataitem|
       textelement|tableelement|fieldattribute|fieldelement|
       key|value|filter|separator|label|usercontrol|
       layout|systemaction|cuegroup|grid|fixed)
    \s*\(
    """,
    re.IGNORECASE | re.MULTILINE | re.VERBOSE,
)


def _split_section(raw: str) -> list[str]:
    """Split a section's inner content into child blocks.

    Falls back to returning the full section if no children are found.
    """
    children: list[str] = []
    for m in _RE_CHILD_BLOCK.finditer(raw):
        brace = raw.find("{", m.start())
        if brace == -1:
            continue
        # Simple local brace match (not as robust as full _find_brace_block
        # because we're operating on a substring, but sections are well-structured).
        depth = 0
        i = brace
        while i < len(raw):
            ch = raw[i]
            if ch == "'":
                i += 1
                while i < len(raw) and raw[i] != "'":
                    i += 1
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    children.append(raw[m.start() : i + 1])
                    break
            i += 1
    return children if children else [raw]


# ---------------------------------------------------------------------------
# Object header extraction
# ---------------------------------------------------------------------------


def _extract_header(obj: ALObject) -> str:
    """Extract the object declaration + top-level properties as a string."""
    lines = obj.raw_source.splitlines(keepends=True)
    header_lines: list[str] = []
    brace_depth = 0
    in_sub = False

    for line in lines:
        # Detect when we enter a section or procedure body.
        if not in_sub:
            # Count braces.
            for ch in line:
                if ch == "{":
                    brace_depth += 1
                    if brace_depth >= 2:
                        in_sub = True
                        break
                elif ch == "}":
                    brace_depth -= 1
            if not in_sub:
                header_lines.append(line)
        else:
            for ch in line:
                if ch == "{":
                    brace_depth += 1
                elif ch == "}":
                    brace_depth -= 1
            if brace_depth <= 1:
                in_sub = False

    # Also skip procedure/trigger lines that might appear at depth 1.
    result: list[str] = []
    skip_proc = False
    for line in header_lines:
        low = line.strip().lower()
        if (
            low.startswith(
                (
                    "procedure ",
                    "trigger ",
                    "local procedure",
                    "internal procedure",
                    "protected procedure",
                    "[",
                )
            )
            and "procedure" not in low.split("=")[0:1]
        ):
            skip_proc = True
        if not skip_proc:
            result.append(line)
        if skip_proc and low.endswith(";"):
            skip_proc = False

    text = "".join(result).rstrip()
    # Ensure it ends with closing brace if it doesn't already.
    if text and not text.rstrip().endswith("}"):
        text += "\n}"
    return text


# ---------------------------------------------------------------------------
# App metadata chunk
# ---------------------------------------------------------------------------


def build_app_metadata_chunk(
    raw_json: str,
    config: ChunkingConfig | None = None,
) -> Chunk | None:
    """Create an ``app_metadata`` chunk from raw ``app.json`` content.

    The chunk content is a human-readable summary of the extension identity,
    dependencies, and target BC version — optimised for embedding.

    Args:
        raw_json: The raw text content of ``app.json``.
        config: Optional chunking configuration (for token estimation).

    Returns:
        A single ``Chunk`` or ``None`` if the JSON is invalid.
    """
    if config is None:
        config = ChunkingConfig()

    try:
        data = json.loads(raw_json)
    except (json.JSONDecodeError, TypeError):
        return None

    if not isinstance(data, dict):
        return None

    lines: list[str] = ["// App Metadata"]
    _name = data.get("name", "")
    if _name:
        lines.append(f"// Name: {_name}")
    if data.get("publisher"):
        lines.append(f"// Publisher: {data['publisher']}")
    if data.get("version"):
        lines.append(f"// Version: {data['version']}")
    if data.get("id"):
        lines.append(f"// ID: {data['id']}")
    if data.get("application"):
        lines.append(f"// Application: {data['application']}")
    if data.get("platform"):
        lines.append(f"// Platform: {data['platform']}")
    if data.get("runtime"):
        lines.append(f"// Runtime: {data['runtime']}")

    deps = data.get("dependencies", [])
    if deps and isinstance(deps, list):
        lines.append("// Dependencies:")
        for dep in deps:
            if isinstance(dep, dict):
                dep_name = dep.get("name", dep.get("id", "?"))
                dep_pub = dep.get("publisher", "")
                dep_ver = dep.get("version", "")
                parts = [f'"{dep_name}"']
                if dep_pub:
                    parts.append(f"by {dep_pub}")
                if dep_ver:
                    parts.append(f"({dep_ver})")
                lines.append(f"//   - {' '.join(parts)}")

    content = "\n".join(lines)
    return Chunk(
        content=content,
        metadata=ChunkMetadata(
            file_path="app.json",
            object_type="app",
            object_id=0,
            object_name=_name or "app",
            chunk_type=ChunkType.APP_METADATA.value,
            line_start=1,
            line_end=content.count("\n") + 1,
        ),
        token_estimate=_estimate_tokens(content) if config.estimate_tokens else 0,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def chunk_object(obj: ALObject, config: ChunkingConfig | None = None) -> list[Chunk]:
    """Chunk a single ``ALObject`` into embedding-ready ``Chunk`` instances.

    Args:
        obj: A parsed AL object.
        config: Chunking configuration.  Uses defaults if ``None``.

    Returns:
        A list of chunks.
    """
    if config is None:
        config = ChunkingConfig()

    raw_len = len(obj.raw_source)

    # Small object → keep whole.
    if raw_len <= config.max_chunk_chars:
        return [
            _make_chunk(
                obj.raw_source,
                obj,
                ChunkType.WHOLE_OBJECT,
                obj.line_start,
                obj.line_end,
                config=config,
            )
        ]

    # Large object → split at semantic boundaries.
    context_header = _build_context_header(obj) if config.include_context_header else ""
    chunks: list[Chunk] = []

    # 1. Header chunk (declaration + properties).
    header_text = _extract_header(obj)
    if header_text and len(header_text) >= config.min_chunk_chars:
        chunks.append(
            _make_chunk(
                header_text,
                obj,
                ChunkType.HEADER,
                obj.line_start,
                obj.line_start,  # approximate
                config=config,
                context_header=context_header,
            )
        )

    # 2. Section chunks.
    for sec in obj.sections:
        if len(sec.raw_source) <= config.max_chunk_chars:
            chunks.append(
                _make_chunk(
                    sec.raw_source,
                    obj,
                    ChunkType.SECTION,
                    sec.line_start,
                    sec.line_end,
                    section_name=sec.name,
                    config=config,
                    context_header=context_header,
                )
            )
        else:
            # Split section into child blocks.
            children = _split_section(sec.raw_source)
            for child in children:
                if len(child) < config.min_chunk_chars:
                    continue
                chunks.append(
                    _make_chunk(
                        child,
                        obj,
                        ChunkType.SECTION,
                        sec.line_start,
                        sec.line_end,
                        section_name=sec.name,
                        config=config,
                        context_header=context_header,
                    )
                )

    # 3. Procedure / trigger chunks.
    for proc in obj.procedures:
        ctype = ChunkType.TRIGGER if proc.is_trigger else ChunkType.PROCEDURE
        chunks.append(
            _make_chunk(
                proc.raw_source,
                obj,
                ctype,
                proc.line_start,
                proc.line_end,
                procedure_name=proc.name,
                attributes=tuple(proc.attributes),
                config=config,
                context_header=context_header,
            )
        )

    return chunks


def chunk_objects(objects: list[ALObject], config: ChunkingConfig | None = None) -> list[Chunk]:
    """Chunk a list of ``ALObject`` instances.

    Args:
        objects: Parsed AL objects (from ``parse_source`` / ``parse_file``).
        config: Chunking configuration.

    Returns:
        A flat list of all chunks, optionally followed by cross-reference chunks.
    """
    if config is None:
        config = ChunkingConfig()
    result: list[Chunk] = []
    for obj in objects:
        result.extend(chunk_object(obj, config))

    if config.emit_cross_references:
        from bc_al_chunker.cross_references import build_cross_reference_chunks

        result.extend(build_cross_reference_chunks(objects, config))

    return result
