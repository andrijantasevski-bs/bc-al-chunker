"""Configuration for chunking behavior."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ChunkingConfig:
    """Controls how AL objects are split into chunks.

    Attributes:
        max_chunk_chars: Maximum characters per chunk. Objects smaller than this
            are kept whole. Default 1500 (~300-500 tokens).
        min_chunk_chars: Minimum characters for a chunk. Smaller pieces are merged
            with adjacent content. Default 100.
        include_context_header: Whether to prepend a context comment header to
            sub-object chunks so each chunk is self-contained. Default True.
        estimate_tokens: Whether to compute a token estimate on each chunk.
            Uses the chars/4 heuristic. Default True.
        emit_app_metadata: Whether to emit an ``app_metadata`` chunk from
            ``app.json`` when available.  Default True.
        emit_cross_references: Whether to emit ``cross_reference`` chunks that
            capture relationships (extends, implements, event subscriptions)
            across objects.  Default True.
    """

    max_chunk_chars: int = 1500
    min_chunk_chars: int = 100
    include_context_header: bool = True
    estimate_tokens: bool = True
    emit_app_metadata: bool = True
    emit_cross_references: bool = True
