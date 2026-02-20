"""Tests for the local filesystem adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bc_al_chunker.adapters.local import LocalAdapter

if TYPE_CHECKING:
    from pathlib import Path


class TestLocalAdapter:
    def test_discover_al_files(self, fixtures_dir: Path) -> None:
        adapter = LocalAdapter(fixtures_dir)
        files = adapter.iter_al_files_sync()
        assert len(files) > 0
        for rel_path, content in files:
            assert rel_path.endswith(".al")
            assert len(content) > 0

    def test_single_file(self, fixtures_dir: Path) -> None:
        single = fixtures_dir / "simple_enum.al"
        adapter = LocalAdapter(single)
        files = adapter.iter_al_files_sync()
        assert len(files) == 1
        assert "enum 50100" in files[0][1]

    def test_multiple_paths(self, fixtures_dir: Path) -> None:
        adapter = LocalAdapter([fixtures_dir, fixtures_dir])
        files = adapter.iter_al_files_sync()
        # Should get files from both (even if same dir).
        assert len(files) > 0

    def test_empty_directory(self, tmp_path: Path) -> None:
        adapter = LocalAdapter(tmp_path)
        files = adapter.iter_al_files_sync()
        assert len(files) == 0

    def test_nested_directories(self, tmp_path: Path) -> None:
        sub = tmp_path / "src" / "tables"
        sub.mkdir(parents=True)
        (sub / "test.al").write_text("table 1 Test {}", encoding="utf-8")
        adapter = LocalAdapter(tmp_path)
        files = adapter.iter_al_files_sync()
        assert len(files) == 1

    def test_non_al_files_ignored(self, tmp_path: Path) -> None:
        (tmp_path / "readme.md").write_text("# hello")
        (tmp_path / "test.al").write_text("table 1 Test {}", encoding="utf-8")
        adapter = LocalAdapter(tmp_path)
        files = adapter.iter_al_files_sync()
        assert len(files) == 1
        assert files[0][0].endswith(".al")


class TestGetAppJson:
    """Test the get_app_json_sync method."""

    def test_returns_app_json_content(self, tmp_path: Path) -> None:
        (tmp_path / "app.json").write_text('{"name": "Test"}', encoding="utf-8")
        adapter = LocalAdapter(tmp_path)
        result = adapter.get_app_json_sync()
        assert result is not None
        assert "Test" in result

    def test_returns_none_when_missing(self, tmp_path: Path) -> None:
        adapter = LocalAdapter(tmp_path)
        result = adapter.get_app_json_sync()
        assert result is None

    def test_fixture_dir_has_app_json(self, fixtures_dir: Path) -> None:
        adapter = LocalAdapter(fixtures_dir)
        result = adapter.get_app_json_sync()
        assert result is not None
        assert "Address Management" in result
