"""Local filesystem adapter — walk directories for .al files."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


class LocalAdapter:
    """Read ``.al`` files from one or more local directories.

    Args:
        paths: A single path or list of paths to directories or files.
    """

    def __init__(self, paths: str | Path | list[str | Path]) -> None:
        if isinstance(paths, (str, Path)):
            paths = [paths]
        self._paths = [Path(p) for p in paths]

    # ---- sync (primary for local) ----

    def iter_al_files_sync(self) -> list[tuple[str, str]]:
        """Return ``(relative_path, content)`` for every ``.al`` file found."""
        results: list[tuple[str, str]] = []
        for root in self._paths:
            root = root.resolve()
            if root.is_file() and root.suffix.lower() == ".al":
                results.append((root.name, root.read_text(encoding="utf-8-sig")))
            elif root.is_dir():
                results.extend(self._walk(root, root))
        return results

    # ---- async (for protocol compat) ----

    async def iter_al_files(self) -> AsyncIterator[tuple[str, str]]:
        """Async wrapper around the sync implementation."""
        for item in self.iter_al_files_sync():
            yield item

    # ---- internal ----

    @staticmethod
    def _walk(directory: Path, base: Path) -> list[tuple[str, str]]:
        """Recursively walk *directory* using ``os.scandir`` for speed."""
        results: list[tuple[str, str]] = []
        try:
            entries = sorted(os.scandir(directory), key=lambda e: e.name)
        except PermissionError:
            return results
        for entry in entries:
            if entry.is_dir(follow_symlinks=False):
                results.extend(LocalAdapter._walk(Path(entry.path), base))
            elif entry.is_file() and entry.name.lower().endswith(".al"):
                rel = os.path.relpath(entry.path, base)
                try:
                    content = Path(entry.path).read_text(encoding="utf-8-sig")
                except (PermissionError, OSError):
                    continue
                results.append((rel, content))
        return results
