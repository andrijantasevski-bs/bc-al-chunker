"""bc-al-chunker — RAG-optimized chunking for Business Central AL files.

Quick start::

    from bc_al_chunker import chunk

    chunks = chunk("/path/to/al-repo")

    # Multiple repos
    chunks = chunk(["/repo1", "/repo2"])

    # Customise thresholds
    from bc_al_chunker import ChunkingConfig
    chunks = chunk("/repo", config=ChunkingConfig(max_chunk_chars=2000))

    # Export
    from bc_al_chunker import chunks_to_json, chunks_to_jsonl
    chunks_to_json(chunks, "output.json")
    chunks_to_jsonl(chunks, "output.jsonl")

    # Remote sources
    from bc_al_chunker import chunk_source
    from bc_al_chunker.adapters.github import GitHubAdapter
    chunks = chunk_source(GitHubAdapter("owner/repo", token="ghp_..."))
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from bc_al_chunker.chunker import chunk_object, chunk_objects
from bc_al_chunker.config import ChunkingConfig
from bc_al_chunker.models import (
    ALObject,
    ALObjectType,
    ALProcedure,
    ALSection,
    Chunk,
    ChunkMetadata,
    ChunkType,
)
from bc_al_chunker.parser import parse_file, parse_files, parse_source
from bc_al_chunker.serializers import (
    chunks_from_json,
    chunks_from_jsonl,
    chunks_to_dicts,
    chunks_to_json,
    chunks_to_jsonl,
)

if TYPE_CHECKING:
    from pathlib import Path

    from bc_al_chunker.adapters import FileSource

__all__ = [
    "ALObject",
    "ALObjectType",
    "ALProcedure",
    "ALSection",
    "Chunk",
    "ChunkMetadata",
    "ChunkType",
    "ChunkingConfig",
    "chunk",
    "chunk_object",
    "chunk_objects",
    "chunk_source",
    "chunks_from_json",
    "chunks_from_jsonl",
    "chunks_to_dicts",
    "chunks_to_json",
    "chunks_to_jsonl",
    "parse_file",
    "parse_files",
    "parse_source",
]


def chunk(
    paths: str | Path | list[str | Path],
    *,
    config: ChunkingConfig | None = None,
) -> list[Chunk]:
    """Chunk all ``.al`` files found under one or more local directories.

    This is the primary entry point for most users.

    Args:
        paths: A directory, file, or list of directories/files to scan.
        config: Optional chunking configuration.

    Returns:
        A list of embedding-ready ``Chunk`` objects.
    """
    from bc_al_chunker.adapters.local import LocalAdapter

    adapter = LocalAdapter(paths)
    files = adapter.iter_al_files_sync()
    objects: list[ALObject] = []
    for rel_path, content in files:
        objects.extend(parse_source(content, file_path=rel_path))
    return chunk_objects(objects, config)


def chunk_source(
    source: FileSource,
    *,
    config: ChunkingConfig | None = None,
) -> list[Chunk]:
    """Chunk ``.al`` files from any adapter (local, GitHub, Azure DevOps).

    For async adapters this runs the event loop synchronously.  If you already
    have a running loop, use the individual ``parse_source`` /
    ``chunk_objects`` functions with ``await source.iter_al_files()``.

    Args:
        source: An adapter implementing the ``FileSource`` protocol.
        config: Optional chunking configuration.

    Returns:
        A list of embedding-ready ``Chunk`` objects.
    """
    # Try sync first (cheaper, no event loop needed).
    try:
        files = source.iter_al_files_sync()
    except (NotImplementedError, AttributeError):
        # Fall back to async.
        files = asyncio.run(_collect_async(source))

    objects: list[ALObject] = []
    for rel_path, content in files:
        objects.extend(parse_source(content, file_path=rel_path))
    return chunk_objects(objects, config)


async def _collect_async(source: FileSource) -> list[tuple[str, str]]:
    results: list[tuple[str, str]] = []
    async for item in source.iter_al_files():
        results.append(item)
    return results
