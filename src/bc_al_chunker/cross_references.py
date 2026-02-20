"""Cross-reference chunk generation — relationship edges between AL objects.

Scans parsed ``ALObject`` instances and emits metadata-only ``Chunk`` records
that describe relationships such as:

- ``TableExtension`` → base ``Table``
- ``PageExtension`` → base ``Page``
- ``EnumExtension`` → base ``Enum``
- ``ReportExtension`` → base ``Report``
- ``PermissionSetExtension`` → base ``PermissionSet``
- ``PageCustomization`` → base ``Page``
- Interface implementations (``implements`` clause)
- ``EventSubscriber`` → event publisher
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from bc_al_chunker.models import (
    ALObject,
    ALObjectType,
    Chunk,
    ChunkMetadata,
    ChunkType,
)

if TYPE_CHECKING:
    from bc_al_chunker.config import ChunkingConfig

# ---------------------------------------------------------------------------
# Attribute argument parsers
# ---------------------------------------------------------------------------

# Matches [EventSubscriber(ObjectType::Table, Database::"Customer", 'OnAfterInsert', '', ...)]
_RE_EVENT_SUBSCRIBER = re.compile(
    r"""
    \[EventSubscriber\s*\(
        \s*ObjectType\s*::\s*(?P<obj_type>\w+)     # ObjectType::Table / Codeunit / ...
        \s*,\s*
        (?:\w+\s*::\s*)?                            # optional qualifier (Database::, Codeunit::)
        (?P<obj_name>"[^"]*"|'[^']*'|\w+)           # target object name
        \s*,\s*
        (?P<event>'[^']*'|"[^"]*")                  # event name
    """,
    re.IGNORECASE | re.VERBOSE | re.DOTALL,
)

# Event publisher markers — the procedure that declares the event.
_RE_INTEGRATION_EVENT = re.compile(
    r"\[(?:IntegrationEvent|BusinessEvent)\s*\(",
    re.IGNORECASE,
)

# Maps extension types to their base object type string.
_EXTENSION_BASE_MAP: dict[ALObjectType, str] = {
    ALObjectType.TABLE_EXTENSION: "table",
    ALObjectType.PAGE_EXTENSION: "page",
    ALObjectType.PAGE_CUSTOMIZATION: "page",
    ALObjectType.ENUM_EXTENSION: "enum",
    ALObjectType.REPORT_EXTENSION: "report",
    ALObjectType.PERMISSION_SET_EXTENSION: "permissionset",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _unquote(s: str) -> str:
    """Strip surrounding quotes (single or double) from a string."""
    if len(s) >= 2 and s[0] in ("'", '"') and s[-1] == s[0]:
        return s[1:-1]
    return s


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def parse_event_subscriber(attr: str) -> tuple[str, str, str] | None:
    """Parse an ``[EventSubscriber(...)]`` attribute string.

    Args:
        attr: The full attribute text, e.g.
            ``'[EventSubscriber(ObjectType::Codeunit, Codeunit::"Customer Mgt.", ...)]'``

    Returns:
        A tuple ``(target_object_type, target_object_name, event_name)``
        or ``None`` if parsing fails.
    """
    m = _RE_EVENT_SUBSCRIBER.search(attr)
    if not m:
        return None
    return (
        m.group("obj_type").lower(),
        _unquote(m.group("obj_name")),
        _unquote(m.group("event")),
    )


def is_event_publisher(attr: str) -> bool:
    """Return ``True`` if *attr* is an ``[IntegrationEvent]`` or ``[BusinessEvent]``."""
    return bool(_RE_INTEGRATION_EVENT.search(attr))


# ---------------------------------------------------------------------------
# Cross-reference chunk builder
# ---------------------------------------------------------------------------


def _make_xref_chunk(
    *,
    source_obj: ALObject,
    relationship_type: str,
    target_object_type: str,
    target_object_name: str,
    description: str,
    config: ChunkingConfig,
    procedure_name: str = "",
    attributes: tuple[str, ...] = (),
) -> Chunk:
    """Construct a single cross-reference ``Chunk``."""
    return Chunk(
        content=description,
        metadata=ChunkMetadata(
            file_path=source_obj.file_path,
            object_type=source_obj.object_type.value,
            object_id=source_obj.object_id,
            object_name=source_obj.object_name,
            chunk_type=ChunkType.CROSS_REFERENCE.value,
            line_start=source_obj.line_start,
            line_end=source_obj.line_end,
            extends=source_obj.extends,
            procedure_name=procedure_name,
            attributes=attributes,
            relationship_type=relationship_type,
            target_object_type=target_object_type,
            target_object_name=target_object_name,
        ),
        token_estimate=_estimate_tokens(description) if config.estimate_tokens else 0,
    )


def build_cross_reference_chunks(
    objects: list[ALObject],
    config: ChunkingConfig,
) -> list[Chunk]:
    """Build cross-reference chunks from a list of parsed AL objects.

    This is a **global batch** operation — it scans all objects at once so that
    relationships spanning multiple files can be resolved.

    Args:
        objects: All parsed AL objects (typically from an entire repository).
        config: Chunking configuration (used for token estimation).

    Returns:
        A list of ``cross_reference`` chunks.
    """
    chunks: list[Chunk] = []

    # Build a lookup for target resolution.
    _obj_lookup: dict[tuple[str, str], ALObject] = {}
    for obj in objects:
        key = (obj.object_type.value, obj.object_name.lower())
        _obj_lookup[key] = obj

    for obj in objects:
        # 1. Extension → base object
        base_type = _EXTENSION_BASE_MAP.get(obj.object_type)
        if base_type and obj.extends:
            _type_label = obj.object_type.value.replace("extension", " extension")
            _type_label = _type_label.replace("customization", " customization")
            desc = (
                f'{obj.object_type.value} {obj.object_id} "{obj.object_name}" '
                f'extends {base_type} "{obj.extends}"'
            )
            chunks.append(
                _make_xref_chunk(
                    source_obj=obj,
                    relationship_type=f"extends_{base_type}",
                    target_object_type=base_type,
                    target_object_name=obj.extends,
                    description=desc,
                    config=config,
                )
            )

        # 2. Interface implementations
        for iface_name in obj.implements:
            desc = (
                f'{obj.object_type.value} {obj.object_id} "{obj.object_name}" '
                f'implements interface "{iface_name}"'
            )
            chunks.append(
                _make_xref_chunk(
                    source_obj=obj,
                    relationship_type="implements_interface",
                    target_object_type="interface",
                    target_object_name=iface_name,
                    description=desc,
                    config=config,
                )
            )

        # 3. EventSubscriber → publisher
        for proc in obj.procedures:
            for attr in proc.attributes:
                parsed = parse_event_subscriber(attr)
                if parsed is None:
                    continue
                target_type, target_name, event_name = parsed
                desc = (
                    f'{obj.object_type.value} {obj.object_id} "{obj.object_name}" '
                    f"subscribes to event '{event_name}' on "
                    f'{target_type} "{target_name}"'
                )
                chunks.append(
                    _make_xref_chunk(
                        source_obj=obj,
                        relationship_type="subscribes_to",
                        target_object_type=target_type,
                        target_object_name=target_name,
                        description=desc,
                        config=config,
                        procedure_name=proc.name,
                        attributes=tuple(proc.attributes),
                    )
                )

    return chunks
