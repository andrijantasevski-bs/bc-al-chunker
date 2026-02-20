"""Serialization helpers — JSON and JSONL export/import for chunks."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from bc_al_chunker.models import Chunk, ChunkMetadata


def _chunk_to_dict(chunk: Chunk) -> dict[str, Any]:
    """Convert a ``Chunk`` to a plain dictionary."""
    return asdict(chunk)


def chunks_to_dicts(chunks: list[Chunk]) -> list[dict[str, Any]]:
    """Convert a list of chunks to a list of plain dictionaries."""
    return [_chunk_to_dict(c) for c in chunks]


def chunks_to_json(chunks: list[Chunk], path: str | Path) -> None:
    """Write chunks as a JSON array to *path*."""
    data = chunks_to_dicts(chunks)
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def chunks_to_jsonl(chunks: list[Chunk], path: str | Path) -> None:
    """Write chunks as newline-delimited JSON (JSONL) to *path*."""
    with Path(path).open("w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(_chunk_to_dict(chunk), ensure_ascii=False))
            f.write("\n")


def chunks_from_json(path: str | Path) -> list[Chunk]:
    """Read chunks from a JSON file produced by ``chunks_to_json``."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [_dict_to_chunk(d) for d in data]


def chunks_from_jsonl(path: str | Path) -> list[Chunk]:
    """Read chunks from a JSONL file produced by ``chunks_to_jsonl``."""
    chunks: list[Chunk] = []
    with Path(path).open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                chunks.append(_dict_to_chunk(json.loads(line)))
    return chunks


def _dict_to_chunk(d: dict[str, Any]) -> Chunk:
    """Reconstruct a ``Chunk`` from a dictionary."""
    meta_dict = d["metadata"]
    # Ensure attributes is a tuple.
    attrs = meta_dict.get("attributes", ())
    if isinstance(attrs, list):
        attrs = tuple(attrs)
    meta = ChunkMetadata(
        file_path=meta_dict["file_path"],
        object_type=meta_dict["object_type"],
        object_id=meta_dict["object_id"],
        object_name=meta_dict["object_name"],
        chunk_type=meta_dict["chunk_type"],
        line_start=meta_dict["line_start"],
        line_end=meta_dict["line_end"],
        extends=meta_dict.get("extends", ""),
        section_name=meta_dict.get("section_name", ""),
        procedure_name=meta_dict.get("procedure_name", ""),
        parent_context=meta_dict.get("parent_context", ""),
        source_table=meta_dict.get("source_table", ""),
        attributes=attrs,
        relationship_type=meta_dict.get("relationship_type", ""),
        target_object_type=meta_dict.get("target_object_type", ""),
        target_object_name=meta_dict.get("target_object_name", ""),
    )
    return Chunk(
        content=d["content"],
        metadata=meta,
        token_estimate=d.get("token_estimate", 0),
    )
