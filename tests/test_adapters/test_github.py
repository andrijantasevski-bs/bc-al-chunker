"""Tests for the GitHub adapter (mocked HTTP)."""

from __future__ import annotations

import pytest

try:
    import respx  # noqa: TC002

    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

pytestmark = pytest.mark.skipif(not HAS_HTTPX, reason="httpx/respx not installed")


@pytest.fixture
def _mock_github(respx_mock: respx.MockRouter) -> None:  # type: ignore[name-defined]
    tree_response = {
        "sha": "abc123",
        "tree": [
            {"path": "src/Table.al", "type": "blob", "sha": "sha1"},
            {"path": "src/Page.al", "type": "blob", "sha": "sha2"},
            {"path": "README.md", "type": "blob", "sha": "sha3"},
        ],
    }
    respx_mock.get("https://api.github.com/repos/owner/repo/git/trees/main?recursive=1").respond(
        200, json=tree_response
    )

    respx_mock.get("https://api.github.com/repos/owner/repo/git/blobs/sha1").respond(
        200, text='table 50100 "Test Table" { fields { } }'
    )
    respx_mock.get("https://api.github.com/repos/owner/repo/git/blobs/sha2").respond(
        200, text='page 50100 "Test Page" { layout { } }'
    )


@pytest.mark.usefixtures("_mock_github")
class TestGitHubAdapter:
    def test_lists_only_al_files(self) -> None:
        from bc_al_chunker.adapters.github import GitHubAdapter

        adapter = GitHubAdapter("owner/repo")
        files = adapter.iter_al_files_sync()
        assert len(files) == 2
        paths = [f[0] for f in files]
        assert "src/Table.al" in paths
        assert "src/Page.al" in paths

    def test_file_content_fetched(self) -> None:
        from bc_al_chunker.adapters.github import GitHubAdapter

        adapter = GitHubAdapter("owner/repo")
        files = adapter.iter_al_files_sync()
        table_content = next(c for p, c in files if "Table.al" in p)
        assert "table 50100" in table_content

    def test_token_header(self) -> None:
        from bc_al_chunker.adapters.github import GitHubAdapter

        adapter = GitHubAdapter("owner/repo", token="ghp_test123")
        headers = adapter._headers()
        assert headers["Authorization"] == "Bearer ghp_test123"

    def test_path_filtering(self) -> None:
        from bc_al_chunker.adapters.github import GitHubAdapter

        adapter = GitHubAdapter("owner/repo", paths=["src/Table"])
        files = adapter.iter_al_files_sync()
        assert len(files) == 1
        assert "Table.al" in files[0][0]
