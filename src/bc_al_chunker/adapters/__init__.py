"""Adapter protocol and base classes for AL file sources."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


@runtime_checkable
class FileSource(Protocol):
    """Protocol for adapters that yield ``.al`` file contents.

    Each adapter must implement ``iter_al_files`` which yields
    ``(relative_path, file_content)`` tuples.  Adapters may also
    implement ``iter_al_files_sync`` for synchronous usage.

    Optionally, adapters may implement ``get_app_json_sync`` to return
    the raw ``app.json`` content for app-metadata chunk generation.
    """

    def iter_al_files_sync(self) -> list[tuple[str, str]]:
        """Synchronous version — return all ``.al`` files at once."""
        ...  # pragma: no cover

    def iter_al_files(self) -> AsyncIterator[tuple[str, str]]:
        """Yield ``(relative_path, file_content)`` for each ``.al`` file."""
        ...  # pragma: no cover

    def get_app_json_sync(self) -> str | None:
        """Return the raw content of ``app.json``, or ``None`` if unavailable."""
        ...  # pragma: no cover
