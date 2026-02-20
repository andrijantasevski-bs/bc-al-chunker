"""GitHub repository adapter — fetch .al files via GitHub API.

Requires ``httpx`` (install with ``pip install bc-al-chunker[github]``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


class GitHubAdapter:
    """Fetch ``.al`` files from a GitHub repository.

    Args:
        repo: Owner/repo string, e.g. ``"microsoft/BCApps"``.
        ref: Git ref (branch, tag, or SHA). Default ``"main"``.
        token: Optional GitHub Personal Access Token for private repos / rate limits.
        paths: Optional list of sub-paths to restrict file discovery.
        api_base: GitHub API base URL (for GitHub Enterprise).
    """

    def __init__(
        self,
        repo: str,
        *,
        ref: str = "main",
        token: str | None = None,
        paths: list[str] | None = None,
        api_base: str = "https://api.github.com",
    ) -> None:
        self._repo = repo
        self._ref = ref
        self._token = token
        self._paths = paths
        self._api_base = api_base.rstrip("/")

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Accept": "application/vnd.github+json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    def iter_al_files_sync(self) -> list[tuple[str, str]]:
        """Synchronous version using ``httpx`` sync client."""
        try:
            import httpx
        except ImportError as exc:
            msg = "httpx is required for GitHubAdapter. Install with: pip install bc-al-chunker[github]"
            raise ImportError(msg) from exc

        files: list[tuple[str, str]] = []
        with httpx.Client(http2=True, timeout=30.0) as client:
            tree = self._fetch_tree(client)
            for item in tree:
                path = item["path"]
                if not path.lower().endswith(".al"):
                    continue
                if self._paths and not any(path.startswith(p) for p in self._paths):
                    continue
                content = self._fetch_blob(client, item["sha"])
                files.append((path, content))
        return files

    async def iter_al_files(self) -> AsyncIterator[tuple[str, str]]:
        """Async version using ``httpx`` async client."""
        try:
            import httpx
        except ImportError as exc:
            msg = "httpx is required for GitHubAdapter. Install with: pip install bc-al-chunker[github]"
            raise ImportError(msg) from exc

        async with httpx.AsyncClient(http2=True, timeout=30.0) as client:
            url = f"{self._api_base}/repos/{self._repo}/git/trees/{self._ref}?recursive=1"
            resp = await client.get(url, headers=self._headers())
            resp.raise_for_status()
            tree_data: list[dict[str, Any]] = resp.json().get("tree", [])

            for item in tree_data:
                path: str = item["path"]
                if item.get("type") != "blob" or not path.lower().endswith(".al"):
                    continue
                if self._paths and not any(path.startswith(p) for p in self._paths):
                    continue
                blob_url = f"{self._api_base}/repos/{self._repo}/git/blobs/{item['sha']}"
                blob_resp = await client.get(
                    blob_url,
                    headers={**self._headers(), "Accept": "application/vnd.github.raw+json"},
                )
                blob_resp.raise_for_status()
                yield (path, blob_resp.text)

    # ---- sync helpers ----

    def _fetch_tree(self, client: Any) -> list[dict[str, Any]]:
        url = f"{self._api_base}/repos/{self._repo}/git/trees/{self._ref}?recursive=1"
        resp = client.get(url, headers=self._headers())
        resp.raise_for_status()
        return [item for item in resp.json().get("tree", []) if item.get("type") == "blob"]

    def _fetch_blob(self, client: Any, sha: str) -> str:
        url = f"{self._api_base}/repos/{self._repo}/git/blobs/{sha}"
        headers = {**self._headers(), "Accept": "application/vnd.github.raw+json"}
        resp = client.get(url, headers=headers)
        resp.raise_for_status()
        return str(resp.text)

    # ---- app.json ----

    def get_app_json_sync(self) -> str | None:
        """Fetch ``app.json`` from the repository root, if it exists."""
        try:
            import httpx
        except ImportError:
            return None

        with httpx.Client(http2=True, timeout=30.0) as client:
            tree = self._fetch_tree(client)
            for item in tree:
                if item["path"].lower() == "app.json":
                    return self._fetch_blob(client, item["sha"])
        return None
