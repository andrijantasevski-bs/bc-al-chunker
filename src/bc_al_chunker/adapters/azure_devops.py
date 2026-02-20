"""Azure DevOps repository adapter — fetch .al files via ADO REST API.

Requires ``httpx`` (install with ``pip install bc-al-chunker[azure]``).
"""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


class AzureDevOpsAdapter:
    """Fetch ``.al`` files from an Azure DevOps Git repository.

    Args:
        org: Azure DevOps organization name.
        project: Project name.
        repo: Repository name.
        ref: Git branch or tag. Default ``"main"``.
        token: Personal Access Token (PAT) for authentication.
        paths: Optional list of sub-paths to restrict file discovery.
        api_base: Base URL override (for Azure DevOps Server on-prem).
    """

    API_VERSION = "7.1"

    def __init__(
        self,
        org: str,
        project: str,
        repo: str,
        *,
        ref: str = "main",
        token: str | None = None,
        paths: list[str] | None = None,
        api_base: str | None = None,
    ) -> None:
        self._org = org
        self._project = project
        self._repo = repo
        self._ref = ref
        self._token = token
        self._paths = paths
        self._api_base = api_base.rstrip("/") if api_base else f"https://dev.azure.com/{org}"

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Accept": "application/json"}
        if self._token:
            encoded = base64.b64encode(f":{self._token}".encode()).decode()
            headers["Authorization"] = f"Basic {encoded}"
        return headers

    def _items_url(self) -> str:
        return f"{self._api_base}/{self._project}/_apis/git/repositories/{self._repo}/items"

    def iter_al_files_sync(self) -> list[tuple[str, str]]:
        """Synchronous file listing + content fetch."""
        try:
            import httpx
        except ImportError as exc:
            msg = (
                "httpx is required for AzureDevOpsAdapter. "
                "Install with: pip install bc-al-chunker[azure]"
            )
            raise ImportError(msg) from exc

        files: list[tuple[str, str]] = []
        with httpx.Client(http2=True, timeout=30.0) as client:
            items = self._list_items(client)
            for item in items:
                path: str = item["path"].lstrip("/")
                content = self._get_content(client, item["path"])
                files.append((path, content))
        return files

    async def iter_al_files(self) -> AsyncIterator[tuple[str, str]]:
        """Async file listing and content fetch."""
        try:
            import httpx
        except ImportError as exc:
            msg = (
                "httpx is required for AzureDevOpsAdapter. "
                "Install with: pip install bc-al-chunker[azure]"
            )
            raise ImportError(msg) from exc

        async with httpx.AsyncClient(http2=True, timeout=30.0) as client:
            params: dict[str, str] = {
                "recursionLevel": "Full",
                "versionDescriptor.version": self._ref,
                "versionDescriptor.versionType": "branch",
                "api-version": self.API_VERSION,
            }
            if self._paths:
                params["scopePath"] = self._paths[0]

            resp = await client.get(self._items_url(), params=params, headers=self._headers())
            resp.raise_for_status()
            items: list[dict[str, Any]] = resp.json().get("value", [])

            for item in items:
                if item.get("gitObjectType") != "blob":
                    continue
                path: str = item["path"].lstrip("/")
                if not path.lower().endswith(".al"):
                    continue
                if self._paths and not any(path.startswith(p) for p in self._paths):
                    continue

                content_resp = await client.get(
                    self._items_url(),
                    params={
                        "path": item["path"],
                        "versionDescriptor.version": self._ref,
                        "versionDescriptor.versionType": "branch",
                        "api-version": self.API_VERSION,
                    },
                    headers={**self._headers(), "Accept": "application/octet-stream"},
                )
                content_resp.raise_for_status()
                yield (path, content_resp.text)

    # ---- sync helpers ----

    def _list_items(self, client: Any) -> list[dict[str, Any]]:
        params: dict[str, str] = {
            "recursionLevel": "Full",
            "versionDescriptor.version": self._ref,
            "versionDescriptor.versionType": "branch",
            "api-version": self.API_VERSION,
        }
        if self._paths:
            params["scopePath"] = self._paths[0]
        resp = client.get(self._items_url(), params=params, headers=self._headers())
        resp.raise_for_status()
        return [
            item
            for item in resp.json().get("value", [])
            if item.get("gitObjectType") == "blob"
            and item["path"].lower().endswith(".al")
            and (
                not self._paths or any(item["path"].lstrip("/").startswith(p) for p in self._paths)
            )
        ]

    def _get_content(self, client: Any, path: str) -> str:
        resp = client.get(
            self._items_url(),
            params={
                "path": path,
                "versionDescriptor.version": self._ref,
                "versionDescriptor.versionType": "branch",
                "api-version": self.API_VERSION,
            },
            headers={**self._headers(), "Accept": "application/octet-stream"},
        )
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
            try:
                return self._get_content(client, "/app.json")
            except Exception:
                return None
